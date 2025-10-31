include { validateParameters } from 'plugin/nf-schema'

include { FROM_DUCKDB; REMOVE_ARTICLES_IN_DUCKDB; TO_DUCKDB } from './workflows/duckdb'
include { FROM_JSON; TO_JSON } from './workflows/json'
include { FROM_TABULAR } from './workflows/tabular'
include { COLLECTION_CHECK; TO_ZOTERO } from './workflows/zotero'

include { PROCESS_ARTICLES } from './workflows/articles'

include { batchArticles; filterAndBatch } from './modules/json'

workflow {

    validateParameters()

    if (params.from == "duckdb") {
        FROM_DUCKDB(file(params.journals_tsv))
        fetched_articles = FROM_DUCKDB.out
    } else if (params.from == "journals_tsv") {
        FROM_TABULAR(file(params.journals_tsv))
        fetched_articles = FROM_TABULAR.out
    } else if (params.from == "articles_json") {
        FROM_JSON(file(params.from_json_input))
        fetched_articles = FROM_JSON.out
    } else {
        error "Unsupported from: ${params.from}. Supported backends: 'articles_json', 'duckdb', 'journals_tsv'."
    }

    if (params.to == "zotero") {
        COLLECTION_CHECK(fetched_articles)
        articles_to_process = COLLECTION_CHECK.out.filtered_articles
    } else if (params.to == "duckdb") {
        REMOVE_ARTICLES_IN_DUCKDB(fetched_articles)
        articles_to_process = REMOVE_ARTICLES_IN_DUCKDB.out.all_articles
    } else {
        articles_to_process = fetched_articles
    }

    PROCESS_ARTICLES(articles_to_process)

    if (params.to == "duckdb") {
        TO_DUCKDB(PROCESS_ARTICLES.out.all_articles)
    } else if (params.to == "zotero") {
        TO_ZOTERO(batchArticles(PROCESS_ARTICLES.out.prioritized_articles, 10))
    } else if (params.to == "articles_json") {
        TO_JSON(batchArticles(PROCESS_ARTICLES.out.all_articles, 1000))
    } else {
        error "Unsupported to: ${params.to}. Supported backends: 'articles_json' 'duckdb', 'zotero'."
    }

}
