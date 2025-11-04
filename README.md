# AI Legal Pipeline

This project uses a Conda environment for dependency management and provides both a command-line and Streamlit GUI for running the full pipeline.

## Setup Instructions

### 1. Create the Conda environment

```bash
conda env create -f environment.yml
```

### 2. Activate the environment

```bash
conda activate diego_env
```

### 3. Configure environment variables
Create a ```.env``` file in the project root with the following contents:

OPENAI_API_KEY=your_openai_api_key_here
CERTIFICATE_PATH=  # Optional, only if required

## Running the Project

Run the full pipeline (all stages). This will run: client configuration, main pipeline, export, evaluation, and translation.

```bash
python -m src.main
```

Run the Streamlit app. This app allows you to upload input CSVs, run the pipeline, view results, and download outputs.

```bash
streamlit run src/app.py
```