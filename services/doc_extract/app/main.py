import os, json, hashlib, requests
from fastapi import FastAPI
from pydantic import BaseModel
from schemas import ExtractResponse
from extractors import extract_text

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_CURRENCY = os.getenv("DEFAULT_CURRENCY", "AED")

app = FastAPI(title="doc-extract-service", version="0.1")

class ExtractRequest(BaseModel):
    file_path: str
    mime_type: str
    currency_hint: str | None = None

def ollama_json(prompt: str, model: str="qwen2.5:7b") -> dict:
    r = requests.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=180
    )
    r.raise_for_status()
    text = r.json().get("response", "")
    # Expect JSON only
    return json.loads(text)

@app.post("/extract", response_model=ExtractResponse)
def extract(req: ExtractRequest):
    text, method = extract_text(req.file_path, req.mime_type)
    currency = req.currency_hint or DEFAULT_CURRENCY

    prompt = f"""
You are extracting bank statement transactions. Output MUST be valid JSON only.

Target schema:
{{
  "bank_hint": string|null,
  "account_hint": string|null,
  "transactions": [
    {{
      "txn_date": "YYYY-MM-DD",
      "description": string,
      "amount": number,              // absolute amount
      "currency": "AED"|"INR",
      "direction": "DEBIT"|"CREDIT",
      "reference_id": string|null,
      "merchant": string|null,
      "confidence": number,          // 0.0 to 1.0
      "raw": object
    }}
  ],
  "text_preview": string|null
}}

Rules:
- Use currency "{currency}" unless clearly indicated otherwise.
- If statement lists debit/credit columns, map direction accordingly.
- If sign is shown, negative means DEBIT; positive means CREDIT.
- If unsure about a row, still include it with lower confidence (e.g. 0.4).
- Do not hallucinate transactions not present in text.

STATEMENT_TEXT:
{text[:200000]}
"""
    data = ollama_json(prompt)
    # add preview to help debugging
    if "text_preview" not in data:
        data["text_preview"] = text[:1500]
    return data
