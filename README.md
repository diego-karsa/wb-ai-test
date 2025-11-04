\## Environment Setup



This project uses a Conda environment for dependency management.



\### 1. Create the environment

```bash

conda env create -f environment.yml

2\. Activate the environment

bash

Copy code

conda activate diego\_env

3\. (Optional) Update the environment if environment.yml changes

bash

Copy code

conda env update -f environment.yml --prune

4\. Run the project

bash

Copy code

python src/main.py



streamlit run src/app.py

python -m src.main