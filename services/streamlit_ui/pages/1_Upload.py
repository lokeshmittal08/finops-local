import os, hashlib, json
import streamlit as st
import requests
import psycopg

POSTGRES_DSN = os.getenv("POSTGRES_DSN")
DOCEXTRACT_URL = "http://doc-extract:8000/extract"

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def normalize_merchant(desc: str) -> str:
    d = desc.lower()
    for ch in ["*", "|", "/", "\\", "-", "_"]:
        d = d.replace(ch, " ")
    d = " ".join(d.split())
    return d[:120]

def fingerprint(account_id: str, txn_date: str, amount_abs: float, direction: str, merchant_norm: str, ref: str | None):
    base = f"{account_id}|{txn_date}|{amount_abs:.2f}|{direction}|{merchant_norm}|{ref or ''}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()

st.header("Upload Bank Statement")

user_email = st.text_input("User email (for now)", value="me@local")
bank_name = st.text_input("Bank name", value="UnknownBank")
currency = st.selectbox("Currency", ["AED","INR"], index=0)

uploaded = st.file_uploader("Upload PDF / image / CSV / XLSX", type=["pdf","png","jpg","jpeg","csv","xlsx","xls"], accept_multiple_files=False)

if uploaded and st.button("Process"):
    file_bytes = uploaded.getvalue()
    file_hash = sha256_bytes(file_bytes)
    save_path = f"/data/uploads/{file_hash}_{uploaded.name}"
    with open(save_path, "wb") as f:
        f.write(file_bytes)

    mime = uploaded.type or ("application/pdf" if uploaded.name.lower().endswith(".pdf") else "application/octet-stream")
    st.write("Saved:", save_path)
    st.write("Mime:", mime)

    # 1) Ensure user + account exist
    with psycopg.connect(POSTGRES_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO users(email) VALUES(%s) ON CONFLICT(email) DO UPDATE SET email=EXCLUDED.email RETURNING id", (user_email,))
            user_id = cur.fetchone()[0]

            cur.execute("""
              INSERT INTO accounts(user_id, bank_name, currency, account_label)
              VALUES(%s,%s,%s,%s)
              RETURNING id
            """, (user_id, bank_name, currency, "Primary"))
            account_id = cur.fetchone()[0]

            cur.execute("""
              INSERT INTO source_files(user_id, filename, file_path, file_sha256, mime_type, status)
              VALUES(%s,%s,%s,%s,%s,'PROCESSING')
              RETURNING id
            """, (user_id, uploaded.name, save_path, file_hash, mime))
            source_file_id = cur.fetchone()[0]
            conn.commit()

    # 2) Extract via local doc-extract-service
    r = requests.post(DOCEXTRACT_URL, json={"file_path": save_path, "mime_type": mime, "currency_hint": currency}, timeout=240)
    if r.status_code != 200:
        st.error(f"Extraction failed: {r.status_code} {r.text}")
        raise SystemExit

    data = r.json()
    txns = data.get("transactions", [])
    st.success(f"Extracted {len(txns)} transactions")

    # 3) Normalize + insert with dedupe
    inserted = 0
    skipped = 0

    with psycopg.connect(POSTGRES_DSN) as conn:
        with conn.cursor() as cur:
            for t in txns:
                txn_date = t["txn_date"]
                desc = t["description"]
                amt = float(t["amount"])
                direction = t["direction"]
                ref = t.get("reference_id")
                merch = t.get("merchant") or normalize_merchant(desc)
                merch_norm = normalize_merchant(merch)

                fp = fingerprint(str(account_id), txn_date, amt, direction, merch_norm, ref)
                signed = amt if direction == "CREDIT" else -amt

                cur.execute("""
                  INSERT INTO transactions(
                    user_id, account_id, source_file_id, txn_date, description, merchant,
                    category, subcategory, currency, direction, amount_abs, signed_amount,
                    reference_id, fingerprint, confidence, raw_json
                  )
                  VALUES (%s,%s,%s,%s,%s,%s,NULL,NULL,%s,%s,%s,%s,%s,%s,%s,%s)
                  ON CONFLICT (user_id, fingerprint) DO NOTHING
                """, (
                    user_id, account_id, source_file_id, txn_date, desc, merch,
                    currency, direction, amt, signed, ref, fp, float(t.get("confidence",0.5)), json.dumps(t.get("raw",{}))
                ))
                if cur.rowcount == 1:
                    inserted += 1
                else:
                    skipped += 1

            cur.execute("UPDATE source_files SET status='PARSED' WHERE id=%s", (source_file_id,))
            conn.commit()

    st.write({"inserted": inserted, "duplicates_skipped": skipped})
    st.text_area("Text preview (debug)", value=data.get("text_preview",""), height=200)
