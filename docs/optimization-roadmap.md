# Project Optimization Roadmap

## P0

- [x] Add startup safety guards for risky bootstrap settings
- [x] Disable auto schema bootstrap and default admin creation by default
- [x] Remove hard-coded bootstrap IDs for admin, LLM, and knowledge base
- [x] Align document processing status to include `splitting`
- [x] Backfill missing backend runtime and quality dependencies
- [x] Add a frontend `type-check` script
- [x] Refactor document pipeline messages to pass metadata only
- [ ] Replace document preview URL token flow with authenticated blob previews everywhere

## P1

- [x] Introduce database migrations to replace `create_all`
- [ ] Add idempotency, retries, and dead-letter handling for Kafka consumers
- [ ] Add task persistence for document pipeline progress
- [ ] Build a retrieval benchmark dataset and metrics baseline

## P2

- [ ] Split oversized frontend pages into feature components and hooks
- [ ] Replace polling-based progress refresh with SSE or WebSocket updates
- [ ] Benchmark Embedding, Milvus, and Elasticsearch independently
