# Full Stack Compose

The repository now supports a single Docker Compose entrypoint for both infrastructure and application services.

Default host ports:

- frontend: `http://localhost:33004`
- backend: `http://localhost:38084`

## Start the Full Stack

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\scripts\start-rag-stack.ps1 -Build
```

If you prefer the manual sequence, it is still:

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\scripts\ensure-rag-network.ps1
powershell -ExecutionPolicy Bypass -File .\backend\scripts\ensure-rag-volumes.ps1
docker compose -f .\backend\docker-compose.yaml up --build -d
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
  - `rag-front`

Compose-managed dependency data now targets stable named volumes such as `rag-mysql-data`, `rag-es-data`, and `rag-kafka-data`.
These volumes are now treated as external shared volumes so Compose does not try to re-own adopted migration volumes on every startup.

If you already have the dependency containers running as standalone containers on `rag-net`, you can start only the app layer first:

```powershell
docker compose -f .\backend\docker-compose.yaml up -d --no-deps backend parser splitter vectorizer front
```

To inspect or migrate the current standalone dependency data into the Compose-managed volumes, use:

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\scripts\migrate-infra-to-compose.ps1
```

To bootstrap the required named volumes on a fresh machine without warnings, use:

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\scripts\ensure-rag-volumes.ps1
```

## Check Stack Status

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\scripts\status-rag-stack.ps1
```

For machine-readable output:

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\scripts\status-rag-stack.ps1 -Json
```

The status helper compares Compose container state with the host HTTP endpoints.
If an endpoint is reachable while the Compose service is stopped, it reports a warning so you can spot host-side processes that are masking the real stack state.

## View Logs

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\scripts\logs-rag-stack.ps1 -Tail 100
```

To follow logs continuously:

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\scripts\logs-rag-stack.ps1 -Follow
```

## Restart Specific Services

Restart one or more compose services:

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\scripts\restart-rag-stack.ps1 -Services backend
```

Restart a service and its app-layer dependents:

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\scripts\restart-rag-stack.ps1 -Services backend -IncludeDependents
```

See [compose-troubleshooting.md](./compose-troubleshooting.md) for the full troubleshooting flow.

## Stop the Full Stack

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\scripts\stop-rag-stack.ps1
```

This stops the services but keeps the containers for a fast restart.

To remove the compose-managed containers too:

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\scripts\stop-rag-stack.ps1 -RemoveContainers
```

To also remove orphaned compose containers:

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\scripts\stop-rag-stack.ps1 -RemoveContainers -RemoveOrphans
```

Because the dependency volumes are declared as external, even the remove-container path preserves the shared `rag-*` named volumes.

## Network

All services join the same Docker bridge network:

- `rag-net`

`rag-net` is treated as an external shared network, so create or reconcile it first if needed:

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\scripts\ensure-rag-network.ps1
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

The backend, parser, splitter, and vectorizer services load `backend/.env` through `env_file`, then Compose overrides the host-style endpoints with container-internal service names.

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
  - `rag-front`

That gives one consistent naming scheme without breaking the current dependency references.
