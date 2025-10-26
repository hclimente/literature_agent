include { FETCH_ARTICLES } from '../modules/rss'
include { CREATE_ARTICLES_DB; FETCH_JOURNALS; REMOVE_PROCESSED; SAVE; UPDATE_TIMESTAMPS } from '../modules/db'

include { batchArticles; filterAndBatch } from '../modules/json'

workflow FROM_DUCKDB {

    take:
        journals_tsv

    main:
        database_path = file(params.database_path)

        if ( !database_path.exists() ) {
            println "Articles database not found. Creating a new one at: ${database_path}."

            global_cutoff_date = new Date(System.currentTimeMillis() - 15 * 24 * 60 * 60 * 1000).format("yyyy-MM-dd")
            println "Global cutoff date set to: ${global_cutoff_date}"

            db_filename = database_path.name
            db_parent_dir = database_path.parent
            CREATE_ARTICLES_DB(file(params.journals_tsv), db_filename, db_parent_dir, global_cutoff_date)
            database_path = CREATE_ARTICLES_DB.out
        }

        FETCH_JOURNALS(database_path)

        journals = FETCH_JOURNALS.out
            .splitCsv(header: true, sep: '\t')

        FETCH_ARTICLES(journals, 50)

        fetched_batches = batchArticles(FETCH_ARTICLES.out, 1000)
        REMOVE_PROCESSED(
            fetched_batches,
            database_path
        )

        articles_to_process = batchArticles(REMOVE_PROCESSED.out, params.batch_size)

    emit:
        articles_to_process

}

workflow TO_DUCKDB {

    take:
        articles_json

    main:
        database_path = file(params.database_path)

        SAVE(articles_json, database_path)
        UPDATE_TIMESTAMPS(SAVE.out.collect(), database_path)

    emit:
        true

}
