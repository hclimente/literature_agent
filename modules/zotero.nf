process EXTRACT_MORE_METADATA {

    container 'community.wave.seqera.io/library/pip_habanero_pydantic:3882895f50c53509'

    input:
    path ARTICLES_JSON

    output:
    path 'articles_with_extra_metadata.json'

    script:
    """
    crossref_annotate_doi.py \
--articles_json ${ARTICLES_JSON} \
--error_strategy include
    """

}

process REMOVE_PROCESSED {

    container 'community.wave.seqera.io/library/pip_pydantic_pyzotero:ba16c1f9d97e42dc'
    secret 'ZOTERO_API_KEY'

    input:
    path ARTICLES_JSON
    val ZOTERO_USER_ID
    val ZOTERO_COLLECTION_ID
    val ZOTERO_LIBRARY_TYPE

    output:
    path "unprocessed_articles.json", optional: true

    script:
    """
    zotero_remove_processed.py \
--articles_json ${ARTICLES_JSON} \
--zotero_user_id ${ZOTERO_USER_ID} \
--zotero_library_type ${ZOTERO_LIBRARY_TYPE} \
--zotero_collection_id ${ZOTERO_COLLECTION_ID}
    """

}


process SAVE {

    container 'community.wave.seqera.io/library/pip_pydantic_pyzotero:ba16c1f9d97e42dc'
    secret 'ZOTERO_API_KEY'

    input:
    path ARTICLES_JSON
    val ZOTERO_USER_ID
    val ZOTERO_COLLECTION_ID
    val ZOTERO_LIBRARY_TYPE

    script:
    """
    zotero_insert_article.py \
--articles_json ${ARTICLES_JSON} \
--zotero_user_id ${ZOTERO_USER_ID} \
--zotero_library_type ${ZOTERO_LIBRARY_TYPE} \
--zotero_collection_id ${ZOTERO_COLLECTION_ID}
    """

}
