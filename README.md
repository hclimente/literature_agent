# Papers please

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

<details>

<summary>How to add secrets to Nextflow</summary>

```bash
nextflow secrets set GOOGLE_API_KEY "<YOUR_GOOGLE_AI_STUDIO_KEY>"
```

</details>

## Quick start

Adjust the journals you want to monitor and your research interests. See examples [here](config/journals.tsv) and [here](config/research_interests.md), respectively. Then, simply run:

```bash
nextflow run hclimente/nf-papers-please \
    --journal_list <your_journals.tsv> \
    --research_interests <your_interests.md>
```
