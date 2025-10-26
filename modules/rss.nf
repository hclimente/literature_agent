process FETCH_ARTICLES {

    container 'community.wave.seqera.io/library/pip_feedparser_pydantic_python-dateutil:e334b7c08b3cb424'
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
