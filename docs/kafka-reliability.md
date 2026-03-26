# Kafka Reliability

## Scope

This document records the reliability hardening completed for the Kafka-backed document pipeline.

## Implemented Changes

- Kafka producers now retry startup and failed sends, including a forced restart before the final resend attempt.
- Kafka consumers now disable auto-commit and only commit offsets after either:
  - the worker callback succeeds
  - the failed message is successfully routed to a dead-letter topic
- Dead-letter topics now follow the pattern `<source-topic>.dlq`.
  - `rag.document.upload.dlq`
  - `rag.document.parsed.dlq`
  - `rag.document.chunks.dlq`
- Upload and retry task dispatch now fail closed.
  - If the upload task cannot be published, the document is marked `failed` instead of staying stuck in `uploading`.
  - If a retry task cannot be published, the document is moved back to `failed` with an explicit queue error.
- Worker stage handlers now guard against stale replays.
  - Parser only replays `uploading/parsing`
  - Splitter only replays `parsing/splitting`
  - Vectorizer only replays `splitting/embedding`
- Vectorizer now deletes existing document rows from Milvus and Elasticsearch before reinserting chunks so Kafka replays do not duplicate indexed content.
- Compose startup already waits for Kafka health before starting the API and workers.

## Verified On 2026-03-26

- End-to-end upload after the changes succeeded with `document_id=11`, `chunk_count=5`, `es_chunk_count=5`, `milvus_entity_count=5`.
- A malformed message was published to `rag.document.upload` and was successfully routed to `rag.document.upload.dlq`.
- A stale replay of the completed upload message for `document_id=11` left the document and downstream storage unchanged.
  - document status remained `completed`
  - Elasticsearch count stayed `5`
  - Milvus entity count stayed `5`
- A synthetic DLQ record with a valid upload payload was replayed back to `rag.document.upload`, and the completed `document_id=11` still remained unchanged with downstream counts staying `5`.
- After restarting `rag-kafka`, a fresh end-to-end upload still succeeded with `document_id=12`, `chunk_count=5`, `es_chunk_count=5`, `milvus_entity_count=5`.

## Operator Recovery Flow

1. Confirm the stack is healthy.
   - `docker compose -f .\backend\docker-compose.yaml ps`
   - `Invoke-WebRequest -UseBasicParsing http://localhost:38084/health`
2. Inspect document statuses.
   - Failed documents should show an explicit `error_msg`.
   - Queue-dispatch failures now surface as `Upload queue dispatch failed` or `Retry queue dispatch failed`.
3. Inspect the relevant dead-letter topic when a worker callback fails.
   - Source topics:
     - `rag.document.upload`
     - `rag.document.parsed`
     - `rag.document.chunks`
   - Dead-letter topics:
     - `rag.document.upload.dlq`
     - `rag.document.parsed.dlq`
     - `rag.document.chunks.dlq`
   - Quick inspection helper:
     - `powershell -ExecutionPolicy Bypass -File .\backend\scripts\kafka-dlq.ps1 -Topic rag.document.upload.dlq`
4. Fix the root cause first.
   - Examples: broken parser input, missing artifact path, temporary Kafka outage, Milvus or Elasticsearch availability.
5. Recover the document.
   - If the document is already marked `failed`, use the existing retry flow from the API/UI.
   - If the failure only exists in the DLQ, republish the original payload after the root cause is fixed.
   - Replay helper:
     - `powershell -ExecutionPolicy Bypass -File .\backend\scripts\replay-kafka-dlq.ps1 -Topic rag.document.upload.dlq -Partition 0 -Offset <offset>`
   - Guardrail:
     - the replay helper refuses to resend DLQ records whose `payload` is not valid JSON
6. Re-run the local integration smoke test if the issue affected infrastructure or workers.
   - `powershell -ExecutionPolicy Bypass -File .\backend\scripts\local-integration.ps1`

## Notes

- The poll-based status API can still skip intermediate states if a stage completes between polling intervals. Worker logs remain the source of truth for full stage-by-stage timing.
- Existing migrated Docker volumes still emit Compose ownership warnings because they were adopted from standalone containers. The warnings are cosmetic for the current setup.
