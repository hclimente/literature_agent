include { EXTRACT_METADATA; SCREEN; PRIORITIZE } from './modules/agentic/main'
include { EXTRACT_METADATA as EXTRACT_METADATA_RETRY } from './modules/agentic/main'
include { SCREEN as SCREEN_RETRY } from './modules/agentic/main'
include { PRIORITIZE as PRIORITIZE_RETRY } from './modules/agentic/main'
include { CREATE_ARTICLES_DB; FETCH_JOURNALS; FETCH_ARTICLES; REMOVE_PROCESSED; SAVE; UPDATE_TIMESTAMPS} from './modules/db/main'
include { batchArticles; filterAndBatch } from './lib/batch_utils.nf'

workflow {

    database_path = file(params.database_path)

    if ( !database_path.exists() ) {
        println "Articles database not found. Creating a new one at: ${database_path}."

        global_cutoff_date = new Date(System.currentTimeMillis() - 15 * 24 * 60 * 60 * 1000).format("yyyy-MM-dd")
        println "Global cutoff date set to: ${global_cutoff_date}"

        db_filename = database_path.name
        db_parent_dir = database_path.parent
        CREATE_ARTICLES_DB(file(params.journal_list), db_filename, db_parent_dir, global_cutoff_date)
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

    removed_batches = batchArticles(REMOVE_PROCESSED.out, params.batch_size)
    EXTRACT_METADATA(
        removed_batches,
        file(params.metadata_extraction.system_prompt),
        params.metadata_extraction.model,
        true
    )

    failed_metadata = batchArticles(EXTRACT_METADATA.out.fail, params.batch_size)
    EXTRACT_METADATA_RETRY(
        failed_metadata,
        file(params.metadata_extraction.system_prompt),
        params.metadata_extraction.model,
        false
    )

    metadata_articles = EXTRACT_METADATA.out.pass
        .concat(EXTRACT_METADATA_RETRY.out.pass)
    filtered_metadata = filterAndBatch(metadata_articles, params.batch_size, "metadata_doi", "NULL")
    SCREEN(
        filtered_metadata.no_match,
        file(params.screening.system_prompt),
        file(params.research_interests),
        params.screening.model,
        true
    )

    SCREEN_RETRY(
        SCREEN.out.fail,
        file(params.screening.system_prompt),
        file(params.research_interests),
        params.screening.model,
        false
    )

    screened_articles = SCREEN.out.pass
        .concat(SCREEN_RETRY.out.pass)
    filtered_screened = filterAndBatch(screened_articles, params.batch_size, "screening_decision", "true")
    PRIORITIZE(
        filtered_screened.match,
        file(params.prioritization.system_prompt),
        file(params.research_interests),
        params.prioritization.model,
        true
    )

    PRIORITIZE_RETRY(
        PRIORITIZE.out.fail,
        file(params.prioritization.system_prompt),
        file(params.research_interests),
        params.prioritization.model,
        false
    )

    prioritized_articles = PRIORITIZE.out.pass
        .concat(PRIORITIZE_RETRY.out.pass)
        .concat(filtered_metadata.match)
        .concat(filtered_screened.no_match)
    final_batches = batchArticles(prioritized_articles, 100)

    SAVE(final_batches, database_path)
    UPDATE_TIMESTAMPS(SAVE.out.collect(), database_path)

}
