# Papers, Please: Agentic framework for literature triaging

An agentic-workflow to assist researchers in staying up-to-date with literature by leveraging LLMs and tools to screen and prioritize scientific articles.

## Pre-requisites

- [Nextflow 25.04](https://www.nextflow.io/)
- Docker
- Add the following secrets to Nextflow's secret store:
    - Required:
        - `GOOGLE_API_KEY`: get it from [Google AI Studio API key](https://aistudio.google.com/app/api-keys)
        - `USER_EMAIL`: your email address, to fetch metadata from the NCBI API
    - Optional, for additional capabilities:
        - `SPRINGER_META_API_KEY`: get an account from [Springer](https://dev.springernature.com/) to get article metadata.
        - `ZOTERO_API_KEY`: get it from your [Zotero settings](https://www.zotero.org/settings/keys) to save articles directly to your Zotero library. It requires additional configuration in `nextflow.config`.

<details>

<summary><strong>How to add secrets to Nextflow</strong></summary>

```bash
nextflow secrets set GOOGLE_API_KEY "<YOUR_GOOGLE_AI_STUDIO_KEY>"
```

</details>

## Quick start

Adjust the journals you want to monitor and your research interests. See examples [here](config/journals.tsv) and [here](config/research_interests.md), respectively. Then, simply run:

```bash
nextflow run hclimente/nf-papers-please \
    --journals_tsv <your_journals.tsv> \
    --research_interests <your_interests.md>
```

# Automated weekly runs on Github Actions

1. Click the "Fork" button at the top right of this page to create your own copy of the repository.
1. Modify the first lines of `config/pipeline_parameters.yaml` to add your configuration as follows:

    ```yaml
    research_interests: "<your_interests.md>"
    journals_tsv: "<your_journals.tsv>"

    zotero:
        user_id: "<your_user_id>"
        collection_id: "<your_collection_id>"
        library_type: "user" # or "group"
    ```

1. Add [the required secrets](#pre-requisites) to your forked repository. See [here](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets#creating-secrets-for-a-repository) for more information.
