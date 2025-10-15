# Literature agent

## Pre-requisites

- [Nextflow 25.04](https://www.nextflow.io/)
- Docker
- A valid [Google AI Studio API key](https://aistudio.google.com/app/api-keys)

## Quick start

After cloning your repository, simply add your Google key to Nextflow's secret store and run the pipeline:

```bash
nextflow secrets set GOOGLE_API_KEY "<YOUR_GOOGLE_AI_STUDIO_KEY>"
nextflow run main.nf
```
