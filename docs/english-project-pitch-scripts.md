# English Project Pitch Scripts

This document provides reusable English pitch scripts for interviews, recruiter calls, and project demos.

## 30-Second Version

I built an enterprise RAG knowledge Q&A platform for private deployment scenarios. It supports document upload, asynchronous parsing and chunking, embedding and indexing, and hybrid retrieval with Milvus and Elasticsearch. My main focus was making the pipeline reliable and turning the system into something that is actually deployable and operable instead of just a demo.

## 60-Second Version

The project is an enterprise-grade RAG knowledge assistant. On the ingestion side, documents go through an asynchronous pipeline with Kafka workers for parsing, chunking, and vectorization. We refactored the pipeline so Kafka carries only lightweight task metadata, while intermediate artifacts are stored outside the queue, which reduces large-message risk and makes retry and replay much safer.

On the retrieval side, the system uses hybrid search: semantic recall in Milvus and keyword recall in Elasticsearch. The results are merged with RRF and optional reranking before the final context is passed to the LLM. I also standardized the local deployment and operations flow with Docker Compose, health checks, recovery scripts, and end-to-end integration tests.

## 3-Minute Version

I worked on an enterprise RAG platform that helps internal teams search and ask questions over private knowledge bases. The interesting part of the project was that the real challenge was not just calling an LLM. The hard part was making document ingestion reliable, improving retrieval accuracy, and ensuring the entire system could be deployed and operated consistently.

For ingestion, users upload files such as PDF, Word, Markdown, or HTML. The system stores the original file, creates a document record, and pushes the task into Kafka. Instead of passing full text through Kafka, we redesigned the pipeline so the message only contains `document_id`, `file_path`, and task metadata. Then separate workers handle parsing, chunking, and vectorization. Intermediate outputs are stored as artifacts between stages, which makes the pipeline easier to retry, replay, and recover from failures.

For retrieval, we use hybrid search. Milvus handles semantic recall, while Elasticsearch handles keyword and phrase recall. That combination matters a lot in enterprise scenarios because users may ask about exact policy names, product terms, or internal abbreviations where semantic search alone is not enough. We merge the two result sets with RRF, apply score blending and threshold filtering, optionally rerank, and then feed the best contexts into the LLM for answer generation.

The other important part was engineering maturity. I introduced schema migration with Alembic, improved Kafka reliability with DLQ and replay tooling, and containerized the full stack with Docker Compose so backend, frontend, workers, MySQL, Redis, Kafka, Elasticsearch, and Milvus can run as one consistent environment. We also added operational scripts for startup, health checks, status, logs, restart, shutdown, and end-to-end local integration validation.

So overall, the value of the project is that it is not just an AI demo. It is a full RAG engineering system that covers ingestion, retrieval, reliability, deployment, and operations.

## Recruiter-Friendly Version

I built a private-deployment RAG platform that converts enterprise documents into searchable knowledge and answerable context for an LLM. The main value I added was reliability and engineering maturity: asynchronous ingestion, hybrid retrieval, failure recovery, local deployment, and integration testing.

## Interview Follow-Up Angles

- Why hybrid retrieval was needed instead of vector search only.
- How Kafka payloads were reduced to task pointers instead of large texts.
- How idempotency and DLQ replay were added for document-processing reliability.
- How local deployment was standardized with Docker Compose and operational scripts.
- How retrieval quality and operability were treated as first-class project goals.
