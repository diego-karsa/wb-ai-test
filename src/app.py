import streamlit as st
import pandas as pd
import os
import subprocess


st.title("AI Legal Pipeline")

# CSV column requirements
csv_columns = {
	"assumptions.csv": "Columns: pillar, section_name, assumptions",
	"economies.csv": "Columns: economy_name",
	"questions.csv": "Columns: pillar, section_name, question_number, question_text, response_type (yes_no or integer), hint"
}

# Upload CSVs
st.header("Upload Input Data")
for fname in ["assumptions.csv", "economies.csv", "questions.csv"]:
	uploaded = st.file_uploader(f"Upload {fname}", type="csv", key=fname)
	st.markdown(f"<small>{csv_columns[fname]}</small>", unsafe_allow_html=True)
	if uploaded:
		out_path = os.path.join("data", "processed", fname)
		with open(out_path, "wb") as f:
			f.write(uploaded.getbuffer())
		st.success(f"{fname} uploaded.")


# Translation option (default True)
run_translation = st.checkbox("Run Translation Step (Spanish)", value=True)

run_clicked = st.button("Run Pipeline")
if run_clicked:
	st.info("Running pipeline...")
	os.environ["RUN_TRANSLATION"] = "1" if run_translation else "0"
	result = subprocess.run(["python", "-m", "src.main"], capture_output=True, text=True)
	if result.returncode == 0:
		st.success("Pipeline completed.")
	else:
		st.error(f"Pipeline failed:\n{result.stderr}")
	with st.expander("Show Pipeline Output", expanded=True):
		st.code(result.stdout + '\n' + result.stderr, language="bash")

# Show results
st.header("Results")
for result_file in ["outputs/processed/artifacts_export.csv", "outputs/processed/artifacts_evaluation.csv"]:
	if os.path.exists(result_file):
		df = pd.read_csv(result_file)
		st.subheader(os.path.basename(result_file))
		st.dataframe(df)
		st.download_button(
			label=f"Download {os.path.basename(result_file)}",
			data=df.to_csv(index=False).encode("utf-8"),
			file_name=os.path.basename(result_file),
			mime="text/csv"
		)
