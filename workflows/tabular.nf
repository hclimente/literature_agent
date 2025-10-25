include { FETCH_ARTICLES } from '../modules/rss/main'

include { batchArticles; filterAndBatch } from '../lib/batch_utils.nf'

workflow FROM_TABULAR {

    take:
        journal_list

    main:
        global_cutoff_date = new Date(System.currentTimeMillis() - 15 * 24 * 60 * 60 * 1000).format("yyyy-MM-dd")
        println "Global cutoff date set to: ${global_cutoff_date}"

        journals = channel.fromPath(journal_list)
            .splitCsv(header: true, sep: '\t')
            .map { row ->
                row['last_checked'] = global_cutoff_date
                return row
            }

        FETCH_ARTICLES(journals, 50)

        articles_to_process = batchArticles(FETCH_ARTICLES.out, params.batch_size)

    emit:
        articles_to_process

}
