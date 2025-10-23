process CREATE_ARTICLES_DB {

    container 'community.wave.seqera.io/library/duckdb:1.4.1--3daff581f117ee85'
    publishDir "${DB_PARENT_DIR}", mode: 'copy'

    input:
    path JOURNALS_TSV
    val DB_FILENAME
    val DB_PARENT_DIR
    val GLOBAL_CUTOFF_DATE

    output:
    path "${DB_FILENAME}"

    script:
    """
    duckdb_create.py \
--journals_tsv ${JOURNALS_TSV} \
--db_path ${DB_FILENAME} \
--global_cutoff_date ${GLOBAL_CUTOFF_DATE}
    """

}

process FETCH_JOURNALS {

    container 'community.wave.seqera.io/library/duckdb:1.4.1--3daff581f117ee85'

    input:
    path DB_PATH

    output:
    path "journals.tsv"

    """
    duckdb_extract_fields.py \
--db_path ${DB_PATH} \
--table sources \
--columns "name, feed_url, last_checked" \
--output_tsv journals.tsv
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
    path "unprocessed_articles.json", optional: true

    """
    duckdb_remove_processed.py \
--db_path ${DB_PATH} \
--articles_json ${ARTICLES_JSON} \
--output_json unprocessed_articles.json
    """

}


process SAVE {

    container 'community.wave.seqera.io/library/duckdb:1.4.1--3daff581f117ee85'

    input:
    path ARTICLES_JSON
    path DB_PATH

    output:
    val true

    script:
    """
    duckdb_insert_article.py \
--db_path ${DB_PATH} \
--articles_json ${ARTICLES_JSON}
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
