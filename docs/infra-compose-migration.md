# Infra Compose Migration

This runbook moves the dependency layer from the current standalone `rag-*` containers into the Compose-managed stack defined in `backend/docker-compose.yaml`.

Status:
- Completed on 2026-03-26 for the current local environment.
- The dependency layer is now running under Compose with the migrated `rag-*` named volumes.
- `backend/docker-compose.yaml` now treats those `rag-*` named volumes as external shared volumes, which removes the repeated Compose ownership warnings during later startups.

## What Changed

- Compose now uses stable named volumes instead of project-prefixed defaults.
- Image-declared data paths that previously produced anonymous volumes are now mounted explicitly:
  - `rag-zookeeper-data`
  - `rag-zookeeper-log`
  - `rag-zookeeper-secrets`
  - `rag-kafka-data`
  - `rag-kafka-secrets`
- MinIO now uses `/data`, which matches the existing standalone container layout.

## Plan Mode

Use this first. It only inspects the current environment and prints the migration map.

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\scripts\migrate-infra-to-compose.ps1
```

The script identifies whether each dependency currently stores data in:

- an anonymous Docker volume
- a container writable layer
- or a missing source container

## Cutover Mode

Only run this during a maintenance window.

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\scripts\migrate-infra-to-compose.ps1 -Cutover
```

What it does:

1. Stops Compose app services.
2. Stops the standalone dependency containers.
3. Creates the target `rag-*` named volumes if they do not exist.
4. Copies dependency data into those named volumes.
5. Removes the old standalone dependency containers.
6. Starts the full Compose-managed stack.

If a target volume already has data, the script stops unless you explicitly rerun with `-Force`.

## Current Target Volumes

- `rag-mysql-data`
- `rag-es-data`
- `rag-kibana-logs`
- `rag-etcd-data`
- `rag-minio-data`
- `rag-milvus-data`
- `rag-redis-data`
- `rag-zookeeper-data`
- `rag-zookeeper-log`
- `rag-zookeeper-secrets`
- `rag-kafka-data`
- `rag-kafka-secrets`

## Recommended Sequence

1. Keep using the current app-layer Compose setup for normal development.
2. Run the migration script in plan mode and review the reported source paths.
3. Choose a maintenance window.
4. Run `-Cutover`.
5. Validate with:
   - `docker compose -f .\backend\docker-compose.yaml ps`
- `http://localhost:38084/health`
   - `powershell -ExecutionPolicy Bypass -File .\backend\scripts\local-integration.ps1`
