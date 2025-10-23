include { EXTRACT_METADATA; SCREEN; PRIORITIZE } from './modules/agentic/main'
include { EXTRACT_METADATA as EXTRACT_METADATA_RETRY } from './modules/agentic/main'
include { SCREEN as SCREEN_RETRY } from './modules/agentic/main'
include { PRIORITIZE as PRIORITIZE_RETRY } from './modules/agentic/main'
include { CREATE_ARTICLES_DB; FETCH_JOURNALS; FETCH_ARTICLES; REMOVE_PROCESSED; SAVE; UPDATE_TIMESTAMPS} from './modules/db/main'

import groovy.json.JsonOutput

def toJson(article_list) {
    def json = JsonOutput.toJson(article_list)
    json = JsonOutput.prettyPrint(json)
    def tempFile = File.createTempFile("articles_", ".json")
    tempFile.write(json)
    return file(tempFile)
}

def processBatch(channel, batch_size) {
    return channel
        .splitJson()
        .flatten()
        .buffer(size: batch_size, remainder: true)
        .map { batch -> toJson(batch) }
        .take(10)
}

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


    REMOVE_PROCESSED(
        processBatch(FETCH_ARTICLES.out, 1000),
        database_path
    )

    EXTRACT_METADATA(
        processBatch(REMOVE_PROCESSED.out, params.batch_size),
        file(params.metadata_extraction.system_prompt),
        params.metadata_extraction.model,
        true
    )

    EXTRACT_METADATA_RETRY(
        processBatch(EXTRACT_METADATA.out.fail, params.batch_size),
        file(params.metadata_extraction.system_prompt),
        params.metadata_extraction.model,
        false
    )

    SCREEN(
        EXTRACT_METADATA.out.pass,
        file(params.screening.system_prompt),
        file(params.research_interests),
        params.screening.model,
        true
    )

    SCREEN_RETRY(
        processBatch(SCREEN.out.fail, params.batch_size),
        file(params.screening.system_prompt),
        file(params.research_interests),
        params.screening.model,
        false
    )

    PRIORITIZE(
        SCREEN.out.pass,
        file(params.prioritization.system_prompt),
        file(params.research_interests),
        params.prioritization.model,
        true
    )

    PRIORITIZE_RETRY(
        processBatch(PRIORITIZE.out.fail, params.batch_size),
        file(params.prioritization.system_prompt),
        file(params.research_interests),
        params.prioritization.model,
        false
    )

    prioritized_articles = PRIORITIZE.out.pass
        .concat(PRIORITIZE_RETRY.out.pass)

    SAVE(prioritized_articles, database_path)
    UPDATE_TIMESTAMPS(SAVE.out.collect(), database_path)

}
