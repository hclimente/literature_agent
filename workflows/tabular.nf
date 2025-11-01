include { samplesheetToList } from 'plugin/nf-schema'

include { FETCH_ARTICLES } from '../modules/rss'

include { batchArticles; filterAndBatch } from '../modules/json'

workflow FROM_TABULAR {

    take:
        journals_tsv: Path
        batch_size: Integer
        days_back: Integer
        debug_mode: Boolean

    main:
        global_cutoff_date = new Date(System.currentTimeMillis() - days_back * 24 * 60 * 60 * 1000).format("yyyy-MM-dd")
        println "Global cutoff date set to ${days_back} days back (${global_cutoff_date})."

        journals = Channel.fromList(samplesheetToList(journals_tsv, "assets/schema_journals_tsv.json"))
            .map { row ->
                tuple(row[0], row[1], global_cutoff_date)
            }
        journals = debug_mode ? journals.take(5) : journals

        FETCH_ARTICLES(journals, 50)

        articles_to_process = batchArticles(FETCH_ARTICLES.out, batch_size)

    emit:
        articles_to_process

}
