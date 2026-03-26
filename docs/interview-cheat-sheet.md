# Interview Cheat Sheet

This document is a fast-reference sheet for interviews, recruiter calls, and live project discussions.

## One-Sentence Version

I built an enterprise RAG knowledge platform with asynchronous document ingestion, Milvus plus Elasticsearch hybrid retrieval, and standardized local operations.

## 30-Second Version

The project helps teams turn private documents into searchable knowledge and grounded answers. It supports upload, parsing, chunking, embedding, hybrid retrieval, and answer generation. My main contribution was making the ingestion pipeline reliable and the full stack operable, instead of stopping at a simple model demo.

## 3 Core Selling Points

- Reliable ingestion with Kafka workers, explicit document states, DLQ, replay, and idempotency.
- Better retrieval quality through Milvus plus Elasticsearch hybrid recall.
- Strong local operability with Docker Compose, health checks, scripts, and integration validation.

## Keywords To Mention

- `RAG`
- `Hybrid Retrieval`
- `Kafka`
- `Milvus`
- `Elasticsearch`
- `FastAPI`
- `Next.js`
- `Alembic`
- `DLQ`
- `Idempotency`
- `Docker Compose`
- `Private Deployment`

## Common Questions And Short Answers

### What was the hardest part?

Making the whole system reliable. The challenge was not just connecting an LLM, but handling asynchronous ingestion, retrieval accuracy, and multi-service operations together.

### Why hybrid retrieval?

Because enterprise questions need both semantic similarity and exact terminology matching. Milvus covers the first part, Elasticsearch covers the second.

### Why change Kafka payloads?

To avoid pushing heavy text through the queue. Sending only task pointers makes retries, replay, and failure recovery much safer.

### Why is this a strong engineering project?

Because it combines AI application logic with system reliability, retrieval design, schema governance, local deployment, and demonstrable end-to-end validation.

## Follow-Up Prompts To Invite

- I can walk through the ingestion workflow step by step.
- I can explain why vector-only retrieval was not enough here.
- I can show how DLQ and replay improved reliability.
- I can describe how the local stack is started, checked, and validated.

## Final Closing Line

The project is valuable because it turns RAG from a prototype into a system that can be ingested, retrieved, operated, and explained with confidence.
