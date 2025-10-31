include { EXTRACT_MORE_METADATA; REMOVE_PROCESSED; SAVE } from '../modules/zotero'

include { batchArticles; filterAndBatch } from '../modules/json'

workflow COLLECTION_CHECK {

    take:
        articles_json

    main:
        REMOVE_PROCESSED(
            batchArticles(articles_json, 1000),
            params.zotero.user_id,
            params.zotero.collection_id,
            params.zotero.library_type
        )

        filtered_articles = batchArticles(REMOVE_PROCESSED.out, params.batch_size)

    emit:
        filtered_articles

}

workflow TO_ZOTERO {

    take:
        articles_json

    main:
        EXTRACT_MORE_METADATA(articles_json)
        SAVE(
            EXTRACT_MORE_METADATA.out,
            params.zotero.user_id,
            params.zotero.collection_id,
            params.zotero.library_type
        )

    emit:
        true

}
