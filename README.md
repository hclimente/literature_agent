# Papers, Please: Agentic framework for literature triaging

An agentic-workflow to assist researchers in staying up-to-date with literature by leveraging LLMs and tools to screen and prioritize scientific articles.

## Pre-requisites

- [Nextflow 25.04](https://www.nextflow.io/)
- Docker
- Add the following secrets to Nextflow's secret store:
    - Required:
        - `GOOGLE_API_KEY`, from [Google AI Studio API key](https://aistudio.google.com/app/api-keys). Used to query Gemini to screen and prioritize articles.
        - `USER_EMAIL`, containing your email address. Used to fetch metadata from the NCBI and CrossRef APIs.
    - Optional, for additional capabilities:
        - `SPRINGER_META_API_KEY`, from [Springer](https://dev.springernature.com/). Used to get article metadata.
        - `ZOTERO_API_KEY`, from the [Zotero settings](https://www.zotero.org/settings/keys). Used to save articles directly to your Zotero library. It requires [additional configuration](config/config.yaml).

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

The workflow will fetch the latest articles from the specified journals, screen them based on your research interests, and output a prioritized list of articles in `results/prioritized_articles.json`. It should look like this:

```json
[
  {
    "title": "Sample Article Title 1",
    "abstract": "...",
    "journal": "Sample Journal",
    "publication_date": "2025-10-23",
    "priority_decision": "high",
    "url": "https://doi.org/xx.xxxx/xxxxx"
  },
    {
    "title": "Sample Article Title 2",
    "abstract": "...",
    "journal": "Sample Journal",
    "publication_date": "2025-10-19",
    "priority_decision": "low",
    "url": "https://doi.org/xx.xxxx/xxxxx"
  }
]
```

# Automated weekly runs on Github Actions

This workflow can be set up to run automatically on a weekly basis using GitHub Actions. The workflow will check for new articles based on your specified research interests and journals, process them, and save the results to your Zotero library.

To set up the automated weekly runs, follow these steps:

1. Click the "Fork" button at the top right of this page to create your own copy of the repository.
1. Modify the first lines of `config/config.yaml` to add your configuration as follows:

    ```yaml
    research_interests: "<your_interests.md>"
    journals_tsv: "<your_journals.tsv>"

    zotero:
        user_id: "<your_user_id>"
        collection_id: "<your_collection_id>"
        library_type: "user" # or "group"
    ```

1. Add [the required secrets](#pre-requisites) to your forked repository. See [here](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets#creating-secrets-for-a-repository) for more information.
