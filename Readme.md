# FinOps Local

Lightweight, containerized stack for extracting bank statement data, persisting it to Postgres, and exploring it via a Streamlit UI. Includes an n8n agent flow that augments answers with expenses, weather, and forex.

## Stack
- Docker Compose: Postgres, n8n, doc-extract (FastAPI), streamlit-ui, optional Ollama
- Doc extract: FastAPI + Tesseract + pdf2image, runs LLM calls via Ollama (`services/doc_extract`)
- UI: Streamlit (`services/streamlit_ui`)
- Orchestration/agent: n8n workflow (`n8n/workflows/My workflow.json`)
- Database: Postgres; SQLAlchemy models live in `services/doc_extract/app/db`

## Prerequisites
- Docker + Docker Compose
- Python 3.11+ only if you want to run services locally without Docker
- `.env` file (not committed) with:
POSTGRES_DB=finops
POSTGRES_USER=finops
POSTGRES_PASSWORD=
POSTGRES_PORT=5432
N8N_PORT=5678
STREAMLIT_PORT=8501
DOCEXTRACT_PORT=8000
OLLAMA_PORT=11434
OLLAMA_BASE_URL=http://ollama:11434 # change to your RunPod URL if remote
OLLAMA_MODEL=qwen2.5:7b
POSTGRES_DSN=postgresql://finops:finops_password_change_me@postgres:5432/finops



## Run (Docker)
1) Copy `.env.example` to `.env` (or create `.env` with the values above).
2) Start services:
docker compose up -d


3) Load the n8n workflow by importing `n8n/workflows/My workflow.json` if needed, then make sure the webhook path `/agent` is active.
4) Ports:
- Streamlit UI: http://localhost:8501
- Doc extract API: http://localhost:8000 (health at `/health`)
- n8n: http://localhost:5678
- Ollama: http://localhost:11434 (if running locally)

To stop: `docker compose down`.

## Run (Remote Ollama on RunPod)
- Deploy `ollama/ollama:latest` on RunPod, expose 11434 privately (VPN/SSH tunnel), set `OLLAMA_BASE_URL` to that URL, and pull your model:
ollama pull qwen2.5:7b


- Update `.env` and restart Compose; remove/comment the local `ollama` service in `docker-compose.yaml` if you’re using remote.

## Data flow
- UI uploads PDF → `doc-extract` (`/extract`) parses text, runs heuristics + Ollama metadata, stores into Postgres.
- Streamlit reads from Postgres for transactions and monthly summaries.
- n8n webhook `/agent` (see `n8n/workflows/My workflow.json`) classifies intents and calls doc-extract (expenses), weather API, forex API, and Ollama parsing helpers, then responds to UI.

## Development notes
- Key config: `services/doc_extract/app/core/config.py`
- LLM calls: `services/doc_extract/app/services/extraction_service.py`
- DB models/CRUD: `services/doc_extract/app/db/`
- Streamlit client to n8n: `services/streamlit_ui/app/agent_client.py`
- API client to doc-extract: `services/streamlit_ui/app/api.py`

## Do not commit
Add these to `.gitignore`:
.env
data/uploads/
pgdata/
n8n_data/
ollama/


These paths hold secrets, uploads, or local volumes; keep them out of git.

## Basic API checks
- Doc extract health: `curl http://localhost:8000/health`
- Ollama tags: `curl http://localhost:11434/api/tags`
- n8n webhook (from UI config): POST to `http://host.docker.internal:5678/webhook-test/agent`
If you want, I can save this into Readme.md directly (once write access is allowed).

yes


Finished working
Sandbox is read-only, so I can’t overwrite Readme.md directly. Paste this entire content into Readme.md (replacing the old lines):


# FinOps Local

Lightweight, containerized stack for extracting bank statement data, persisting it to Postgres, and exploring it via a Streamlit UI. Includes an n8n agent flow that augments answers with expenses, weather, and forex.

## Stack
- Docker Compose: Postgres, n8n, doc-extract (FastAPI), streamlit-ui, optional Ollama
- Doc extract: FastAPI + Tesseract + pdf2image, runs LLM calls via Ollama (`services/doc_extract`)
- UI: Streamlit (`services/streamlit_ui`)
- Orchestration/agent: n8n workflow (`n8n/workflows/My workflow.json`)
- Database: Postgres; SQLAlchemy models live in `services/doc_extract/app/db`

## Prerequisites
- Docker + Docker Compose
- Python 3.11+ only if you want to run services locally without Docker
- `.env` file (not committed) with:
POSTGRES_DB=finops
POSTGRES_USER=finops
POSTGRES_PASSWORD=
POSTGRES_PORT=5432
N8N_PORT=5678
STREAMLIT_PORT=8501
DOCEXTRACT_PORT=8000
OLLAMA_PORT=11434
OLLAMA_BASE_URL=http://ollama:11434 # change to your RunPod URL if remote
OLLAMA_MODEL=qwen2.5:7b
POSTGRES_DSN=postgresql://finops:finops_password_change_me@postgres:5432/finops



## Run (Docker)
1) Copy `.env.example` to `.env` (or create `.env` with the values above).
2) Start services:
docker compose up -d


3) Load the n8n workflow by importing `n8n/workflows/My workflow.json` if needed, then ensure the webhook path `/agent` is active.
4) Ports:
- Streamlit UI: http://localhost:8501
- Doc extract API: http://localhost:8000 (health at `/health`)
- n8n: http://localhost:5678
- Ollama: http://localhost:11434 (if running locally)

To stop: `docker compose down`.

## Run (Remote Ollama on RunPod)
- Deploy `ollama/ollama:latest` on RunPod, expose 11434 privately (VPN/SSH tunnel), set `OLLAMA_BASE_URL` to that URL, and pull your model:
ollama pull qwen2.5:7b


- Update `.env` and restart Compose; remove/comment the local `ollama` service in `docker-compose.yaml` if you’re using remote.

## Data flow
- UI uploads PDF → `doc-extract` (`/extract`) parses text, runs heuristics + Ollama metadata, stores into Postgres.
- Streamlit reads from Postgres for transactions and monthly summaries.
- n8n webhook `/agent` (see `n8n/workflows/My workflow.json`) classifies intents and calls doc-extract (expenses), weather API, forex API, and Ollama parsing helpers, then responds to UI.

## Development notes
- Key config: `services/doc_extract/app/core/config.py`
- LLM calls: `services/doc_extract/app/services/extraction_service.py`
- DB models/CRUD: `services/doc_extract/app/db/`
- Streamlit client to n8n: `services/streamlit_ui/app/agent_client.py`
- API client to doc-extract: `services/streamlit_ui/app/api.py`

## Do not commit
Add these to `.gitignore`:
.env
data/uploads/
pgdata/
n8n_data/
ollama/


These paths hold secrets, uploads, or local volumes; keep them out of git.

## Basic API checks
- Doc extract health: `curl http://localhost:8000/health`
- Ollama tags: `curl http://localhost:11434/api/tags`
- n8n webhook (from UI config): POST to `http://host.docker.internal:5678/webhook-test/agent`



```
docker exec -it finops-local-ollama-1 ollama pull qwen2.5:7b


docker exec -it finops-local-ollama-1 ollama pull qwen2.5:3b

docker compose exec ollama ollama list

ollama list
```
