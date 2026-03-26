# Interview Technical Deep Dive Q&A

This document is a technical interview preparation pack focused on system design, ingestion reliability, hybrid retrieval, and operability decisions in the project.

## Q1. What problem does this project solve?

It solves the problem of turning private enterprise documents into searchable knowledge and grounded answers. The key challenge is not only connecting an LLM, but building a reliable ingestion pipeline, accurate retrieval, and a deployable full-stack system around it.

## Q2. Why is this project more than an LLM demo?

Because the difficult work is in the system design:

- multi-format document ingestion,
- asynchronous worker orchestration,
- hybrid retrieval,
- failure recovery,
- local deployment and operations.

The project covers the full chain from document upload to answer generation instead of only calling a chat model.

## Q3. How does the ingestion workflow work end to end?

The workflow is:

1. A user uploads a document.
2. The backend stores the file and creates a document record.
3. The backend publishes a lightweight Kafka task.
4. The parser worker extracts normalized text.
5. The splitter worker creates structured chunks and metadata.
6. The vectorizer worker generates embeddings, writes vectors to Milvus, writes full chunk records to Elasticsearch, and finalizes the document status.

The status flow is explicit: `uploading -> parsing -> splitting -> embedding -> completed/failed`.

## Q4. Why split the pipeline into parser, splitter, and vectorizer workers?

Because each stage has different failure modes and resource needs. Splitting them improves:

- fault isolation,
- retry granularity,
- observability,
- throughput tuning,
- recovery behavior.

It also makes it easier to reason about where a document failed and how to resume safely.

## Q5. Why does Kafka carry only `document_id`, `file_path`, and metadata?

Passing full document text or chunk batches through Kafka creates avoidable risk:

- larger messages,
- more fragile retries,
- harder replay,
- more duplication issues.

By sending only lightweight task pointers, each worker can read the real content from storage or stage artifacts. This makes the queue cheaper, cleaner, and easier to recover.

## Q6. Where are intermediate results stored?

Intermediate stage outputs are stored as pipeline artifacts outside Kafka. For example:

- parsed text is stored after parsing,
- chunk JSON is stored after splitting.

This means workers exchange references instead of heavy payloads.

## Q7. Why use both Milvus and Elasticsearch?

They solve different retrieval problems:

- `Milvus` handles semantic recall when user wording differs from source wording.
- `Elasticsearch` handles exact keyword, title, and phrase matching.

Enterprise knowledge questions often require both. Internal abbreviations, policy titles, product names, and exact terminology are easy to miss with vector-only retrieval.

## Q8. How are the two retrieval paths combined?

The system runs vector recall and keyword recall in parallel, then merges results with reciprocal rank fusion and score blending. After that, it can apply optional reranking and threshold filtering before assembling the final context for the LLM.

## Q9. Why is hybrid retrieval important in enterprise scenarios?

Because the user may ask with natural language while the source document uses formal or domain-specific terms. Hybrid retrieval gives better balance between:

- semantic coverage,
- exact-match precision,
- title and phrase sensitivity.

## Q10. What reliability work did you add to Kafka consumption?

The project added:

- manual offset commits,
- DLQ routing,
- replay tooling,
- stage-level idempotency,
- failure-state closure for broken tasks.

This prevents a failed message from silently disappearing and reduces duplicate-write risk.

## Q11. How do you reduce duplicate ingestion side effects?

There are several protections:

- workers validate whether the document is in a legal state for the current stage,
- duplicate or stale messages are less likely to corrupt state,
- the vectorization stage can rebuild downstream data safely instead of blindly appending.

The goal is to make replay and retry operationally safe.

## Q12. Why introduce Alembic instead of using `create_all`?

`create_all` is convenient for an early prototype, but it is weak for long-term evolution. Alembic improves:

- schema change traceability,
- controlled initialization,
- deploy and rollback discipline,
- reproducibility across environments.

## Q13. What makes operability a first-class concern here?

The stack depends on many services: frontend, backend, workers, Kafka, Elasticsearch, Milvus, MySQL, Redis, and supporting infra. Without standardized startup, status, logs, restart, stop, and integration checks, debugging becomes expensive and confidence drops quickly.

## Q14. How do you prove the system actually works end to end?

The project includes local integration validation that checks more than a `200 OK`. The validation covers:

- service health,
- migration execution,
- upload-to-vectorization workflow,
- MySQL state,
- Elasticsearch chunk presence,
- Milvus entity counts.

This makes the result demonstrable and repeatable.

## Q15. What trade-off did you make intentionally?

One intentional trade-off is introducing more system components in exchange for better reliability and retrieval quality. The system is more complex than a minimal prototype, but that complexity is targeted at real bottlenecks: ingestion failures, retrieval precision, and deployment consistency.

## Short Technical Wrap-Up

If I summarize the technical value in one sentence: I turned a RAG prototype into a recoverable engineering system by solving ingestion reliability, hybrid retrieval accuracy, and local multi-service operability together.
