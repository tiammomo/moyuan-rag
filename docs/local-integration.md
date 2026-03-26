# Local Integration Runbook

This repository now includes a repeatable local integration flow for the backend document pipeline.

## Scripts

- `backend/scripts/local-integration.ps1`
  - PowerShell wrapper that can start local services, run Alembic migrations, start the API and workers, and launch the integration scenario.
- `backend/scripts/run_local_integration.py`
  - Python scenario runner that:
    - registers an admin user
    - logs in
    - creates a local embedding LLM record
    - creates a knowledge base
    - uploads a document
    - polls until the document reaches `completed`
    - verifies MySQL, Elasticsearch, and Milvus writes

## Prerequisites

- `backend/.env` exists and contains safe local secrets.
- `EMBEDDING_MODEL_PATH` in `backend/.env` points to a local model directory that exists.
- Docker Desktop is running if you want the wrapper to start infrastructure for you.

## One-shot Command

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\scripts\local-integration.ps1 -StartInfra -SyncDeps
```

If your containers are already up and your virtual environment is ready, a faster rerun is:

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\scripts\local-integration.ps1
```

## Docker Dependency Network

All dependency containers should live on the same bridge network: `rag-net`.

- `backend/docker-compose.yaml` now declares an explicit Docker network name:
  - `rag-net`
- Existing standalone containers can be attached to that network with:

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\scripts\ensure-rag-network.ps1
```

- `backend/scripts/local-integration.ps1 -StartInfra` now runs this network check automatically before `docker compose up -d`.
- `backend/scripts/local-integration.ps1 -StartInfra` now runs both the network check and the volume bootstrap automatically before `docker compose up -d`.

## Docker Named Volumes

The compose stack now treats the shared `rag-*` data volumes as external named volumes.

- Bootstrap or reconcile them with:

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\scripts\ensure-rag-volumes.ps1
```

- To inspect the current members:

```powershell
docker network inspect rag-net
```

## Useful Options

- `-StartInfra`
  - Runs `docker compose up -d` with `backend/docker-compose.yaml` and waits for local ports.
- `-SyncDeps`
  - Reinstalls `backend/requirements.txt` into `backend/.venv`.
- `-StopStartedProcesses`
  - Stops only the backend and worker processes that the wrapper started itself.
- `-UploadFile <path>`
  - Overrides the default upload file. The default is `docs/optimization-roadmap.md`.

## Logs

Wrapper-managed process logs are written to `backend/run-logs/`:

- `integration-backend.out.log`
- `integration-backend.err.log`
- `integration-parser.out.log`
- `integration-parser.err.log`
- `integration-splitter.out.log`
- `integration-splitter.err.log`
- `integration-vectorizer.out.log`
- `integration-vectorizer.err.log`

Application logs still go to `backend/logs/`.

## Reliability Notes

- Kafka pipeline reliability hardening, dead-letter topics, and operator recovery steps are documented in `docs/kafka-reliability.md`.
