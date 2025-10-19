include { fromQuery; sqlInsert; sqlExecute } from 'plugin/nf-sqldb'

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

    container 'community.wave.seqera.io/library/pip_feedparser_python-dateutil:2bbb86f41337cff4'
    tag { JOURNAL_NAME }

    input:
    tuple val(JOURNAL_NAME), val(FEED_URL), val(LAST_CHECKED)

    output:
    path "article_*.txt"

    script:
    """
    fetch_articles.py \
--journal_name "${JOURNAL_NAME}" \
--feed_url "${FEED_URL}" \
--cutoff_date "2025-10-10" \
--max_items 20
    """
}

process SAVE_ARTICLE {

    container 'community.wave.seqera.io/library/duckdb:1.4.1--3daff581f117ee85'
    maxForks 1
    tag { TITLE }

    input:
    tuple val(TITLE), val(SUMMARY), val(LINK), val(JOURNAL_NAME), val(DATE), val(DOI), val(SCREENING_DECISION), val(PRIORITY)
    path DB_PATH

    output:
    val true

    script:
    """
    duckdb_insert_article.py \
--db_path ${DB_PATH} \
--title "${TITLE}" \
--summary "${SUMMARY}" \
--link "${LINK}" \
--journal_name "${JOURNAL_NAME}" \
--date "${DATE}" \
--doi "${DOI}" \
--screening_decision "${SCREENING_DECISION}" \
--priority "${PRIORITY}"
    """

}

process EXTRACT_METADATA {

    container 'community.wave.seqera.io/library/duckdb_google-genai:2de7f99e6ef8ab9a'
    maxForks 2
    secret 'GOOGLE_API_KEY'

    input:
    file ARTICLE_FILE

    output:
    file "metadata.tsv"

    script:
    """
    extract_metadata.py \
--article_file ${ARTICLE_FILE}
    """

}

process SCREEN_ARTICLES {

    container 'community.wave.seqera.io/library/duckdb_google-genai:2de7f99e6ef8ab9a'
    secret 'GOOGLE_API_KEY'
    secret 'SPRINGER_META_API_KEY'
    secret 'USER_EMAIL'
    tag { TITLE }

    input:
    tuple val(TITLE), val(SUMMARY), val(LINK), val(JOURNAL_NAME), val(DATE), val(DOI)
    path RESEARCH_INTERESTS_PATH

    output:
    tuple val(TITLE), val(SUMMARY), val(LINK), val(JOURNAL_NAME), val(DATE), val(DOI), env(SCREENING_DECISION)

    script:
    """
    if [ "${DOI}" = "NULL" ]; then
        SCREENING_DECISION="NULL"
    else
        screen_articles.py \
--title "${TITLE}" \
--summary "${SUMMARY}" \
--journal_name "${JOURNAL_NAME}" \
--doi "${DOI}" \
--research_interests_path ${RESEARCH_INTERESTS_PATH}

        SCREENING_DECISION=`cat decision.txt`
    fi
    """
}

process PRIORITIZE_ARTICLES {

    container 'community.wave.seqera.io/library/duckdb_google-genai:2de7f99e6ef8ab9a'
    secret 'GOOGLE_API_KEY'
    secret 'SPRINGER_META_API_KEY'
    secret 'USER_EMAIL'
    tag { TITLE }

    input:
    tuple val(TITLE), val(SUMMARY), val(LINK), val(JOURNAL_NAME), val(DATE), val(DOI), val(SCREENING_DECISION)
    path RESEARCH_INTERESTS_PATH

    output:
    tuple val(TITLE), val(SUMMARY), val(LINK), val(JOURNAL_NAME), val(DATE), val(DOI), val(SCREENING_DECISION), env(PRIORITY)

    script:
    """
    if [ "${SCREENING_DECISION}" = "NULL" ] || [ "${SCREENING_DECISION}" = "false" ]; then
        PRIORITY="NULL"
    else
        prioritize_articles.py \
--title "${TITLE}" \
--summary "${SUMMARY}" \
--journal_name "${JOURNAL_NAME}" \
--doi "${DOI}" \
--research_interests_path ${RESEARCH_INTERESTS_PATH}

        PRIORITY=`cat priority.txt`
    fi
    """
}

workflow {

    database_path = file(params.database_path)

    if ( !database_path.exists() ) {
        println "Articles database not found. Creating a new one at: ${database_path}."
        println "Upon completion, re-run the workflow."
        db_filename = database_path.name
        db_parent_dir = database_path.parent
        CREATE_ARTICLES_DB(file(params.journal_list), db_filename, db_parent_dir)
    } else {
        journals = channel.fromQuery("SELECT name, feed_url, last_checked FROM sources", db: 'articles_db')

        FETCH_ARTICLES(journals)
        EXTRACT_METADATA(FETCH_ARTICLES.out.flatten())

        articles = EXTRACT_METADATA.out |
            splitCsv(sep: '\t')
        SCREEN_ARTICLES(articles, file(params.research_interests))
        PRIORITIZE_ARTICLES(SCREEN_ARTICLES.out, file(params.research_interests))

        SAVE_ARTICLE(PRIORITIZE_ARTICLES.out, database_path)

        // today = new Date().format("yyyy-MM-dd")
        // sqlExecute("""
        // UPDATE sources
        // SET last_checked = '${today}'
        // """, db: 'articles_db')

    }

}
