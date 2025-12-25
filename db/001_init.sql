CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- multi-user ready
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  name TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS accounts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  bank_name TEXT NOT NULL,
  account_label TEXT,
  currency TEXT NOT NULL CHECK (currency IN ('AED','INR')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS source_files (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  filename TEXT NOT NULL,
  file_path TEXT NOT NULL,
  file_sha256 TEXT NOT NULL,
  mime_type TEXT,
  uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  status TEXT NOT NULL DEFAULT 'UPLOADED', -- UPLOADED, PROCESSING, PARSED, FAILED
  error TEXT
);

-- canonical transaction storage
CREATE TABLE IF NOT EXISTS transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  source_file_id UUID REFERENCES source_files(id) ON DELETE SET NULL,

  txn_date DATE NOT NULL,
  description TEXT NOT NULL,
  merchant TEXT,
  category TEXT,
  subcategory TEXT,

  currency TEXT NOT NULL CHECK (currency IN ('AED','INR')),
  direction TEXT NOT NULL CHECK (direction IN ('DEBIT','CREDIT')),

  amount_abs NUMERIC(14,2) NOT NULL CHECK (amount_abs >= 0),
  signed_amount NUMERIC(14,2) NOT NULL,

  reference_id TEXT, -- if bank provides
  fingerprint TEXT NOT NULL, -- sha256 key for dedupe

  confidence NUMERIC(4,3) NOT NULL DEFAULT 0.0,
  raw_json JSONB,

  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Strong dedupe: one canonical transaction per fingerprint
CREATE UNIQUE INDEX IF NOT EXISTS uq_transactions_fingerprint
ON transactions(user_id, fingerprint);

-- helps dashboards
CREATE INDEX IF NOT EXISTS ix_transactions_user_date
ON transactions(user_id, txn_date);

CREATE INDEX IF NOT EXISTS ix_transactions_user_category_date
ON transactions(user_id, category, txn_date);

-- minimal starter categories (you can expand)
CREATE TABLE IF NOT EXISTS category_rules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  pattern TEXT NOT NULL, -- keyword/regex
  category TEXT NOT NULL,
  subcategory TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
