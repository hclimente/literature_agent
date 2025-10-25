include { EXTRACT_METADATA; SCREEN; PRIORITIZE } from '../modules/agentic/main'
include { EXTRACT_METADATA as EXTRACT_METADATA_RETRY } from '../modules/agentic/main'
include { SCREEN as SCREEN_RETRY } from '../modules/agentic/main'
include { PRIORITIZE as PRIORITIZE_RETRY } from '../modules/agentic/main'

include { batchArticles; filterAndBatch } from '../lib/batch_utils.nf'

workflow PROCESS_ARTICLES {

    take:
        articles_json

    main:
        EXTRACT_METADATA(
            articles_json,
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
        filtered_screened = filterAndBatch(screened_articles, params.batch_size, "screening_decision", true)
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
        all_articles = prioritized_articles
            .concat(filtered_metadata.match)
            .concat(filtered_screened.no_match)
        final_batches = batchArticles(all_articles, 100)

    emit:
        prioritized_articles = prioritized_articles
        all_articles = final_batches
}
