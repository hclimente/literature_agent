include { SAVE } from '../modules/zotero/main'

workflow TO_ZOTERO {

    take:
        articles_json

    main:
        SAVE(
            articles_json,
            params.zotero.user_id,
            params.zotero.collection_id,
            params.zotero.library_type
        )

    emit:
        true

}
