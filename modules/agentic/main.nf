process EXTRACT_METADATA {

    container 'community.wave.seqera.io/library/pip_google-genai:2e5c0f1812c5cbda'
    label 'gemini_api'
    secret 'GOOGLE_API_KEY'
    secret 'SPRINGER_META_API_KEY'
    secret 'USER_EMAIL'

    input:
    path ARTICLES_JSON
    path SYSTEM_PROMPT
    val MODEL
    val ALLOW_QC_ERRORS

    output:
    path "metadata_pass.json", emit: pass, optional: true
    path "metadata_fail.json", emit: fail, optional: true

    script:
    """
    llm_process_articles.py \
--articles_json ${ARTICLES_JSON} \
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
    path ARTICLES_JSON
    path SYSTEM_PROMPT
    path RESEARCH_INTERESTS_PATH
    val MODEL
    val ALLOW_QC_ERRORS

    output:
    path "screening_pass.json", emit: pass, optional: true
    path "screening_fail.json", emit: fail, optional: true

    script:
    """
    llm_process_articles.py \
--articles_json ${ARTICLES_JSON} \
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
    path ARTICLES_JSON
    path SYSTEM_PROMPT
    path RESEARCH_INTERESTS_PATH
    val MODEL
    val ALLOW_QC_ERRORS

    output:
    path "priority_pass.json", emit: pass, optional: true
    path "priority_fail.json", emit: fail, optional: true

    script:
    """
    llm_process_articles.py \
--articles_json ${ARTICLES_JSON} \
priority \
--system_prompt_path ${SYSTEM_PROMPT} \
--research_interests_path ${RESEARCH_INTERESTS_PATH} \
--model ${MODEL} \
--allow_qc_errors ${ALLOW_QC_ERRORS}
    """
}
