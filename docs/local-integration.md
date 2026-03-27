# Local Integration Runbook

This repository includes a repeatable local integration flow for the backend document pipeline.

Default host ports used by the wrapper and compose stack:

- frontend: `http://localhost:33004`
- backend API: `http://localhost:38084`

## Scripts

- `backend/scripts/local_integration.py`
  - Cross-platform wrapper that can start compose services, prepare the local Python environment, and run the integration scenario.
- `backend/scripts/run_local_integration.py`
  - Scenario runner that:
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

```bash
python backend/scripts/local_integration.py --start-infra --sync-deps
```

If your containers are already up and `backend/.venv` is ready, a faster rerun is:

```bash
python backend/scripts/local_integration.py
```

## Docker Dependency Network

All dependency containers should live on the same bridge network: `rag-net`.

- `backend/docker-compose.yaml` declares an explicit Docker network name: `rag-net`
- Existing standalone containers can be attached with:

```bash
python backend/scripts/rag_stack.py ensure-network
```

- `python backend/scripts/local_integration.py --start-infra` now runs the network check automatically before compose startup.
- `python backend/scripts/local_integration.py --start-infra` also runs the named-volume bootstrap before compose startup.

## Docker Named Volumes

The compose stack treats the shared `rag-*` data volumes as external named volumes.

- Bootstrap or reconcile them with:

```bash
python backend/scripts/rag_stack.py ensure-volumes
```

- To inspect current network members:

```bash
docker network inspect rag-net
```

## Useful Options

- `--start-infra`
  - Runs the compose stack first and waits for service health.
- `--compose-build`
  - Rebuilds images when starting compose services.
- `--sync-deps`
  - Reinstalls `backend/requirements.txt` into `backend/.venv`.
- `--stop-started-processes`
  - Stops only the backend and worker processes that this wrapper started itself.
- `--upload-file <path>`
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

- Kafka pipeline reliability hardening, dead-letter topics, and operator recovery steps are documented in [kafka-reliability.md](./kafka-reliability.md).
