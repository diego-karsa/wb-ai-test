import os
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from src.modules.client_config import client

ARTIFACTS_CSV = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'outputs', 'processed', 'artifacts_export.csv')
EVAL_OUTPUT_CSV = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'outputs', 'processed', 'artifacts_evaluation.csv')

MODEL_NAME = "gpt-5-mini"

def build_instructions():
    return (
        "You are a legal expert reviewing the output of an AI model that searched the internet for legal basis for the question provided. "
        "Your job is to review the AI's answer and sources. "
        "Return STRICT JSON ONLY with these keys: "
        "verdict (one of: 'Correct', 'Incorrect', 'Insufficient Evidence', 'Outdated Law'), "
        "justification (short, reference specific sources), "
        "corrected_answer (optional, if the original answer is wrong or incomplete), "
        "replacement_citations (optional, array of up to 2 with title and url), "
        "confidence (float, 0-1, 1 decimal). "
        "If the answer is correct, justification should reference the sources and legal basis. "
        "If insufficient, outdated, or incorrect, explain why and provide corrections if possible. "
        "Output STRICT JSON only, no prose or markdown."
    )

def build_input(row):
    # Compose a review input for the model
    question = row['question_number'] + ': ' + row['question_text'] if 'question_text' in row else row['question_number']
    answer = row.get('answer', '')
    reasoning = row.get('reasoning', '')
    sources = []
    if row.get('source_1_title') or row.get('source_1_url'):
        sources.append({'title': row.get('source_1_title', ''), 'url': row.get('source_1_url', '')})
    if row.get('source_2_title') or row.get('source_2_url'):
        sources.append({'title': row.get('source_2_title', ''), 'url': row.get('source_2_url', '')})
    input_text = (
        f"Question: {question}\n"
        f"AI Answer: {answer}\n"
        f"Reasoning: {reasoning}\n"
        f"Sources: {json.dumps(sources, ensure_ascii=False)}\n"
    )
    return input_text

def main():
    with open(ARTIFACTS_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    results = []
    instructions = build_instructions()

    for idx, row in enumerate(rows):
        input_text = build_input(row)
        try:
            resp = client.responses.create(
                model=MODEL_NAME,
                instructions=instructions,
                input=input_text,
                timeout=300,
                tools=[{"type": "web_search_preview",
                        "search_context_size": "low"
                }],
                reasoning={
                "effort": "low"
                },
                store=True
            )
            content = resp.output_text.strip()
            verdict = None
            justification = None
            corrected_answer = None
            replacement_citations = None
            confidence = None
            try:
                parsed = json.loads(content)
                verdict = parsed.get('verdict', '')
                justification = parsed.get('justification', '')
                corrected_answer = parsed.get('corrected_answer', '')
                replacement_citations = parsed.get('replacement_citations', [])
                confidence = parsed.get('confidence', '')
            except Exception:
                pass
            results.append({
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'question_number': row.get('question_number', ''),
                'answer': row.get('answer', ''),
                'verdict': verdict,
                'justification': justification,
                'corrected_answer': corrected_answer,
                'replacement_citations': json.dumps(replacement_citations, ensure_ascii=False) if replacement_citations else '',
                'confidence': confidence
            })
            print(f"[{idx+1}/{len(rows)}] {row.get('question_number', '')}: {verdict}")
        except Exception as e:
            print(f"Error on row {idx+1}: {e}")

    # Write results to CSV
    with open(EVAL_OUTPUT_CSV, 'w', encoding='utf-8', newline='') as f:
        fieldnames = ['timestamp', 'question_number', 'answer', 'verdict', 'justification', 'corrected_answer', 'replacement_citations', 'confidence']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    print(f"Evaluation complete. Results saved to {EVAL_OUTPUT_CSV}")

if __name__ == "__main__":
    main()