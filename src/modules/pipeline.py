# Configuration and client import (Chat Completions API)
# Minimal, with comments for clarity.

import json
import time
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from pathlib import Path
import pandas as pd
from IPython.display import display
from src.modules.client_config import client

# Model and operational parameters
MODEL_NAME = "gpt-5-mini"
RATE_LIMIT_RPM = 20              # Per-minute cap
MAX_RETRIES = 5                  # Exponential backoff tries
BACKOFF_BASE_SECONDS = 2.0       # Initial backoff delay
BACKOFF_CAP_SECONDS = 30.0       # Max backoff delay

# Caching and artifacts
FORCE_REGENERATE = True
CACHE_PATH = Path("outputs/raw/cache.json")
ARTIFACTS_DIR = Path("outputs/raw/artifacts")

ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
# Step 1: Read assumptions and questions CSVs with existence checks

# Define input paths (relative to project root)
QUESTIONS_CSV = Path("data/processed/questions.csv")
ASSUMPTIONS_CSV = Path("data/processed/assumptions.csv")
ECONOMIES_CSV = Path("data/processed/economies.csv")

# Check file existence early and fail fast with a clear message
missing = [str(p) for p in (QUESTIONS_CSV, ASSUMPTIONS_CSV, ECONOMIES_CSV) if not p.exists()]
if missing:
    raise FileNotFoundError(
        "Missing required file(s): " + ", ".join(missing)
    )

# Load DataFrames
questions_df = pd.read_csv(QUESTIONS_CSV)
assumptions_df = pd.read_csv(ASSUMPTIONS_CSV)
economies_df = pd.read_csv(ECONOMIES_CSV)

# Basic sanity check for directories
Path("outputs/raw").mkdir(parents=True, exist_ok=True)
Path("outputs/processed").mkdir(parents=True, exist_ok=True)
print("Output directories ensured.")
# Assumptions helper (pillar/section-specific with fallback to 'All')

from collections import defaultdict

def build_assumptions_map(df) -> Dict[str, Dict[str, List[str]]]:
    mp: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))
    for _, r in df.iterrows():
        p = str(r.get("pillar", "")).strip()
        s = str(r.get("section_name", "")).strip()
        a = str(r.get("assumptions", "")).strip()
        if p and s and a:
            mp[p][s].append(a)
    return mp

assumptions_map = build_assumptions_map(assumptions_df)

def applicable_assumptions(pillar: str, section: str) -> List[str]:
    pillar = (pillar or "").strip()
    section = (section or "").strip()
    out: List[str] = []
    out += assumptions_map.get(pillar, {}).get(section, [])
    out += assumptions_map.get(pillar, {}).get("All", [])
    return [x for x in out if x]
# Utilities: sanitize, cache, rate limit, retries, cache keys

def sanitize_filename(name: str) -> str:
    keep = [c if c.isalnum() or c in ("-", "_", ".") else "_" for c in str(name)]
    out = "".join(keep).strip("._")
    return out or "untitled"

# Cache stored as a simple JSON dict

def load_cache() -> Dict[str, Any]:
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_cache(cache: Dict[str, Any]) -> None:
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


# RPM rate limiter
class RateLimiter:
    def __init__(self, rpm: int):
        self.rpm = max(1, int(rpm))
        self._times: List[float] = []

    def acquire(self):
        now = time.time()
        window = now - 60.0
        self._times = [t for t in self._times if t >= window]
        if len(self._times) >= self.rpm:
            sleep_for = self._times[0] + 60.0 - now
            if sleep_for > 0:
                time.sleep(sleep_for)
        self._times.append(time.time())

rate_limiter = RateLimiter(RATE_LIMIT_RPM)


def with_retries(fn):
    def wrapped(*args, **kwargs):
        attempt = 0
        while True:
            try:
                rate_limiter.acquire()
                return fn(*args, **kwargs)
            except Exception as e:
                attempt += 1
                if attempt > MAX_RETRIES:
                    raise
                # Exponential backoff with light jitter
                delay = min(BACKOFF_CAP_SECONDS, BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)))
                # jitter via hashing current time
                jitter = (hashlib.sha1(str(time.time()).encode()).digest()[0] / 255.0)
                delay *= 0.8 + 0.4 * jitter
                print(f"Retry {attempt} after error: {e}. Sleeping ~{delay:.1f}s...")
                time.sleep(delay)
    return wrapped


def cache_key_for(economy: str, row: Any) -> str:
    payload = {
        "economy": str(economy),
        "pillar": str(row.get("pillar", "")),
        "section_name": str(row.get("section_name", "")),
        "question_number": str(row.get("question_number", "")),
        "question_text": str(row.get("question_text", "")),
        "response_type": str(row.get("response_type", "")),
    }
    return hashlib.sha1(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

print("Utilities initialized.")
# Cell 8: Responses API helper
@with_retries
def call_responses_api(instructions: str, input_text: str):
    """
    Minimal wrapper for Responses API.
    Returns the response object.
    """
    return client.responses.create(
        model=MODEL_NAME,
        instructions=instructions,
        input=input_text,
        tools=[{"type": "web_search_preview",
                "search_context_size": "low"
        }],
        reasoning={
        "effort": "low"
        },
        store=True,
        timeout=300,
    )

def build_instructions_and_input(economy: str, row: Any, extra_assumptions: List[str]):
    """
    Compose instructions and input for the Responses API.
    """
    pillar = str(row.get("pillar", "")).strip()
    section = str(row.get("section_name", "")).strip()
    qnum = str(row.get("question_number", "")).strip()
    qtext = str(row.get("question_text", "")).strip()
    hint = str(row.get("hint", "")).strip()
    rtype = str(row.get("response_type", "")).strip().lower()

    assumptions_text = "\n".join([f"- {a}" for a in extra_assumptions]) if extra_assumptions else "- None"

    if rtype == "integer":
        format_spec = (
            "Return ONLY a JSON object with keys: "
            "value (integer), reasoning (string, <= 40 words), confidence (float, 0-1, 1 decimal), "
            "sources (array up to 2 items with fields: title, url)"
        )
    else:
        format_spec = (
            "Return ONLY a JSON object with keys: "
            "answer (one of: 'Yes', 'No', 'Don't know'), reasoning (string, <= 40 words), confidence (float, 0-1, 1 decimal), "
            "sources (array up to 2 items with fields: title, url)"
        )

    instructions = (
        "You are a careful assistant. Answer concisely and factually; prefer official legal sources when known. "
        "If unsure, answer 'Don't know'. Output STRICT JSON only; no prose, no markdown. "
        "Include up to 2 authoritative legal sources with live URLs (e.g., official gazettes, government or parliament sites). "
        "If no authoritative source is known, return an empty sources array.\n"
        "Rate confidence 0–1 (1 decimal). High score only if the answer is supported by well-established facts or strong reasoning. "
        "Use low confidence if: ambiguous, lack of data, conflicting interpretations, or you are guessing."
    )

    input_parts = [
        f"Economy: {economy}",
        f"Pillar: {pillar}",
        f"Section: {section}",
        f"Question {qnum}: {qtext}",
        f"Response type: {rtype}",
    ]
    if hint:
        input_parts.append(f"Hint: {hint}")
    input_parts.append("Assumptions:\n" + assumptions_text)
    input_parts.append("\nFORMAT:\n" + format_spec)

    input_text = "\n".join(input_parts)
    return instructions, input_text

print("Responses API helpers ready.")

def main():
    import uuid
    from datetime import timezone

    cache = load_cache()

    econ_col = "economy_name"
    if econ_col not in economies_df.columns:
        raise KeyError(f"Expected column '{econ_col}' in economies.csv; found: {list(economies_df.columns)}")

    economies = [str(x) for x in economies_df[econ_col].dropna().astype(str).unique()]

    for econ in economies:
        for idx, row in questions_df.head(1).iterrows():
            pillar = str(row.get("pillar", "")).strip()
            section = str(row.get("section_name", "")).strip()
            qnum = str(row.get("question_number", "")).strip()
            rtype = str(row.get("response_type", "")).strip().lower()

            key = cache_key_for(econ, row)

            if (not FORCE_REGENERATE) and key in cache:
                cached = cache[key]
                content = cached.get("content", "")
                structured = cached.get("structured")
                usage_total_tokens = cached.get("usage_total_tokens")
            else:
                extra_assumps = applicable_assumptions(pillar, section)
                instructions, input_text = build_instructions_and_input(econ, row, extra_assumps)

                resp = call_responses_api(instructions, input_text)

                # Extract output text (Responses API)
                try:
                    content = resp.output_text.strip()
                except Exception:
                    content = ""

                # Parse JSON content if possible
                structured = None
                try:
                    structured = json.loads(content)
                except Exception:
                    structured = None

                # Usage metric (if available)
                usage_total_tokens = getattr(resp, "usage", None)
                # --- Fix: convert to int if possible ---
                if usage_total_tokens is not None:
                    if isinstance(usage_total_tokens, dict):
                        usage_total_tokens = usage_total_tokens.get("total_tokens")
                    elif hasattr(usage_total_tokens, "total_tokens"):
                        usage_total_tokens = usage_total_tokens.total_tokens
                    else:
                        usage_total_tokens = int(usage_total_tokens) if isinstance(usage_total_tokens, (int, float, str)) else None

                cache[key] = {
                    "economy": econ,
                    "pillar": pillar,
                    "section_name": section,
                    "question_number": qnum,
                    "response_type": rtype,
                    "content": content,
                    "structured": structured,
                    "usage_total_tokens": usage_total_tokens  # Now always serializable
                }
                save_cache(cache)

            out_dir = ARTIFACTS_DIR / sanitize_filename(econ) / sanitize_filename(pillar) / sanitize_filename(section)
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"{sanitize_filename(qnum)}.json"

            sources = None
            reasoning = None
            answer_or_value = None
            confidence = None
            try:
                if isinstance(structured, dict):
                    sources = structured.get("sources")
                    reasoning = structured.get("reasoning")
                    confidence = structured.get("confidence")
                    if rtype == "integer":
                        answer_or_value = structured.get("value")
                    else:
                        answer_or_value = structured.get("answer")
            except Exception:
                pass

            artifact = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "economy": econ,
                "question": {
                    "pillar": str(row.get("pillar", "")),
                    "section_name": str(row.get("section_name", "")),
                    "question_number": str(row.get("question_number", "")),
                    "question_text": str(row.get("question_text", "")),
                    "response_type": rtype,
                    "hint": str(row.get("hint", "")),
                },
                "assumptions_used": applicable_assumptions(pillar, section),
                "model": MODEL_NAME,
                "usage": {"total_tokens": usage_total_tokens},
                "output": {
                    "raw": content,
                    "structured": structured,
                    "reasoning": reasoning,
                    "sources": sources,
                    "confidence": confidence,
                    "answer": answer_or_value if rtype != "integer" else None,
                    "value": answer_or_value if rtype == "integer" else None,
                },
            }

            out_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")

            print(f"   ✅ Done {idx + 1}/{len(questions_df)}")

if __name__ == "__main__":
    main()