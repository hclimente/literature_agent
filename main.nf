include { fromQuery; sqlInsert } from 'plugin/nf-sqldb'

process FETCH_ARTICLES {

    container 'community.wave.seqera.io/library/pip_feedparser:daf4046ba37d0661'
    tag { JOURNAL_NAME }

    input:
    tuple val(JOURNAL_NAME), val(FEED_URL), val(LAST_CHECKED)

    output:
    path "articles.tsv"

    script:
    """
    fetch_articles.py --journal_name "${JOURNAL_NAME}" --feed_url "${FEED_URL}" --cutoff_date "${LAST_CHECKED}"
    """
}

process SCREEN_ARTICLES {

    container 'community.wave.seqera.io/library/pip_google-adk:581ba88bd7868075'
    secret 'GOOGLE_API_KEY'
    secret 'SPRINGER_META_API_KEY'
    secret 'USER_EMAIL'

    input:
    path ARTICLES_TSV
    path RESEARCH_INTERESTS_PATH

    output:
    path "screened_articles.tsv"

    script:
    """
    screen_articles.py \
--in_articles_tsv ${ARTICLES_TSV} \
--research_interests_path ${RESEARCH_INTERESTS_PATH} \
--out_articles_tsv screened_articles.tsv
    """
}

workflow {

    journals = channel.fromQuery("SELECT name, feed_url, last_checked FROM sources", db: 'articles_db')

    FETCH_ARTICLES(journals)
    SCREEN_ARTICLES(FETCH_ARTICLES.out, file(params.research_interests))

    SCREEN_ARTICLES.out
        .splitCsv(header: true, sep: '\t')
        .map { row -> tuple(row.title, row.journal_name, row.link, row.date) }
        .sqlInsert( into: 'articles', columns: 'title, journal_name, link, date', db: 'articles_db' )

}
