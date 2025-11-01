include { batchArticles; filterAndBatch; COLLECT_OUTPUTS; VALIDATE } from '../modules/json'

workflow FROM_JSON {

    take:
        articles_json: Path

    main:
        VALIDATE(articles_json, "import", "validated_articles")
    emit:
        VALIDATE.out

}

workflow TO_JSON {

    take:
        articles_json: Path

    main:
        VALIDATE(articles_json, "export", "prioritized_articles")
        COLLECT_OUTPUTS(VALIDATE.out.collect())

    emit:
        VALIDATE.out

}
