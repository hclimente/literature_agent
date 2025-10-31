include { FETCH_ARTICLES } from '../modules/rss'
include { CREATE_ARTICLES_DB; FETCH_JOURNALS; REMOVE_PROCESSED; SAVE; UPDATE_TIMESTAMPS } from '../modules/db'

include { batchArticles; filterAndBatch } from '../modules/json'

workflow FROM_DUCKDB {

    take:
        journals_tsv

    main:
        db = file(params.duckdb.database_path)

        if ( !db.exists() ) {
            println "Articles database not found. Creating a new one at: ${db}."

            global_cutoff_date = new Date(System.currentTimeMillis() - 15 * 24 * 60 * 60 * 1000).format("yyyy-MM-dd")
            println "Global cutoff date set to: ${global_cutoff_date}"

            db_filename = db.name
            db_parent_dir = db.parent
            CREATE_ARTICLES_DB(file(params.journals_tsv), db_filename, db_parent_dir, global_cutoff_date)
            db = CREATE_ARTICLES_DB.out
        }

        FETCH_JOURNALS(db)

        journals = FETCH_JOURNALS.out
            .splitCsv(header: true, sep: '\t')

        FETCH_ARTICLES(journals, 50)

    emit:
        FETCH_ARTICLES.out

}

workflow REMOVE_ARTICLES_IN_DUCKDB {

    take:
        articles_json

    main:
        REMOVE_PROCESSED(
            batchArticles(articles_json, 1000),
            db
        )

        filtered_articles = batchArticles(REMOVE_PROCESSED.out, params.batch_size)

    emit:
        filtered_articles

}

workflow TO_DUCKDB {

    take:
        articles_json

    main:
        db = file(params.duckdb.database_path)

        SAVE(articles_json, db)
        UPDATE_TIMESTAMPS(SAVE.out.collect(), db)

    emit:
        true

}
