include { fromQuery; sqlInsert; sqlExecute } from 'plugin/nf-sqldb'

process CREATE_ARTICLES_DB {

    container 'community.wave.seqera.io/library/duckdb:1.4.1--3daff581f117ee85'
    publishDir "${DB_PARENT_DIR}", mode: 'copy'

    input:
    path JOURNALS_TSV
    val DB_FILENAME
    val DB_PARENT_DIR

    output:
    path "${DB_FILENAME}"

    script:
    """
    duckdb_create.py \
--journals_tsv ${JOURNALS_TSV} \
--db_path ${DB_FILENAME} \
--global_cutoff_date "2025-10-01"
    """

}

process FETCH_ARTICLES {

    container 'community.wave.seqera.io/library/pip_feedparser_python-dateutil:2bbb86f41337cff4'
    tag { JOURNAL_NAME }

    input:
    tuple val(JOURNAL_NAME), val(FEED_URL), val(LAST_CHECKED)
    val MAX_ITEMS

    output:
    path "articles.json", optional: true

    script:
    """
    fetch_articles.py \
--journal_name "${JOURNAL_NAME}" \
--feed_url "${FEED_URL}" \
--cutoff_date "${LAST_CHECKED}" \
--max_items ${MAX_ITEMS}
    """
}

process REMOVE_PROCESSED {

    container 'community.wave.seqera.io/library/duckdb:1.4.1--3daff581f117ee85'

    input:
    path ARTICLES_JSON
    path DB_PATH

    output:
    path "unprocessed_articles.json"

    """
    duckdb_remove_processed.py \
--db_path ${DB_PATH} \
--articles_json ${ARTICLES_JSON} \
--output_json unprocessed_articles.json
    """

}


process SAVE {

    container 'community.wave.seqera.io/library/duckdb:1.4.1--3daff581f117ee85'
    tag { TITLE }

    input:
    tuple val(TITLE), val(SUMMARY), val(LINK), val(JOURNAL_NAME), val(DATE), val(DOI), val(SCREENING_DECISION), val(PRIORITY)
    path DB_PATH

    output:
    val true

    script:
    """
    duckdb_insert_article.py \
--db_path ${DB_PATH} \
--title "${TITLE}" \
--summary "${SUMMARY}" \
--link "${LINK}" \
--journal_name "${JOURNAL_NAME}" \
--date "${DATE}" \
--doi "${DOI}" \
--screening_decision "${SCREENING_DECISION}" \
--priority "${PRIORITY}"
    """

}

process UPDATE_TIMESTAMPS {

    container 'community.wave.seqera.io/library/duckdb:1.4.1--3daff581f117ee85'

    input:
    val COMPLETION_SIGNALS
    path DB_PATH

    output:
    val true

    script:
    today = new Date().format("yyyy-MM-dd")
    """
    duckdb ${DB_PATH} "UPDATE sources SET last_checked = '${today}'"
    """

}

process EXTRACT_METADATA {

    container 'community.wave.seqera.io/library/pip_google-genai:2e5c0f1812c5cbda'
    label 'gemini_api'
    secret 'GOOGLE_API_KEY'

    input:
    file ARTICLE_FILE
    file SYSTEM_PROMPT
    val MODEL

    output:
    file "metadata.tsv"

    script:
    """
    extract_metadata.py \
--article_file ${ARTICLE_FILE} \
--system_prompt_path ${SYSTEM_PROMPT} \
--model ${MODEL}
    """

}

process SCREEN {

    container 'community.wave.seqera.io/library/pip_google-genai:2e5c0f1812c5cbda'
    label 'gemini_api'
    secret 'GOOGLE_API_KEY'
    secret 'SPRINGER_META_API_KEY'
    secret 'USER_EMAIL'
    tag { TITLE }

    input:
    tuple val(TITLE), val(SUMMARY), val(LINK), val(JOURNAL_NAME), val(DATE), val(DOI)
    file SYSTEM_PROMPT
    path RESEARCH_INTERESTS_PATH
    val MODEL

    output:
    tuple val(TITLE), val(SUMMARY), val(LINK), val(JOURNAL_NAME), val(DATE), val(DOI), env(SCREENING_DECISION)

    script:
    """
    if [ "${DOI}" = "NULL" ]; then
        SCREENING_DECISION="NULL"
    else
        screen_articles.py \
--title "${TITLE}" \
--summary "${SUMMARY}" \
--journal_name "${JOURNAL_NAME}" \
--doi "${DOI}" \
--system_prompt_path ${SYSTEM_PROMPT} \
--research_interests_path ${RESEARCH_INTERESTS_PATH} \
--model ${MODEL}

        SCREENING_DECISION=`cat decision.txt`
    fi
    """
}

process PRIORITIZE {

    container 'community.wave.seqera.io/library/pip_google-genai:2e5c0f1812c5cbda'
    label 'gemini_api'
    secret 'GOOGLE_API_KEY'
    secret 'SPRINGER_META_API_KEY'
    secret 'USER_EMAIL'
    tag { TITLE }

    input:
    tuple val(TITLE), val(SUMMARY), val(LINK), val(JOURNAL_NAME), val(DATE), val(DOI), val(SCREENING_DECISION)
    path SYSTEM_PROMPT
    path RESEARCH_INTERESTS_PATH
    val MODEL

    output:
    tuple val(TITLE), val(SUMMARY), val(LINK), val(JOURNAL_NAME), val(DATE), val(DOI), val(SCREENING_DECISION), env(PRIORITY)

    script:
    """
    if [ "${SCREENING_DECISION}" = "NULL" ] || [ "${SCREENING_DECISION}" = "false" ]; then
        PRIORITY="NULL"
    else
        prioritize_articles.py \
--title "${TITLE}" \
--summary "${SUMMARY}" \
--journal_name "${JOURNAL_NAME}" \
--doi "${DOI}" \
--system_prompt_path ${SYSTEM_PROMPT} \
--research_interests_path ${RESEARCH_INTERESTS_PATH} \
--model ${MODEL}

        PRIORITY=`cat priority.txt`
    fi
    """
}

workflow {

    database_path = file(params.database_path)

    if ( !database_path.exists() ) {
        println "Articles database not found. Creating a new one at: ${database_path}."
        println "Upon completion, re-run the workflow."
        db_filename = database_path.name
        db_parent_dir = database_path.parent
        CREATE_ARTICLES_DB(file(params.journal_list), db_filename, db_parent_dir)
    } else {
        journals = channel.fromQuery("SELECT name, feed_url, last_checked FROM sources", db: 'articles_db')

        FETCH_ARTICLES(journals, 50)
        REMOVE_PROCESSED(FETCH_ARTICLES.out, database_path)

        EXTRACT_METADATA(
            REMOVE_PROCESSED.out.flatten().splitJson().flatten() | take(5),
            file(params.metadata_extraction.system_prompt),
            params.metadata_extraction.model
        )

        // articles = EXTRACT_METADATA.out |
        //     splitCsv(sep: '\t')
        // SCREEN(
        //     articles,
        //     file(params.screening.system_prompt),
        //     file(params.research_interests),
        //     params.screening.model
        // )
        // PRIORITIZE(
        //     SCREEN.out,
        //     file(params.prioritization.system_prompt),
        //     file(params.research_interests),
        //     params.prioritization.model
        // )

        // SAVE(PRIORITIZE.out, database_path)

        // all_saved = SAVE.out.collect()
        // UPDATE_TIMESTAMPS(all_saved, database_path)

    }

}
