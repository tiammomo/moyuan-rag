# Case Study: Business Difficulties and Technical Challenges

This document provides reusable interview answers and talking points around the business difficulties and technical challenges behind the project.

## Business Difficulty 1: Internal Knowledge Exists, But It Is Not Operational

### Problem

Organizations often have a large amount of internal documentation, but the knowledge is buried in files, folders, and inconsistent formats. People spend time searching manually instead of reusing knowledge efficiently.

### Why It Matters

- Search cost is high.
- Knowledge reuse is low.
- Answers depend too much on who remembers the right document.

### Project Response

The project turns documents into a structured RAG pipeline so that internal knowledge can be uploaded, indexed, retrieved, and used as grounded context during answer generation.

## Business Difficulty 2: Enterprise Scenarios Need Private Deployment

### Problem

Many teams cannot rely on public-only AI workflows for internal documents, especially when the content includes business policies, process documents, customer deliverables, or proprietary product information.

### Why It Matters

- Compliance and privacy expectations are higher.
- Deployment control becomes part of product value.
- Reliability issues are harder to hide in self-hosted environments.

### Project Response

The stack was designed around local orchestration with Docker Compose and explicit operational scripts so the system can be started, checked, validated, and recovered in a self-hosted environment.

## Business Difficulty 3: Exact Terms Matter

### Problem

Enterprise users often ask about exact policy titles, product names, abbreviations, or internal terminology. A purely semantic system may retrieve text that is related but not precise enough.

### Project Response

The retrieval path combines semantic recall in Milvus with keyword and phrase recall in Elasticsearch, then fuses the results before generation.

## Technical Challenge 1: Multi-Stage Ingestion Fails In Real Life

### Problem

Parsing, chunking, and vectorization are separate steps, and each can fail independently. Without strong state management, failures can leave the system in inconsistent states.

### Project Response

- split ingestion into separate workers,
- track explicit document status,
- add dead-letter queue handling,
- support replay and failure recovery,
- use stage-level idempotency.

### Reusable Interview Answer

One of the hardest parts was not retrieval itself but the ingestion pipeline. A document has to pass through parsing, splitting, and vectorization, and failures in any stage can lead to inconsistent states or duplicate data. I addressed that by decoupling stages with Kafka, making the message payload lightweight, adding explicit state transitions, and strengthening reliability with DLQ, replay, and idempotency.

## Technical Challenge 2: Kafka Should Not Be A Document Transport Layer

### Problem

Large payloads in Kafka make retries, duplicate handling, and observability more painful. They also increase the operational cost of a failure.

### Project Response

Kafka now carries only:

- `document_id`
- `file_path`
- task metadata

Stage outputs are written as intermediate artifacts outside the queue.

### Reusable Interview Answer

We redesigned the Kafka payload model so the queue carries task pointers instead of the full document content. That made the pipeline lighter, reduced operational risk, and made replay safer because each worker can re-read artifacts instead of depending on oversized queue payloads.

## Technical Challenge 3: Retrieval Quality Needs More Than Vectors

### Problem

Vector retrieval is strong for semantic similarity, but enterprise queries often need exact phrase matching as well.

### Project Response

The system runs vector recall and keyword recall in parallel, merges them with reciprocal rank fusion and score blending, then optionally reranks before generating the final answer.

### Reusable Interview Answer

We used hybrid retrieval because enterprise knowledge is full of exact terms that matter. Milvus gives us semantic recall, Elasticsearch gives us exact keyword and phrase matching, and together they improve both coverage and precision.

## Technical Challenge 4: Operability Is Part Of The Product

### Problem

A multi-service RAG stack is hard to trust if it cannot be started, monitored, and recovered consistently.

### Project Response

The project standardized local operations with:

- one-stack Docker Compose orchestration,
- health checks,
- startup, status, logs, restart, and stop scripts,
- end-to-end local integration validation.

### Reusable Interview Answer

I treated operability as a first-class engineering concern. A RAG platform is not just a model endpoint. It depends on many services, so consistent startup, health checks, logs, restart flows, and integration validation are necessary if you want it to be useful beyond a demo.

## Suggested Final Wrap-Up

The key lesson from the project is that enterprise RAG is a systems problem. The challenge is not only model quality, but also reliable ingestion, accurate retrieval, and operational consistency.
