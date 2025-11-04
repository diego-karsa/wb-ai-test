import os
import csv
import json
from pathlib import Path
from src.modules.client_config import client

MODEL_NAME = "gpt-5-mini"

FILES_TO_TRANSLATE = [
	(os.path.join("outputs", "processed", "artifacts_evaluation.csv"), "artifacts_evaluation_spanish.csv"),
	(os.path.join("outputs", "processed", "artifacts_export.csv"), "artifacts_export_spanish.csv"),
	(os.path.join("data", "processed", "assumptions.csv"), "assumptions_spanish.csv"),
	(os.path.join("data", "processed", "economies.csv"), "economies_spanish.csv"),
	(os.path.join("data", "processed", "questions.csv"), "questions_spanish.csv"),
]

TRANSLATION_DIR = os.path.join("outputs", "processed", "translations", "spanish")
os.makedirs(TRANSLATION_DIR, exist_ok=True)

def build_instructions():
	return (
		"Translate the following CSV row to Spanish. "
		"Return STRICT JSON ONLY with the same keys as the input, but with all values translated to Spanish. "
		"Do not change the column names, only translate the values. "
		"Output STRICT JSON only, no prose or markdown."
	)

def build_input(row):
	return json.dumps(row, ensure_ascii=False)

def translate_csv(in_path, out_name):
    out_path = os.path.join(TRANSLATION_DIR, out_name)
    with open(in_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames

    instructions = build_instructions()
    translated_rows = []
    for idx, row in enumerate(rows):
        input_text = build_input(row)
        try:
            resp = client.responses.create(
                model=MODEL_NAME,
                instructions=instructions,
                input=input_text,
                reasoning={
                    "effort": "low"
                },
                timeout=120,
                store=True
            )
            content = resp.output_text.strip()
            translated = None
            try:
                translated = json.loads(content)
            except Exception:
                translated = None
            if translated:
                # Only keep keys that are in fieldnames
                filtered = {k: translated.get(k, "") for k in fieldnames}
                translated_rows.append(filtered)
            else:
                translated_rows.append(row)
            print(f"[{idx+1}/{len(rows)}] Translated row for {out_name}")
        except Exception as e:
            print(f"Error translating row {idx+1} in {in_path}: {e}")

    # Write translated CSV
    with open(out_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(translated_rows)
    print(f"Saved translated CSV: {out_path}")

def main():
	for in_path, out_name in FILES_TO_TRANSLATE:
		if os.path.exists(in_path):
			translate_csv(in_path, out_name)
		else:
			print(f"File not found: {in_path}")

if __name__ == "__main__":
	main()
