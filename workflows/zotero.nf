include { EXTRACT_MORE_METADATA; SAVE } from '../modules/zotero/main'

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
