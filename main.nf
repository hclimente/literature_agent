include { fromQuery; sqlInsert; sqlExecute } from 'plugin/nf-sqldb'

// Function to get articles by processing stage for incremental processing
def getUnprocessedArticles(flagColumn, columns, db = 'articles_db') {
    return channel.fromQuery(
        "SELECT ${columns} FROM articles WHERE ${flagColumn} IS NULL",
        db: db
    )
}

// Function to insert new articles with UPSERT logic
def insertNewArticles(channel, db = 'articles_db') {
    return channel
        .splitCsv(header: true, sep: '\t')
        .map { row ->
            // Use INSERT OR IGNORE to avoid duplicates based on unique link
            sqlExecute(
                db: db,
                statement: """
                    INSERT OR IGNORE INTO articles (title, summary, journal_name, link, date)
                    VALUES ('${row.title}', '${row.summary}', '${row.journal_name}', '${row.link}', '${row.date}')
                """
            )
        }
}

process CREATE_ARTICLES_DB {

    container 'community.wave.seqera.io/library/duckdb:1.4.1--3daff581f117ee85'
    publishDir "${DB_PARENT_DIR}", mode: 'copy'

    input:
    path JOURNALS_TSV
    val DB_FILENAME
    val DB_PARENT_DIR

    output:
    path "${DB_FILENAME}"

    script:
    """
    duckdb_create.py \
--journals_tsv ${JOURNALS_TSV} \
--db_path ${DB_FILENAME}
    """

}

process FETCH_ARTICLES {

    container 'community.wave.seqera.io/library/pip_feedparser:daf4046ba37d0661'
    tag { JOURNAL_NAME }

    input:
    tuple val(JOURNAL_NAME), val(FEED_URL), val(LAST_CHECKED)

    output:
    path "articles.tsv"

    script:
    """
    fetch_articles.py \
--journal_name "${JOURNAL_NAME}" \
--feed_url "${FEED_URL}" \
--cutoff_date "2025-10-10" \
--max_items 20
    """
}

process INSERT_NEW_ARTICLES {

    container 'community.wave.seqera.io/library/duckdb:1.4.1--3daff581f117ee85'

    input:
    path ARTICLES_TSV
    path DB_PATH

    output:
    val true

    script:
    """
    duckdb_insert_articles.py \
--db_path ${DB_PATH} \
--articles_tsv ${ARTICLES_TSV}
    """

}

process FETCH_UNPROCESSED_ARTICLES {

    container 'community.wave.seqera.io/library/duckdb:1.4.1--3daff581f117ee85'

    input:
    val WHERE_CLAUSE
    path DB_PATH
    val PROCESS_SINK

    output:
    path "output.tsv"

    script:
    """
    duckdb_extract_fields.py \
--db_path ${DB_PATH} \
--table articles \
--where_clause "${WHERE_CLAUSE}" \
--columns "id, title, summary, link, journal_name"
    """
}

process EXTRACT_DOI {

    container 'community.wave.seqera.io/library/duckdb_google-genai:2de7f99e6ef8ab9a'
    secret 'GOOGLE_API_KEY'
    tag { TITLE }

    input:
    tuple val(TITLE), val(SUMMARY), val(LINK), val(JOURNAL_NAME)

    output:
    tuple val(TITLE), val(SUMMARY), val(LINK), val(JOURNAL_NAME), env(DOI)

    script:
    """
    extract_doi.py \
--title "${TITLE}" \
--summary "${SUMMARY}" \
--link "${LINK}" \
--journal_name "${JOURNAL_NAME}"

    DOI=`cat doi.txt`
    """

}

process UPDATE_FIELDS {

    container 'community.wave.seqera.io/library/duckdb_google-genai:2de7f99e6ef8ab9a'
    secret 'GOOGLE_API_KEY'
    tag { JOURNAL_NAME }

    input:
    tuple val(ARTICLE_ID), val(TITLE), val(SUMMARY), val(LINK), val(JOURNAL_NAME)

    output:
    tuple val(ARTICLE_ID), val(DOI)

    script:
    """
    duckdb_update_field.py \
--db_path ${DB_PATH} \
--table articles \
--where_clause "id = ${ARTICLE_ID}" \
--set_clause "doi = '\$(cat doi.txt)'"


    """

}

process SCREEN_ARTICLES {

    container 'community.wave.seqera.io/library/duckdb_google-genai:2de7f99e6ef8ab9a'
    secret 'GOOGLE_API_KEY'
    secret 'SPRINGER_META_API_KEY'
    secret 'USER_EMAIL'
    tag { DOI }

    input:
    tuple val(TITLE), val(SUMMARY), val(LINK), val(JOURNAL_NAME), val(DOI)
    path RESEARCH_INTERESTS_PATH

    output:
    tuple val(TITLE), val(SUMMARY), val(LINK), val(JOURNAL_NAME), val(DOI), env(SCREENING_DECISION)

    script:
    """
    if [ "${DOI}" = "NULL" ]; then
        SCREENING_DECISION="NULL"
        exit 0
    fi

    screen_articles.py \
--title "${TITLE}" \
--summary "${SUMMARY}" \
--journal_name "${JOURNAL_NAME}" \
--doi "${DOI}" \
--research_interests_path ${RESEARCH_INTERESTS_PATH}

    SCREENING_DECISION=`cat decision.txt`
    """
}

process PRIORITIZE_ARTICLES {

    container 'community.wave.seqera.io/library/duckdb_google-genai:2de7f99e6ef8ab9a'
    secret 'GOOGLE_API_KEY'
    secret 'SPRINGER_META_API_KEY'
    secret 'USER_EMAIL'

    input:
    tuple val(TITLE), val(SUMMARY), val(LINK), val(JOURNAL_NAME), val(DOI), val(SCREENING_DECISION)
    path RESEARCH_INTERESTS_PATH

    output:
    tuple val(TITLE), val(SUMMARY), val(LINK), val(JOURNAL_NAME), val(DOI), val(SCREENING_DECISION), env(PRIORITY)

    script:
    """
    if [ "${SCREENING_DECISION}" = "NULL" ] || [ "${SCREENING_DECISION}" = "false" ]; then
        PRIORITY="NULL"
        exit 0
    fi

    prioritize_articles.py \
--title "${TITLE}" \
--summary "${SUMMARY}" \
--journal_name "${JOURNAL_NAME}" \
--doi "${DOI}" \
--research_interests_path ${RESEARCH_INTERESTS_PATH}

    PRIORITY=`cat priority.txt`
    """
}

workflow {

    database_path = file(params.database_path)

    if ( !database_path.exists() ) {
        println "Articles database not found. Creating a new one at: ${database_path}."
        println "Upon completion, re-run the workflow."
        // TODO this process crashes, there are errors with the Docker container
        db_filename = database_path.name
        db_parent_dir = database_path.parent
        CREATE_ARTICLES_DB(file(params.journal_list), db_filename, db_parent_dir)
    } else {
        journals = channel.fromQuery("SELECT name, feed_url, last_checked FROM sources", db: 'articles_db')

        // Fetch articles and insert new ones with fetched=true
        FETCH_ARTICLES(journals)

        new_articles = FETCH_ARTICLES.out |
            collectFile(name: 'articles.tsv', keepHeader: true)

        new_articles |
            splitCsv(header: true, sep: '\t') |
            map { row ->
                tuple(row.title, row.summary, row.link, row.journal_name)
            } |
            EXTRACT_DOI

        SCREEN_ARTICLES(EXTRACT_DOI.out, file(params.research_interests))
        PRIORITIZE_ARTICLES(SCREEN_ARTICLES.out, file(params.research_interests))

        // getUnprocessedArticles(
        //     'doi',
        //     'id, title, summary, link, journal_name',
        //     )
        // EXTRACT_DOI(articles_without_doi, database_path)

        // // Get articles that haven't been screened yet
        // articles_to_screen = getUnprocessedArticles(
        //     'screened',
        //     'id, title, summary, journal_name, doi')
        // SCREEN_ARTICLES(articles_to_screen, file(params.research_interests), database_path)
        // SCREEN_ARTICLES.out.view()

        // // Get articles that haven't been prioritized yet
        // unprioritized_articles = getUnprocessedArticles('priority')

        // PRIORITIZE_ARTICLES(unprioritized_articles, file(params.research_interests))
        // updateArticlesFlag(PRIORITIZE_ARTICLES.out, 'priority')
    }

}
