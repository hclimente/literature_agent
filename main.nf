include { fromQuery; sqlInsert } from 'plugin/nf-sqldb'

process CREATE_ARTICLES_DB {

    container 'duckdb/duckdb:1.4.1'
    publishDir "${DB_PARENT_DIR}", mode: 'copy'

    input:
    val DB_FILENAME
    val DB_PARENT_DIR

    output:
    path DATABASE_PATH

    script:
    """
    create_db.py --db_path "${DB_FILENAME}"
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
        CREATE_ARTICLES_DB(db_filename, db_parent_dir)
    } else {
        journals = channel.fromQuery("SELECT name, feed_url, last_checked FROM sources", db: 'articles_db')

        FETCH_ARTICLES(journals)

        FETCH_ARTICLES.out
            .collectFile(name: 'all_articles.tsv', storeDir: params.outdir)
            .splitText(by: 50, keepHeader: true, file: true)
            .set { all_articles }

        SCREEN_ARTICLES(all_articles, file(params.research_interests))

        SCREEN_ARTICLES.out
            .collectFile(name: 'screened_articles.tsv', storeDir: params.outdir)
            .splitText(by: 50, keepHeader: true, file: true)
            .set { screened_articles }

        PRIORITIZE_ARTICLES(SCREEN_ARTICLES.out, file(params.research_interests))

        PRIORITIZE_ARTICLES.out
            .collectFile(name: 'prioritized_articles.tsv', storeDir: params.outdir)
            .splitText(by: 50, keepHeader: true, file: true)
            .set { prioritized_articles }

        // SCREEN_ARTICLES.out
        //     .splitCsv(header: true, sep: '\t')
        //     .map { row -> tuple(row.title, row.journal_name, row.link, row.date) }
        //     .sqlInsert( into: 'articles', columns: 'title, journal_name, link, date', db: 'articles_db' )
    }

}
