# English Delivery Kit

This document is the English-facing delivery package for resumes, LinkedIn, interviews, and external project introductions. The wording stays aligned with the current repository implementation.

## One-Line Summary

An enterprise-grade RAG knowledge assistant with asynchronous document ingestion, hybrid retrieval on Milvus and Elasticsearch, and production-oriented local deployment and operations workflows.

## Project Positioning

- Built for internal knowledge search, policy lookup, product documentation Q&A, and private enterprise deployment scenarios.
- Focuses on engineering reliability, hybrid retrieval accuracy, and end-to-end operability instead of stopping at an LLM demo.
- Covers the full chain from document ingestion to answer generation, plus local infrastructure orchestration and troubleshooting.

## Resume Version

Project: Enterprise RAG Knowledge Q&A Platform

Role: Backend / Full-Stack Engineer (RAG Focus)

Stack: `FastAPI`, `Next.js`, `MySQL`, `Redis`, `Kafka`, `Elasticsearch`, `Milvus`, `Docker Compose`

Description:

Designed and implemented an enterprise-oriented RAG platform that supports multi-format document upload, asynchronous parsing and chunking, embedding and indexing, hybrid retrieval, conversational Q&A, and local deployment workflows. The project emphasizes reliability across the document-processing pipeline, retrieval quality, and practical operations for self-hosted environments.

## Resume Highlights

- Designed and implemented the end-to-end RAG workflow covering upload, parsing, chunking, embedding, hybrid retrieval, answer generation, and management-side capabilities.
- Split document ingestion into `parse / split / vectorize` Kafka workers to improve throughput, fault isolation, and recovery.
- Refactored Kafka payloads to pass only `document_id`, `file_path`, and task metadata, avoiding large-message transport of full text and chunk batches.
- Built hybrid retrieval with semantic recall in `Milvus` and keyword recall in `Elasticsearch`, then merged results with RRF, score blending, threshold filtering, and optional reranking.
- Introduced `Alembic` migrations to replace startup-time `create_all`, improving schema governance and deployment safety.
- Strengthened pipeline reliability with manual offset commits, DLQ routing, replay tooling, stage-level idempotency, and explicit failure handling.
- Unified backend, frontend, workers, and infra services into a single Docker Compose stack with standard startup, status, logs, restart, and stop scripts.
- Added repeatable local integration validation to verify end-to-end ingestion and cross-store consistency in MySQL, Elasticsearch, and Milvus.

## Business-Facing Value

- Turns internal documents into searchable and answerable knowledge assets with support for private deployment.
- Balances semantic matching and exact terminology matching, which is critical for enterprise documents, product names, policy clauses, and internal jargon.
- Reduces operational overhead by standardizing local orchestration, recovery, and troubleshooting procedures.

## Recommended Role Targets

- RAG Engineer
- AI Application Engineer
- LLM Application Backend Engineer
- AI Platform Engineer
- Retrieval / Search Engineer with LLM focus

## Short Intro for Interviews

I built an enterprise-grade RAG knowledge platform that goes beyond model integration. The core work was making the document ingestion pipeline reliable, improving retrieval quality with Milvus plus Elasticsearch hybrid search, and turning the whole stack into something that can be deployed, validated, and operated locally.

## Recommended Keywords

- `RAG`
- `Hybrid Retrieval`
- `Milvus`
- `Elasticsearch`
- `Kafka`
- `FastAPI`
- `Docker Compose`
- `DLQ`
- `Idempotency`
- `Private Deployment`

## Related Materials

- [english-project-pitch-scripts.md](./english-project-pitch-scripts.md)
- [english-repo-copy-assets.md](./english-repo-copy-assets.md)
- [external-delivery-kit.md](./external-delivery-kit.md)
- [rag-workflow-hybrid-retrieval.md](./rag-workflow-hybrid-retrieval.md)
- [rag-interview-qa.md](./rag-interview-qa.md)
- [showcase-architecture-workflow.md](./showcase-architecture-workflow.md)
- [showcase-demo-walkthrough.md](./showcase-demo-walkthrough.md)
- [showcase-capture-checklist.md](./showcase-capture-checklist.md)
