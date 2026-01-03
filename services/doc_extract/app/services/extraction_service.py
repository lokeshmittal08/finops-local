import os, json, re, traceback, hashlib
from typing import Optional, List, Dict, Any, Tuple

from fastapi import UploadFile, HTTPException

from extractors import extract_text
from core.config import *
import requests
from db.database import SessionLocal
from db.crud import create_statement, create_transactions

# -------------------------------------------------
# Helpers: parsing + numbers
# -------------------------------------------------


def extract_reference_from_row_text(row_text: str) -> Optional[str]:
    """
    Extract Ref/Cheque No from a transaction row.
    Rules:
    - Must contain at least one digit
    - Length >= 5
    - Must NOT be a pure word (e.g., DHABI)
    """
    if not row_text:
        return None

    tokens = row_text.split()

    # Remove dates
    tokens = [
        t for t in tokens
        if not re.fullmatch(r"\d{2}/\d{2}/\d{4}", t)
    ]

    # Remove amount-like tokens
    tokens = [
        t for t in tokens
        if not is_amount_like(t.replace(",", ""))
    ]

    # Valid reference candidates:
    # - at least one digit
    # - length >= 5
    # - alphanumeric allowed
    candidates = [
        t for t in tokens
        if (
            len(t) >= 5
            and re.search(r"\d", t)          # must contain digit
            and re.fullmatch(r"[A-Z0-9]+", t)
        )
    ]

    return candidates[-1] if candidates else None


def extract_reference_id(tx: dict) -> dict:
    raw = tx.get("raw") or {}
    if not isinstance(raw, dict):
        return tx

    ref_value = None

    for k, v in raw.items():
        lk = k.lower()

        if any(x in lk for x in ["ref", "cheque", "check", "txn", "transaction"]):
            if v and isinstance(v, (str, int)):
                val = str(v).strip()

                # Ignore obvious junk
                if val and not re.fullmatch(r"0+(\.0+)?", val):
                    ref_value = val
                    break

    tx["reference_id"] = ref_value
    return tx



def clean_description(desc: str, raw: dict) -> Tuple[str, dict]:
    """
    Improves semantic quality of description without losing data.
    Returns (cleaned_description, updated_raw)
    """
    if not desc:
        return desc, raw

    tokens = desc.split()
    kept = []
    removed = []

    for t in tokens:
        # remove embedded dates like 02/11
        if re.fullmatch(r"\d{2}/\d{2}", t):
            removed.append(t)
            continue

        # remove currency+amount like AED1050 or AED10000.00
        if re.fullmatch(r"[A-Z]{3}\d+(\.\d{1,2})?", t):
            removed.append(t)
            continue

        # remove pure numeric chunks (likely refs)
        if re.fullmatch(r"\d{4,}", t):
            removed.append(t)
            continue

        # remove common txn prefixes (safe, global)
        if t.upper() in {"PUR", "POS", "MBTRF", "B/F", "TRF", "ATM"}:
            removed.append(t)
            continue

        kept.append(t)

    cleaned = " ".join(kept).strip()

    # preserve removed info
    if removed:
        raw = dict(raw)
        raw["description_tokens_removed"] = removed

    return cleaned if cleaned else desc, raw


def parse_amount(x) -> Optional[float]:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip()
    if s == "":
        return None
    s = s.replace(",", "")
    # remove currency symbols if any
    s = re.sub(r"[^\d\.\-]", "", s)
    if s in ("", "-", "."):
        return None
    try:
        return float(s)
    except:
        return None

def is_amount_like(x) -> bool:
    if x is None:
        return False
    s = str(x).replace(",", "").strip()
    return bool(re.fullmatch(r"-?\d+(\.\d{1,2})?", s))

def ddmmyyyy_to_iso(s: str) -> Optional[str]:
    s = s.strip()
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", s)
    if not m:
        return None
    dd, mm, yyyy = m.group(1), m.group(2), m.group(3)
    return f"{yyyy}-{mm}-{dd}"

def safe_round(x: Optional[float]) -> Optional[float]:
    if x is None:
        return None
    return float(round(x, 2))

def approx_equal(a: float, b: float, tol: float = 0.02) -> bool:
    return abs(a - b) <= tol

def extract_json_block(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError(f"No JSON found in LLM output:\n{text[:1000]}")
    return json.loads(m.group(0))


# -------------------------------------------------
# Step 4: Ollama metadata only (small prompt)
# -------------------------------------------------

def ollama_metadata(prompt: str) -> dict:
    r = requests.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": (
                "You are a bank statement metadata extractor.\n"
                "Return VALID JSON ONLY.\n"
                "No markdown. No explanations.\n"
                "Do not invent values.\n"
                "If missing, return null.\n\n"
                + prompt
            ),
            "stream": False,
            "options": {
                "temperature": 0.0
            }
        },
        timeout=(OLLAMA_CONNECT_TIMEOUT, OLLAMA_READ_TIMEOUT),
    )

    r.raise_for_status()
    text = r.json()["response"]   # 👈 IMPORTANT difference
    return extract_json_block(text)

# def ollama_metadata(prompt: str) -> dict:
#     r = requests.post(
#         f"{OLLAMA_BASE_URL}/api/chat",
#         json={
#             "model": OLLAMA_MODEL,
#             "messages": [
#                 {
#                     "role": "system",
#                     "content": (
#                         "You are a bank statement metadata extractor.\n"
#                         "Return VALID JSON ONLY.\n"
#                         "No markdown. No explanations.\n"
#                         "Do not invent values.\n"
#                         "If missing, return null."
#                     ),
#                 },
#                 {"role": "user", "content": prompt},
#             ],
#             "stream": False,
#             "options": {
#                 "temperature": 0.0
#             }
#         },
#         timeout=(OLLAMA_CONNECT_TIMEOUT, OLLAMA_READ_TIMEOUT),
#     )
#     r.raise_for_status()
#     text = r.json()["message"]["content"]
#     return extract_json_block(text)


def build_metadata_prompt(text: str, currency: str, bank_hint: Optional[str], holder_hint: Optional[str]) -> str:
    # Keep small: only header-ish content for metadata extraction
    # We take first N chars + last N chars (often statement period + balances appear in header/footer)
    head = text[:25000]
    tail = text[-15000:] if len(text) > 15000 else ""
    snippet = head + "\n\n---\n\n" + tail

    return f"""
Extract ONLY statement metadata from the statement text snippet.

Output JSON schema:
{{
  "bank_name": string|null,
  "account_holder_name": string|null,
  "account_number": string|null,
  "statement_period": {{ "from": "YYYY-MM-DD"|null, "to": "YYYY-MM-DD"|null }},
  "opening_balance": {{ "amount": number|null, "currency": "{currency}" }},
  "closing_balance": {{ "amount": number|null, "currency": "{currency}" }}
}}

Rules:
- Account number MUST be FULL as printed (do NOT mask).
- bank_name/account_holder_name must be exact if present, else null.
- statement_period from/to as YYYY-MM-DD if present.
- opening/closing balances if present, else null.
- Use currency "{currency}" unless clearly different.

Hints (optional):
- bank_hint: {bank_hint or "null"}
- account_holder_hint: {holder_hint or "null"}

STATEMENT_SNIPPET:
{snippet}
""".strip()


# -------------------------------------------------
# Step 1/2: deterministic transaction row extraction from text
# -------------------------------------------------

DATE2 = r"(\d{2}/\d{2}/\d{4})"

def looks_like_txn_line(line: str) -> bool:
    # must contain at least one dd/mm/yyyy and at least one amount-like token
    if not re.search(DATE2, line):
        return False
    # numeric tokens
    nums = re.findall(r"-?\d[\d,]*\.\d{1,2}|\b-?\d[\d,]*\b", line)
    # require at least 2 numeric-ish tokens besides dates/ref
    return len(nums) >= 2

def normalize_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

def parse_possible_row(line: str) -> Optional[dict]:
    """
    Parse a *single transaction row text* in a bank-agnostic way.
    Strategy:
      - capture 1-2 dates at start (posting/value)
      - capture trailing numeric columns (debit/credit/balance) if present
      - everything in middle is description/ref
    """
    line = normalize_spaces(line)
    # Pull leading dates (posting/value)
    m = re.match(rf"^\s*{DATE2}(?:\s+{DATE2})?\s+(.*)$", line)
    if not m:
        return None

    dates = re.findall(DATE2, line[:30])
    posting = dates[0] if len(dates) >= 1 else None
    value = dates[1] if len(dates) >= 2 else None

    rest = line
    # Remove leading dates from rest
    if value:
        rest = re.sub(rf"^\s*{DATE2}\s+{DATE2}\s+", "", line)
    else:
        rest = re.sub(rf"^\s*{DATE2}\s+", "", line)

    # Now attempt to grab up to 3 trailing amounts (debit/credit/balance)
    # We detect amounts at end separated by spaces
    tokens = rest.split(" ")
    # Extract numeric-like tokens from the end
    tail_nums = []
    tail_idx = len(tokens) - 1

    def token_to_num(tok: str) -> Optional[float]:
        return parse_amount(tok)

    while tail_idx >= 0 and len(tail_nums) < 3:
        tok = tokens[tail_idx]
        if is_amount_like(tok.replace(",", "")):
            tail_nums.append(token_to_num(tok))
            tail_idx -= 1
        else:
            break

    tail_nums = list(reversed(tail_nums))  # keep original order
    middle = " ".join(tokens[:tail_idx + 1]).strip()

    ref_id = extract_reference_from_row_text(line)
    desc = middle

    # ---- Extract Ref/Cheque token from the last text token before amounts ----
    ref_id = None
    desc_tokens = tokens[:tail_idx + 1]  # everything before amounts

    if desc_tokens:
        last_tok = desc_tokens[-1].strip()

        # Reference must contain at least one digit and be length>=5 (prevents "DHABI")
        if len(last_tok) >= 5 and re.search(r"\d", last_tok) and re.fullmatch(r"[A-Z0-9]+", last_tok, flags=re.IGNORECASE):
            ref_id = last_tok
            desc_tokens = desc_tokens[:-1]  # remove ref from description tokens

    desc = " ".join(desc_tokens).strip()


    # Heuristics:
    # If 3 nums => interpret as (debit, credit, balance) OR (debit, balance) OR (credit, balance) depending on zero/null
    debit = credit = bal = None
    if len(tail_nums) == 3:
        # Common bank format: Debit Credit Balance OR Debit Credit Balance (one side empty/0)
        debit, credit, bal = tail_nums[0], tail_nums[1], tail_nums[2]
    elif len(tail_nums) == 2:
        # Often: Amount Balance (either debit or credit)
        # We'll set debit=amount (tentatively) and let Step-3 fix using balance chain
        debit, credit, bal = tail_nums[0], None, tail_nums[1]
    elif len(tail_nums) == 1:
        # Rare: only one numeric at end, treat as balance
        bal = tail_nums[0]

    # If debit/credit are exactly 0 => null
    if debit is not None and abs(debit) < 1e-9:
        debit = None
    if credit is not None and abs(credit) < 1e-9:
        credit = None

    # Create "raw" as best-effort canonical keys (not bank-specific)
    raw = {
        "Posting Date": posting,
        "Value Date": value,
        "Description": desc if desc else None,
        "Ref/Cheque No": ref_id,
        "Debit Amount": safe_round(debit) if debit is not None else None,
        "Credit Amount": safe_round(credit) if credit is not None else None,
        "Balance": safe_round(bal) if bal is not None else None,
        "row_text": line,
    }

    date_iso = ddmmyyyy_to_iso(posting) or ddmmyyyy_to_iso(value)  # prefer posting
    if not date_iso:
        return None

    return {
        "date": date_iso,
        "description": desc if desc else "UNKNOWN",
        "debit": safe_round(debit) if debit is not None else None,
        "credit": safe_round(credit) if credit is not None else None,
        "balance_after": safe_round(bal) if bal is not None else None,
        "reference_id": ref_id,
        "raw": raw,
    }

def extract_candidate_transactions(text: str) -> List[dict]:
    """
    Bank-agnostic candidate extraction:
      - scan lines
      - keep lines that look like transaction rows
    """
    lines = [normalize_spaces(x) for x in text.splitlines()]
    # Remove empty lines
    lines = [x for x in lines if x]

    candidates = []
    for ln in lines:
        if not looks_like_txn_line(ln):
            continue
        row = parse_possible_row(ln)
        if row:
            candidates.append(row)

    # De-dup by row_text hash
    seen = set()
    uniq = []
    for c in candidates:
        h = hashlib.md5(c["raw"].get("row_text", "").encode("utf-8")).hexdigest()
        if h in seen:
            continue
        seen.add(h)
        uniq.append(c)
    return uniq


# -------------------------------------------------
# Step 2: canonicalize + direction from amounts (tentative)
# -------------------------------------------------

def canonicalize_and_set_direction(tx: dict, currency: str) -> dict:
    debit = parse_amount(tx.get("debit"))
    credit = parse_amount(tx.get("credit"))
    bal = parse_amount(tx.get("balance_after"))

    if debit == 0.0: debit = None
    if credit == 0.0: credit = None

    direction = "DEBIT" if debit is not None and credit is None else "CREDIT" if credit is not None and debit is None else "DEBIT"

    tx["debit"] = safe_round(debit) if debit is not None else None
    tx["credit"] = safe_round(credit) if credit is not None else None
    tx["balance_after"] = safe_round(bal) if bal is not None else None
    tx["currency"] = currency
    tx["direction"] = direction
    # confidence is provisional here
    tx["confidence"] = 0.6 if (tx["debit"] is not None or tx["credit"] is not None) else 0.3
    if not isinstance(tx.get("raw"), dict):
        tx["raw"] = {"row_text": str(tx.get("raw"))}
    return tx


# -------------------------------------------------
# Step 3: Balance-based correction (robust, bank-agnostic)
# -------------------------------------------------

def balance_coverage(txns: List[dict]) -> float:
    if not txns:
        return 0.0
    have = sum(1 for t in txns if parse_amount(t.get("balance_after")) is not None)
    return have / max(1, len(txns))

def compute_chain_error(txns: List[dict]) -> float:
    """
    Average absolute error across consecutive rows where balances exist.
    """
    errs = []
    for i in range(1, len(txns)):
        b_prev = parse_amount(txns[i-1].get("balance_after"))
        b_cur = parse_amount(txns[i].get("balance_after"))
        if b_prev is None or b_cur is None:
            continue
        d = parse_amount(txns[i].get("debit")) or 0.0
        c = parse_amount(txns[i].get("credit")) or 0.0
        pred = b_prev - d + c
        errs.append(abs(pred - b_cur))
    if not errs:
        return float("inf")
    return sum(errs) / len(errs)

def maybe_reverse_best_order(txns: List[dict]) -> List[dict]:
    """
    Statements can be ascending or descending.
    We choose the orientation with lower balance chain error.
    """
    if len(txns) < 3:
        return txns
    e_fwd = compute_chain_error(txns)
    e_rev = compute_chain_error(list(reversed(txns)))
    return txns if e_fwd <= e_rev else list(reversed(txns))

def try_swap_for_best_fit(prev_bal: float, cur_bal: float, debit: Optional[float], credit: Optional[float]) -> Tuple[Optional[float], Optional[float], float]:
    """
    Given prev balance and current balance, choose debit/credit assignment that minimizes equation error:
      cur ≈ prev - debit + credit
    Return: best_debit, best_credit, best_error
    """
    # treat None as 0 for evaluation
    d = debit or 0.0
    c = credit or 0.0

    pred1 = prev_bal - d + c
    err1 = abs(pred1 - cur_bal)

    # swap scenario (only meaningful if both exist or one exist)
    pred2 = prev_bal - c + d
    err2 = abs(pred2 - cur_bal)

    if err2 + 1e-9 < err1:
        return (credit, debit, err2)
    return (debit, credit, err1)

def balance_correct(txns: List[dict]) -> List[dict]:
    """
    Correct debit/credit using balance chain, if balances are sufficiently present.
    """
    if not txns:
        return txns

    txns = maybe_reverse_best_order(txns)
    cov = balance_coverage(txns)
    if cov < 0.55:
        # Not enough balances to reliably correct
        return txns

    # Walk and correct each row using previous balance
    for i in range(1, len(txns)):
        b_prev = parse_amount(txns[i-1].get("balance_after"))
        b_cur = parse_amount(txns[i].get("balance_after"))
        if b_prev is None or b_cur is None:
            continue

        debit = parse_amount(txns[i].get("debit"))
        credit = parse_amount(txns[i].get("credit"))

        # If both missing, cannot correct
        if debit is None and credit is None:
            continue

        best_d, best_c, err = try_swap_for_best_fit(b_prev, b_cur, debit, credit)

        # Accept swap if it clearly improves fit
        # tolerance: 0.05 AED (adjust if needed)
        txns[i]["debit"] = safe_round(best_d) if best_d is not None and best_d != 0.0 else None
        txns[i]["credit"] = safe_round(best_c) if best_c is not None and best_c != 0.0 else None

        # Set direction deterministically after correction
        if txns[i]["debit"] is not None and txns[i]["credit"] is None:
            txns[i]["direction"] = "DEBIT"
        elif txns[i]["credit"] is not None and txns[i]["debit"] is None:
            txns[i]["direction"] = "CREDIT"
        elif txns[i]["debit"] is not None and txns[i]["credit"] is not None:
            # keep larger as direction, drop smaller (rare)
            if txns[i]["debit"] >= txns[i]["credit"]:
                txns[i]["credit"] = None
                txns[i]["direction"] = "DEBIT"
            else:
                txns[i]["debit"] = None
                txns[i]["direction"] = "CREDIT"

        # confidence boosted based on balance fit
        # smaller err => higher confidence (cap to 1.0)
        # err ~ 0 => 1.0, err > 2 => low
        conf = max(0.4, min(1.0, 1.0 - (err / 5.0)))
        txns[i]["confidence"] = float(round(conf, 3))

    # final pass: ensure balance_after numeric
    for t in txns:
        t["balance_after"] = safe_round(parse_amount(t.get("balance_after"))) if parse_amount(t.get("balance_after")) is not None else None

    return txns


# -------------------------------------------------
# File handling
# -------------------------------------------------

def save_upload(upload: UploadFile) -> str:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    content = upload.file.read()
    sha = hashlib.sha256(content).hexdigest()
    path = os.path.join(UPLOAD_DIR, f"{sha}_{upload.filename}".replace(" ", "_"))
    with open(path, "wb") as f:
        f.write(content)
    return path


# def persist_to_db(statement_metadata: dict, transactions: list):
#     db = SessionLocal()
#     try:
#         statement = create_statement(db, statement_metadata)
#         create_transactions(db, statement.id, transactions)
#     finally:
#         db.close()


def persist_to_db(statement_metadata: dict, transactions: list):
    db = SessionLocal()
    try:
        statement = create_statement(db, statement_metadata)

        # 🔹 RECONCILIATION
        opening = statement_metadata["opening_balance"]["amount"]
        closing = statement_metadata["closing_balance"]["amount"]

        ok, diff = reconcile_statement(opening, closing, transactions)
        stmt_conf = compute_statement_confidence(transactions)

        statement.is_reconciled = ok
        statement.reconciliation_diff = diff
        statement.statement_confidence = stmt_conf

        create_transactions(db, statement.id, transactions)

        db.commit()
    finally:
        db.close()

def compute_statement_confidence(txns: list) -> Optional[float]:
    if not txns:
        return None
    return round(
        sum(t.get("confidence", 0) for t in txns) / len(txns),
        3
    )


def reconcile_statement(
    opening: Optional[float],
    closing: Optional[float],
    txns: list,
    tolerance: float = 0.05,
):
    """
    Returns:
      (is_reconciled: bool, diff: float|None)
    """
    if opening is None or closing is None:
        return False, None

    total_debit = sum(t.get("debit") or 0 for t in txns)
    total_credit = sum(t.get("credit") or 0 for t in txns)

    expected_closing = opening + total_credit - total_debit
    diff = round(expected_closing - closing, 2)

    return abs(diff) <= tolerance, diff


def detect_duplicates(transactions: list):
    """
    Marks duplicate transactions in-place.
    Rule:
      (reference_id, date, amount) must be identical
    """
    seen = {}

    for idx, tx in enumerate(transactions):
        amount = tx.get("debit") or tx.get("credit")
        key = (
            tx.get("reference_id"),
            tx["date"],
            amount,
        )

        if tx.get("reference_id") and key in seen:
            tx["is_duplicate"] = True
            tx["duplicate_of"] = seen[key]
        else:
            tx["is_duplicate"] = False
            tx["duplicate_of"] = None
            seen[key] = idx

def apply_manual_adjustments(opening_balance: float, adjustments: list) -> float:
    debit = sum(a.amount for a in adjustments if a.direction == "DEBIT")
    credit = sum(a.amount for a in adjustments if a.direction == "CREDIT")
    return opening_balance + credit - debit


def handle_extract(
    file: UploadFile,
    currency_hint: Optional[str],
    bank_hint: Optional[str],
    account_holder_hint: Optional[str],
):
    try:
        path = save_upload(file)
        mime = file.content_type or "application/octet-stream"
        text, method = extract_text(path, mime)

        currency = (currency_hint or DEFAULT_CURRENCY).strip().upper()
        if currency not in ("AED", "INR"):
            currency = DEFAULT_CURRENCY

        candidates = extract_candidate_transactions(text)
        txns = [canonicalize_and_set_direction(t, currency) for t in candidates]
        txns = balance_correct(txns)
        detect_duplicates(txns)


        for t in txns:
            cleaned_desc, new_raw = clean_description(t["description"], t["raw"])
            t["description"] = cleaned_desc
            t["raw"] = new_raw

            d = parse_amount(t.get("debit"))
            c = parse_amount(t.get("credit"))
            if d is not None and c is not None:
                if d >= c:
                    t["credit"] = None
                    t["direction"] = "DEBIT"
                else:
                    t["debit"] = None
                    t["direction"] = "CREDIT"

        meta_prompt = build_metadata_prompt(
            text, currency, bank_hint, account_holder_hint
        )
        meta = ollama_metadata(meta_prompt)

        # ---- Bank name reconciliation (deterministic, safe) ----
        bank_name = meta.get("bank_name")

        if not bank_name:
            if bank_hint and isinstance(bank_hint, str):
                bank_hint_clean = bank_hint.strip()
                if bank_hint_clean:
                    bank_name = bank_hint_clean


        statement_metadata = {
            "bank_name": bank_name,
            # "bank_name": meta.get("bank_name"),
            "account_holder_name": meta.get("account_holder_name"),
            "account_number": meta.get("account_number"),
            "statement_period": {
                "from": meta.get("statement_period", {}).get("from"),
                "to": meta.get("statement_period", {}).get("to"),
            },
            "opening_balance": {
                "amount": safe_round(parse_amount(meta.get("opening_balance", {}).get("amount"))),
                "currency": currency,
            },
            "closing_balance": {
                "amount": safe_round(parse_amount(meta.get("closing_balance", {}).get("amount"))),
                "currency": currency,
            },
        }
        persist_to_db(statement_metadata, txns)

        # return {
        #     "statement_metadata": {
        #         **statement_metadata,
        #         "is_reconciled": ok,
        #         "reconciliation_diff": diff,
        #         "statement_confidence": stmt_conf,
        #     },
        #     "transactions": txns,
        # }
        return {
            "statement_metadata": statement_metadata,
            "transactions": txns,
        }

    except Exception as e:
        print("❌ EXTRACT FAILED")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))