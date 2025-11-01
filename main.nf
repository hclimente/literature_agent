// include { validateParameters } from 'plugin/nf-schema'

include { FROM_DUCKDB; REMOVE_ARTICLES_IN_DUCKDB; TO_DUCKDB } from './workflows/duckdb'
include { FROM_JSON; TO_JSON } from './workflows/json'
include { FROM_TABULAR } from './workflows/tabular'
include { COLLECTION_CHECK; TO_ZOTERO } from './workflows/zotero'

include { PROCESS_ARTICLES } from './workflows/articles'

include { batchArticles; filterAndBatch } from './modules/json'

params {
    // ===========================
    // General Configuration
    // ===========================
    research_interests: Path
    journals_tsv: Path

    // ===========================
    // Backend Configuration
    // ===========================
    from: String                 = "journals_tsv"
    from_json_input: Path        = "articles.json"
    from_duckdb_input: Path      = "papers_please.duckdb"

    to: String                   = "articles_json"
    to_json_outdir: Path         = "./results"

    zotero_user_id: String
    zotero_collection_id: String
    zotero_library_type: String  = "user"

    days_back: Integer           = 8

    // ===========================
    // LLM Models Configuration
    // ===========================
    batch_size: Integer                     = 10
    metadata_extraction_model: String       = "gemini-2.5-flash-lite"
    metadata_extraction_system_prompt: Path = "${projectDir}/prompts/metadata_extraction.md"
    screening_model: String                 = "gemini-2.5-flash-lite"
    screening_system_prompt: Path           = "${projectDir}/prompts/screening.md"
    prioritization_model: String            = "gemini-2.5-flash-lite"
    prioritization_system_prompt: Path      = "${projectDir}/prompts/prioritization.md"

    // ===========================
    // Others
    // ===========================
    debug: Boolean              = false

}

workflow {

    // validateParameters()

    if (params.from == "duckdb") {
        FROM_DUCKDB(file(params.journals_tsv), params.days_back)
        fetched_articles = FROM_DUCKDB.out
    } else if (params.from == "journals_tsv") {
        FROM_TABULAR(file(params.journals_tsv), params.batch_size, params.days_back, params.debug)
        fetched_articles = FROM_TABULAR.out
    } else if (params.from == "articles_json") {
        FROM_JSON(file(params.from_json_input))
        fetched_articles = FROM_JSON.out
    } else {
        error "Unsupported from: ${params.from}. Supported backends: 'articles_json', 'duckdb', 'journals_tsv'."
    }

    if (params.to == "zotero") {
        COLLECTION_CHECK(
            fetched_articles,
            params.zotero_user_id,
            params.zotero_collection_id,
            params.zotero_library_type
        )
        articles_to_process = COLLECTION_CHECK.out.filtered_articles
    } else if (params.to == "duckdb") {
        REMOVE_ARTICLES_IN_DUCKDB(
            fetched_articles,
            file(params.from_duckdb_input)
        )
        articles_to_process = REMOVE_ARTICLES_IN_DUCKDB.out.all_articles
    } else {
        articles_to_process = fetched_articles
    }

    PROCESS_ARTICLES(
        articles_to_process,
        params.batch_size,
        [file(params.metadata_extraction_system_prompt), params.metadata_extraction_model],
        [file(params.screening_system_prompt), params.screening_model],
        [file(params.prioritization_system_prompt), params.prioritization_model],
        file(params.research_interests),
        params.debug,
    )

    if (params.to == "duckdb") {
        TO_DUCKDB(PROCESS_ARTICLES.out.all_articles)
    } else if (params.to == "zotero") {
        TO_ZOTERO(
            batchArticles(PROCESS_ARTICLES.out.prioritized_articles, 10),
            params.zotero_user_id,
            params.zotero_collection_id,
            params.zotero_library_type
        )
    } else if (params.to == "articles_json") {
        TO_JSON(batchArticles(PROCESS_ARTICLES.out.all_articles, 1000))
        output_ch = TO_JSON.out
    } else {
        error "Unsupported to: ${params.to}. Supported backends: 'articles_json' 'duckdb', 'zotero'."
    }

    // publish:
    // output = output_ch

}

// output {
//     output {}
// }
