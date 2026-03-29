# Full Stack Compose

The repository now supports a single Docker Compose entrypoint for both infrastructure and application services.

Default host ports:

- frontend: `http://localhost:33004`
- backend: `http://localhost:38084`

## Start the Full Stack

From the repository root:

```bash
python backend/scripts/rag_stack.py start --build
```

If you prefer the manual sequence, it is still:

```bash
python backend/scripts/rag_stack.py ensure-network
python backend/scripts/rag_stack.py ensure-volumes
docker compose -f backend/docker-compose.yaml up --build -d
```

This brings up:

- Infra
  - `rag-mysql8`
  - `rag-es7`
  - `rag-kibana`
  - `rag-etcd`
  - `rag-minio`
  - `rag-milvus`
  - `rag-attu`
  - `rag-redis`
  - `rag-zookeeper`
  - `rag-kafka`
  - `rag-kafka-ui`
- App
  - `rag-backend`
  - `rag-parser`
  - `rag-splitter`
  - `rag-vectorizer`
  - `rag-recall`
  - `rag-front`

Compose-managed dependency data now targets stable named volumes such as `rag-mysql-data`, `rag-es-data`, and `rag-kafka-data`.
These volumes are now treated as external shared volumes so Compose does not try to re-own adopted migration volumes on every startup.

If you already have the dependency containers running as standalone containers on `rag-net`, you can start only the app layer first:

```bash
docker compose -f backend/docker-compose.yaml up -d --no-deps backend parser splitter vectorizer recall front
```

To inspect or migrate the current standalone dependency data into the Compose-managed volumes, use:

```bash
python backend/scripts/migrate_infra_to_compose.py
```

To bootstrap the required named volumes on a fresh machine without warnings, use:

```bash
python backend/scripts/rag_stack.py ensure-volumes
```

## Check Stack Status

```bash
python backend/scripts/rag_stack.py status
```

For machine-readable output:

```bash
python backend/scripts/rag_stack.py status --json
```

The status helper compares Compose container state with the host HTTP endpoints.
If an endpoint is reachable while the Compose service is stopped, it reports a warning so you can spot host-side processes that are masking the real stack state.

## View Logs

```bash
python backend/scripts/rag_stack.py logs --tail 100
```

To follow logs continuously:

```bash
python backend/scripts/rag_stack.py logs --follow
```

## Run Playwright Smoke

Run the shared browser smoke workflow through the operator CLI:

```bash
python backend/scripts/rag_stack.py smoke --ensure-admin
```

To ensure the stack is up first:

```bash
python backend/scripts/rag_stack.py smoke --start-stack --ensure-admin
```

Artifacts are written under `front/test-results/playwright-smoke/operator/` with both `runs/<timestamp>/` and `latest/` outputs.
The recommended credential source is the dedicated `PLAYWRIGHT_SMOKE_USERNAME`, `PLAYWRIGHT_SMOKE_EMAIL`, and `PLAYWRIGHT_SMOKE_PASSWORD` contract documented in `backend/.env.example`.

## Restart Specific Services

Restart one or more compose services:

```bash
python backend/scripts/rag_stack.py restart backend
```

Restart a service and its app-layer dependents:

```bash
python backend/scripts/rag_stack.py restart backend --include-dependents
```

See [compose-troubleshooting.md](./compose-troubleshooting.md) for the full troubleshooting flow.

## Stop the Full Stack

```bash
python backend/scripts/rag_stack.py stop
```

This stops the services but keeps the containers for a fast restart.

To remove the compose-managed containers too:

```bash
python backend/scripts/rag_stack.py stop --remove-containers
```

To also remove orphaned compose containers:

```bash
python backend/scripts/rag_stack.py stop --remove-containers --remove-orphans
```

Because the dependency volumes are declared as external, even the remove-container path preserves the shared `rag-*` named volumes.

## Network

All services join the same Docker bridge network:

- `rag-net`

`rag-net` is treated as an external shared network, so create or reconcile it first if needed:

```bash
python backend/scripts/rag_stack.py ensure-network
```

This keeps service discovery simple:

- backend reaches MySQL via `rag-mysql8`
- backend reaches Redis via `rag-redis`
- backend reaches Elasticsearch via `http://rag-es7:9200`
- backend reaches Milvus via `rag-milvus`
- backend and workers reach Kafka via `rag-kafka:29092`
- frontend proxies server-side calls to `http://backend:8000`
- `backend` and the Kafka workers now wait for `rag-kafka` to pass its health check before starting

## Environment

The backend, parser, splitter, vectorizer, and recall services load `backend/.env` through `env_file`, then Compose overrides the host-style endpoints with container-internal service names.

Before the first `up`, make sure:

- `backend/.env` exists
- `JWT_SECRET_KEY` and `AES_ENCRYPTION_KEY` are set
- `EMBEDDING_MODEL_PATH` points to a model directory mounted under `backend/models`

## Container Names

I kept the existing dependency container names for compatibility with the current scripts, the shared `rag-net` network, and the already running standalone dependency containers.

- Existing infra names remain unchanged
- New app-layer names use:
  - `rag-backend`
  - `rag-parser`
  - `rag-splitter`
  - `rag-vectorizer`
  - `rag-recall`
  - `rag-front`

That gives one consistent naming scheme without breaking the current dependency references.
