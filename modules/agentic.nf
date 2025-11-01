nextflow.preview.types = true

process EXTRACT_METADATA {

    container 'community.wave.seqera.io/library/pip_google-genai:2e5c0f1812c5cbda'
    label 'gemini_api'
    secret 'GOOGLE_API_KEY'
    secret 'SPRINGER_META_API_KEY'
    secret 'USER_EMAIL'

    input:
    ARTICLES_JSON: Path
    (SYSTEM_PROMPT, MODEL): Tuple<Path, String>
    ALLOW_QC_ERRORS: Boolean
    DEBUG: Boolean

    output:
    pass = file("metadata_pass.json", optional: true)
    fail = file("metadata_fail.json", optional: true)

    script:
    """
    llm_process_articles.py \
--articles_json ${ARTICLES_JSON} \
${DEBUG ? '--debug' : ''} \
metadata \
--system_prompt_path ${SYSTEM_PROMPT} \
--model ${MODEL} \
--allow_qc_errors ${ALLOW_QC_ERRORS}
    """

}

process SCREEN {

    container 'community.wave.seqera.io/library/pip_google-genai:2e5c0f1812c5cbda'
    label 'gemini_api'
    secret 'GOOGLE_API_KEY'
    secret 'SPRINGER_META_API_KEY'
    secret 'USER_EMAIL'

    input:
    ARTICLES_JSON: Path
    (SYSTEM_PROMPT, MODEL): Tuple<Path, String>
    RESEARCH_INTERESTS_PATH: Path
    ALLOW_QC_ERRORS: Boolean
    DEBUG: Boolean

    output:
    pass = file("screening_pass.json", optional: true)
    fail = file("screening_fail.json", optional: true)

    script:
    """
    llm_process_articles.py \
--articles_json ${ARTICLES_JSON} \
${DEBUG ? '--debug' : ''} \
screening \
--system_prompt_path ${SYSTEM_PROMPT} \
--research_interests_path ${RESEARCH_INTERESTS_PATH} \
--model ${MODEL} \
--allow_qc_errors ${ALLOW_QC_ERRORS}
    """
}

process PRIORITIZE {

    container 'community.wave.seqera.io/library/pip_google-genai:2e5c0f1812c5cbda'
    label 'gemini_api'
    secret 'GOOGLE_API_KEY'
    secret 'SPRINGER_META_API_KEY'
    secret 'USER_EMAIL'

    input:
    ARTICLES_JSON: Path
    (SYSTEM_PROMPT, MODEL): Tuple<Path, String>
    RESEARCH_INTERESTS_PATH: Path
    ALLOW_QC_ERRORS: Boolean
    DEBUG: Boolean

    output:
    pass = file("priority_pass.json", optional: true)
    fail = file("priority_fail.json", optional: true)

    script:
    """
    llm_process_articles.py \
--articles_json ${ARTICLES_JSON} \
${DEBUG ? '--debug' : ''} \
priority \
--system_prompt_path ${SYSTEM_PROMPT} \
--research_interests_path ${RESEARCH_INTERESTS_PATH} \
--model ${MODEL} \
--allow_qc_errors ${ALLOW_QC_ERRORS}
    """
}
