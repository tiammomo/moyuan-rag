# Case Study: Problem, Solution, and Impact

This document presents the project as a case study that can be reused in interviews, portfolio pages, outbound applications, and technical writeups.

## Project Context

The project is an enterprise-oriented RAG knowledge assistant designed for private knowledge bases. It supports document upload, asynchronous parsing and chunking, embedding and indexing, hybrid retrieval, and grounded question answering. The practical goal is to turn internal documents into searchable and answerable knowledge without losing deployment control or operational visibility.

## Business Problem

Many internal teams have large amounts of private documents, but those documents are difficult to search efficiently and even harder to turn into reliable Q&A experiences. Traditional keyword search is often too literal, while raw LLM chat without retrieval is not grounded enough for enterprise use.

The business need behind this project is:

- Make internal knowledge searchable across heterogeneous document types.
- Improve answerability without exposing private documents to public-only workflows.
- Support self-hosted deployment and practical operations in a multi-service environment.
- Reduce the manual effort needed to locate policies, product documents, and internal process knowledge.

## Core Constraints

This project had to work under several real engineering constraints:

- Documents come in multiple formats such as PDF, Word, Markdown, HTML, and plain text.
- Ingestion is multi-stage and failure-prone because parsing, chunking, and embedding can each fail independently.
- Enterprise retrieval needs both semantic understanding and exact terminology matching.
- The system depends on multiple moving services including Kafka, Elasticsearch, Milvus, MySQL, Redis, frontend, backend, and worker processes.
- Local deployment and repeatable recovery matter as much as model integration.

## Why A Simple Demo Was Not Enough

A prototype that only uploads text and calls an LLM would not solve the actual problem. The hard parts were:

- keeping the ingestion pipeline reliable,
- making retrieval accurate enough for enterprise content,
- and turning the system into something deployable, observable, and recoverable.

That is why the project evolved into a full engineering system rather than a model wrapper.

## Solution Design

## 1. Asynchronous Ingestion Pipeline

The ingestion path is split into separate worker stages:

- `parse`
- `split`
- `vectorize`

Kafka is used to decouple stages and isolate failures. Instead of passing full text or batch chunk payloads through Kafka, the system now publishes only lightweight task messages that contain:

- `document_id`
- `file_path`
- task metadata

Intermediate artifacts are stored outside Kafka between stages. This reduces queue payload size and makes retries and replay safer.

## 2. Explicit Document State Machine

The pipeline is tracked with explicit states:

- `uploading`
- `parsing`
- `splitting`
- `embedding`
- `completed`
- `failed`

This improves observability for both users and operators and reduces ambiguity during error recovery.

## 3. Hybrid Retrieval

The retrieval path combines:

- `Milvus` for semantic recall
- `Elasticsearch` for keyword and phrase recall

The two result sets are merged with reciprocal rank fusion and score blending, with optional reranking and threshold filtering before final context assembly.

This design is important because enterprise knowledge questions often require both:

- semantic matching when wording differs from source text,
- exact matching when the answer depends on policy names, product terms, or internal abbreviations.

## 4. Reliability and Recovery

The project was strengthened with:

- manual Kafka offset commits,
- dead-letter queue routing,
- replay scripts,
- stage-level idempotency,
- explicit failure handling,
- migration-based schema control with Alembic.

These changes move the system from "works when happy-path only" to "can recover from realistic failures."

## 5. Local Full-Stack Operations

The project runs through a standardized Docker Compose setup that covers:

- frontend,
- backend,
- parser, splitter, vectorizer workers,
- MySQL,
- Redis,
- Kafka,
- Elasticsearch,
- Milvus,
- related supporting services.

Operational scripts were added for startup, status, logs, restart, shutdown, and end-to-end local integration validation.

## Engineering Decisions That Mattered

## Kafka Should Carry Pointers, Not Heavy Content

Passing large content through Kafka increases operational risk, complicates retries, and makes duplicate handling messier. Using task pointers plus external artifacts keeps the queue lightweight and easier to recover.

## Hybrid Retrieval Beats A Single Recall Strategy

Vector-only retrieval is often not enough for enterprise knowledge. Exact terminology still matters. The combination of Milvus and Elasticsearch gives better coverage for realistic internal Q&A use cases.

## Reliability Work Is Product Work

For RAG systems, ingestion reliability is part of product quality. If documents cannot be processed consistently or recovered after failures, the downstream chat experience will never be trustworthy.

## Operational Consistency Is A Feature

A locally runnable and health-checked stack lowers the barrier for debugging, onboarding, demos, and repeatable testing. This matters for both internal engineering usage and external project presentation.

## Outcome

The result is an enterprise-ready RAG engineering project with:

- end-to-end ingestion from upload to vectorized knowledge,
- hybrid retrieval for grounded answers,
- recovery mechanisms for pipeline failures,
- local orchestration and validation for repeatable operation,
- and reusable delivery materials for resumes, demos, and interviews.

## Reusable Closing Line

This project shows how to turn RAG from a prototype into an engineering system by solving three real problems at once: reliable ingestion, accurate retrieval, and operable deployment.
