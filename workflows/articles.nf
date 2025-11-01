include { EXTRACT_METADATA; SCREEN; PRIORITIZE } from '../modules/agentic'
include { EXTRACT_METADATA as EXTRACT_METADATA_RETRY } from '../modules/agentic'
include { SCREEN as SCREEN_RETRY } from '../modules/agentic'
include { PRIORITIZE as PRIORITIZE_RETRY } from '../modules/agentic'

include { batchArticles; filterAndBatch } from '../modules/json'

workflow PROCESS_ARTICLES {

    take:
        articles_json: Path
        batch_size: Integer
        metadata_params: Tuple<Path, String>
        screening_params: Tuple<Path, String>
        prioritization_params: Tuple<Path, String>
        research_interests: Path
        debug_mode: Boolean

    main:
        EXTRACT_METADATA(
            articles_json,
            metadata_params,
            true,
            debug_mode
        )

        failed_metadata = batchArticles(EXTRACT_METADATA.out.fail, batch_size)
        EXTRACT_METADATA_RETRY(
            failed_metadata,
            metadata_params,
            false,
            debug_mode
        )

        metadata_articles = EXTRACT_METADATA.out.pass
            .concat(EXTRACT_METADATA_RETRY.out.pass)
        filtered_metadata = filterAndBatch(metadata_articles, batch_size, "doi", null)
        SCREEN(
            filtered_metadata.no_match,
            screening_params,
            research_interests,
            true,
            debug_mode
        )

        SCREEN_RETRY(
            SCREEN.out.fail.filter { it != null },
            screening_params,
            research_interests,
            false,
            debug_mode
        )

        screened_articles = SCREEN.out.pass
            .concat(SCREEN_RETRY.out.pass)
        filtered_screened = filterAndBatch(screened_articles, batch_size, "screening_decision", true)
        PRIORITIZE(
            filtered_screened.match,
            prioritization_params,
            research_interests,
            true,
            debug_mode
        )

        PRIORITIZE_RETRY(
            PRIORITIZE.out.fail.filter { it != null },
            prioritization_params,
            research_interests,
            false,
            debug_mode
        )

        prioritized_articles = PRIORITIZE.out.pass
            .concat(PRIORITIZE_RETRY.out.pass)
        all_articles = prioritized_articles
            .concat(filtered_metadata.match)
            .concat(filtered_screened.no_match)
        final_batches = batchArticles(all_articles, 100)

    emit:
        prioritized_articles = prioritized_articles
        all_articles = final_batches
}
