include { fromQuery } from 'plugin/nf-sqldb'

process FETCH_ARTICLES {

    container 'community.wave.seqera.io/library/pip_feedparser:daf4046ba37d0661'
    tag { journal_name }

    input:
    tuple val(journal_name), val(feed_url), val(last_checked)

    output:
    path "articles.tsv"

    script:
    """
    fetch_articles.py --feed_url "${feed_url}" --cutoff_date "${last_checked}"
    """
}

process SCREEN_ARTICLES {

    container 'community.wave.seqera.io/library/pip_google-adk:581ba88bd7868075'
    secret 'GOOGLE_API_KEY'
    secret 'USER_EMAIL'

    input:
    path articles_tsv

    output:
    path "screened_articles.tsv"

    script:
    """
    screen_articles.py --in_articles_tsv ${articles_tsv} --out_articles_tsv screened_articles.tsv
    """
}

workflow {

    journals = channel.fromQuery("SELECT name, feed_url, last_checked FROM sources", db: 'articles_db')

    FETCH_ARTICLES(journals)
    SCREEN_ARTICLES(FETCH_ARTICLES.out)

}
