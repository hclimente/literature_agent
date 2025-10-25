include { FROM_DUCKDB; TO_DUCKDB } from './workflows/duckdb.nf'
include { FROM_TABULAR } from './workflows/tabular.nf'
include { TO_ZOTERO } from './workflows/zotero.nf'

include { PROCESS_ARTICLES } from './workflows/articles.nf'

include { batchArticles; filterAndBatch } from './lib/batch_utils.nf'

workflow {

    if (params.backend_from == "duckdb") {
        FROM_DUCKDB(file(params.journal_list))
        articles_to_process = FROM_DUCKDB.out
    } else if (params.backend_from == "tsv") {
        FROM_TABULAR(file(params.journal_list))
        articles_to_process = FROM_TABULAR.out
    } else {
        error "Unsupported backend: ${params.backend}. Supported backends are 'duckdb' and 'tsv'."
    }

    PROCESS_ARTICLES(articles_to_process)

    if (params.backend_to == "duckdb") {
        TO_DUCKDB(PROCESS_ARTICLES.out.all_articles)
    } else if (params.backend_to == "zotero") {
        TO_ZOTERO(batchArticles(PROCESS_ARTICLES.out.prioritized_articles, 1000))
    } else {
        error "Unsupported backend: ${params.backend}. Supported backends are 'duckdb' and 'zotero'."
    }
}
