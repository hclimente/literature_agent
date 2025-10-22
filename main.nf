include { EXTRACT_METADATA } from './modules/agentic/main'
include { EXTRACT_METADATA as EXTRACT_METADATA_FALLBACK } from './modules/agentic/main'
include {  SCREEN; PRIORITIZE } from './modules/agentic/main'
include { CREATE_ARTICLES_DB; FETCH_JOURNALS; FETCH_ARTICLES; REMOVE_PROCESSED; SAVE; UPDATE_TIMESTAMPS} from './modules/db/main'

import groovy.json.JsonOutput

def toJson(article_list) {
    def json = JsonOutput.toJson(article_list)
    json = JsonOutput.prettyPrint(json)
    def tempFile = File.createTempFile("articles_", ".json")
    tempFile.write(json)
    return file(tempFile)
}

workflow {

    database_path = file(params.database_path)

    if ( !database_path.exists() ) {
        println "Articles database not found. Creating a new one at: ${database_path}."
        db_filename = database_path.name
        db_parent_dir = database_path.parent
        CREATE_ARTICLES_DB(file(params.journal_list), db_filename, db_parent_dir)
        database_path = CREATE_ARTICLES_DB.out
    }

    FETCH_JOURNALS(database_path)

    journals = FETCH_JOURNALS.out
        .splitCsv(header: true, sep: '\t')

    FETCH_ARTICLES(journals, 50)
    REMOVE_PROCESSED(FETCH_ARTICLES.out, database_path)

    articles = REMOVE_PROCESSED.out
        .splitJson()
        .flatten()
        .buffer(size: params.batch_size, remainder: true)
        .map { batch -> toJson(batch) }

    EXTRACT_METADATA(
        articles,
        file(params.metadata_extraction.system_prompt),
        params.metadata_extraction.model
    )

    articles_failed_metadata = EXTRACT_METADATA.out.fail
        .splitJson()
        .flatten()
        .buffer(size: params.batch_size, remainder: true)
        .map { batch -> toJson(batch) }

    EXTRACT_METADATA_FALLBACK(
        articles_failed_metadata,
        file(params.metadata_extraction.system_prompt),
        params.metadata_extraction.model
    )

    SCREEN(
        EXTRACT_METADATA.out.pass,
        file(params.screening.system_prompt),
        file(params.research_interests),
        params.screening.model
    )
    PRIORITIZE(
        SCREEN.out,
        file(params.prioritization.system_prompt),
        file(params.research_interests),
        params.prioritization.model
    )

    SAVE(PRIORITIZE.out, database_path)
    UPDATE_TIMESTAMPS(SAVE.out.collect(), database_path)

}
