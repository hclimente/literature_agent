include { fromQuery; sqlInsert; sqlExecute } from 'plugin/nf-sqldb'

// Function to update processing flags for existing articles
def updateArticlesFlag(channel, flagColumn, db = 'articles_db') {
    return channel
        .splitCsv(header: true, sep: '\t')
        .map { row -> 
            sqlExecute(
                db: db,
                statement: """
                    UPDATE articles SET ${flagColumn} = ${row.decision} WHERE link = '${row.link}'
                """
            )
        }
}

// Function to get articles by processing stage for incremental processing
def getUnprocessedArticles(flagColumn, db = 'articles_db') {
    return channel.fromQuery(
        "SELECT * FROM articles WHERE ${flagColumn} IS NULL", 
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
                    INSERT OR IGNORE INTO articles (title, journal_name, link, date, abstract, fetched) 
                    VALUES ('${row.title}', '${row.journal_name}', '${row.link}', '${row.date}', '${row.abstract ?: ''}', true)
                """
            )
        }
}

process CREATE_ARTICLES_DB {

    container 'duckdb/duckdb:1.4.1'
    publishDir "${DB_PARENT_DIR}", mode: 'copy'

    input:
    path JOURNALS_TSV
    val DB_FILENAME
    val DB_PARENT_DIR

    output:
    path DATABASE_PATH

    script:
    """
    create_db.py --journals_tsv ${JOURNALS_TSV} --db_path "${DB_FILENAME}"
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
--cutoff_date "${LAST_CHECKED}" \
--max_items 20
    """
}

process SCREEN_ARTICLES {

    container 'community.wave.seqera.io/library/pip_google-adk:581ba88bd7868075'
    secret 'GOOGLE_API_KEY'
    secret 'SPRINGER_META_API_KEY'
    secret 'USER_EMAIL'

    input:
    path ARTICLES_TSV
    path RESEARCH_INTERESTS_PATH

    output:
    path "screened_articles.tsv"

    script:
    """
    screen_articles.py \
--in_articles_tsv ${ARTICLES_TSV} \
--research_interests_path ${RESEARCH_INTERESTS_PATH} \
--out_articles_tsv screened_articles.tsv
    """
}

process PRIORITIZE_ARTICLES {

    container 'community.wave.seqera.io/library/pip_google-adk:581ba88bd7868075'
    secret 'GOOGLE_API_KEY'
    secret 'SPRINGER_META_API_KEY'
    secret 'USER_EMAIL'

    input:
    path ARTICLES_TSV
    path RESEARCH_INTERESTS_PATH

    output:
    path "prioritized_articles.tsv"

    script:
    """
    prioritize_articles.py \
--in_articles_tsv ${ARTICLES_TSV} \
--research_interests_path ${RESEARCH_INTERESTS_PATH} \
--out_articles_tsv prioritized_articles.tsv
    """
}

workflow {

    database_path = file(params.database_path)

    if ( !database_path.exists() ) {
        println "Articles database not found. Creating a new one at: ${database_path}."
        println "Upon completion, re-run the workflow."
        // TODO this process crashes, there are errors with the Docker container
        db_filename = database_path.getBaseName()
        db_parent_dir = database_path.getParent()
        CREATE_ARTICLES_DB(file(params.journal_list), db_filename, db_parent_dir)
    } else {
        journals = channel.fromQuery("SELECT name, feed_url, last_checked FROM sources", db: 'articles_db')

        // Fetch articles and insert new ones with fetched=true
        FETCH_ARTICLES(journals)
        insertNewArticles(FETCH_ARTICLES.out)

        // Get articles that haven't been screened yet
        unscreened_articles = getUnprocessedArticles('screened')

        SCREEN_ARTICLES(unscreened_articles, file(params.research_interests))
        updateArticlesFlag(SCREEN_ARTICLES.out, 'screened')

        // Get articles that haven't been prioritized yet
        unprioritized_articles = getUnprocessedArticles('priority')

        PRIORITIZE_ARTICLES(unprioritized_articles, file(params.research_interests))
        updateArticlesFlag(PRIORITIZE_ARTICLES.out, 'priority')
    }

}
