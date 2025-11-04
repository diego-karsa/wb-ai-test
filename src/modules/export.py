import os
import json
import csv

ARTIFACTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'outputs', 'raw', 'artifacts')
OUTPUT_CSV = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'outputs', 'processed', 'artifacts_export.csv')

COLUMNS = [
	'timestamp', 'economy', 'pillar', 'section_name', 'question_number',
	'answer', 'reasoning', 'confidence',
	'source_1_title', 'source_1_url', 'source_2_title', 'source_2_url'
]

def extract_info_from_path(path):
	# path: .../artifacts/economy/pillar/section_name/question_number.json
	parts = path.split(os.sep)
	# Find 'artifacts' index
	try:
		idx = parts.index('artifacts')
		economy = parts[idx+1]
		pillar = parts[idx+2]
		section_name = parts[idx+3]
		question_number = os.path.splitext(parts[idx+4])[0]
		return economy, pillar, section_name, question_number
	except Exception:
		return None, None, None, None

def get_sources(data):
	sources = data.get('sources', [])
	s1 = sources[0] if len(sources) > 0 else {}
	s2 = sources[1] if len(sources) > 1 else {}
	return (
		s1.get('title', ''), s1.get('url', ''),
		s2.get('title', ''), s2.get('url', '')
	)

def main():
	rows = []
	for root, _, files in os.walk(ARTIFACTS_DIR):
			for fname in files:
				if fname.endswith('.json'):
					fpath = os.path.join(root, fname)
					economy, pillar, section_name, question_number = extract_info_from_path(fpath)
					with open(fpath, 'r', encoding='utf-8') as f:
						data = json.load(f)
					timestamp = data.get('timestamp', '')
					output = data.get('output', {})
					structured = output.get('structured', {})
					answer = structured.get('answer', '') or output.get('answer', '') or data.get('answer', '')
					reasoning = structured.get('reasoning', '') or output.get('reasoning', '') or data.get('reasoning', '')
					confidence = structured.get('confidence', '') or output.get('confidence', '') or data.get('confidence', '')
					sources = structured.get('sources', []) or output.get('sources', []) or data.get('sources', [])
					s1 = sources[0] if len(sources) > 0 else {}
					s2 = sources[1] if len(sources) > 1 else {}
					s1_title = s1.get('title', '')
					s1_url = s1.get('url', '')
					s2_title = s2.get('title', '')
					s2_url = s2.get('url', '')
					row = [timestamp, economy, pillar, section_name, question_number, answer, reasoning, confidence, s1_title, s1_url, s2_title, s2_url]
					rows.append(row)
	with open(OUTPUT_CSV, 'w', encoding='utf-8', newline='') as f:
		writer = csv.writer(f)
		writer.writerow(COLUMNS)
		writer.writerows(rows)
	print(f"Exported {len(rows)} rows to {OUTPUT_CSV}")

if __name__ == "__main__":
	main()
