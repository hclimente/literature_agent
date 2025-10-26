include { FROM_DUCKDB; TO_DUCKDB } from './workflows/duckdb'
include { FROM_JSON; TO_JSON } from './workflows/json'
include { FROM_TABULAR } from './workflows/tabular'
include { TO_ZOTERO } from './workflows/zotero'

include { PROCESS_ARTICLES } from './workflows/articles'

include { batchArticles; filterAndBatch } from './modules/json'

workflow {

    if (params.backend_from == "duckdb") {
        FROM_DUCKDB(file(params.journals_tsv))
        articles_to_process = FROM_DUCKDB.out
    } else if (params.backend_from == "journals_tsv") {
        FROM_TABULAR(file(params.journals_tsv))
        articles_to_process = FROM_TABULAR.out
    } else if (params.backend_from == "articles_json") {
        FROM_JSON(file(params.from_json.input))
        articles_to_process = FROM_JSON.out
    } else {
        error "Unsupported backend: ${params.backend}. Supported backends are 'duckdb', 'journals_tsv', and 'articles_json'."
    }

    PROCESS_ARTICLES(articles_to_process)

    if (params.backend_to == "duckdb") {
        TO_DUCKDB(PROCESS_ARTICLES.out.all_articles)
    } else if (params.backend_to == "zotero") {
        TO_ZOTERO(batchArticles(PROCESS_ARTICLES.out.prioritized_articles, 1000))
    } else if (params.backend_to == "articles_json") {
        TO_JSON(batchArticles(PROCESS_ARTICLES.out.prioritized_articles, 1000))
    } else {
        error "Unsupported backend: ${params.backend}. Supported backends are 'duckdb', 'zotero', and 'articles_json'."
    }

}
