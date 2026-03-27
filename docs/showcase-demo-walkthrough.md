# Showcase Demo Walkthrough

This document is a practical walkthrough for recording or presenting the project as a short product demo. The steps below align with the current local ports:

- Frontend: `http://localhost:33004`
- Backend API: `http://localhost:38084`
- Backend health check: `http://localhost:38084/health`
- API docs: `http://localhost:38084/docs`

## Demo Goal

Show that the project is not only an AI interface, but a complete RAG system that supports ingestion, retrieval, chat, and local operations.

## Recommended Demo Length

- Short version: 2 to 3 minutes
- Full version: 5 to 7 minutes

## Demo Storyline

1. Show the running stack and confirm the frontend and backend are reachable.
2. Open the knowledge-base page and show an existing knowledge base or create one if needed.
3. Upload a sample document and explain the asynchronous ingestion workflow.
4. Show the document status changing and explain parse, split, and embedding stages.
5. Open the chat page and ask a grounded question against the uploaded knowledge.
6. Show the answer with references and explain hybrid retrieval.
7. Close by showing the local operations scripts and health/status checks.

## Recording Script

### 1. Start With System Availability

- Open `http://localhost:33004`
- Mention that the frontend is running on port `33004`
- Open `http://localhost:38084/health`
- Mention that the backend is running on port `38084`
- Optional: open `http://localhost:38084/docs` to show Swagger

Suggested wording:

This project runs as a locally orchestrated RAG stack. The frontend is exposed on port 33004, the backend API is on 38084, and the full ingestion and retrieval flow is backed by Kafka, Elasticsearch, Milvus, MySQL, and Redis.

### 2. Show Knowledge-Base Management

- Navigate to the knowledge-base area
- Open an existing knowledge base or create one
- Briefly mention that each knowledge base has its own vector collection and configurable chunk settings

Suggested wording:

Each knowledge base has its own ingestion settings and vector storage target, which makes isolation and maintenance easier.

### 3. Upload a Document

- Upload a Markdown, PDF, or Word file
- Keep the upload visible long enough to show status movement
- Explain that the system stores the file first and then pushes a lightweight task to Kafka

Suggested wording:

After upload, the system creates a document record and publishes a lightweight ingestion task. The heavy content itself does not travel through Kafka anymore. Instead, each stage reads from storage and writes intermediate artifacts safely between steps.

### 4. Explain The Pipeline

- Point out the document status
- Mention the state flow: `uploading -> parsing -> splitting -> embedding -> completed`
- If the UI moves quickly, narrate the states even if not every transition is visible

Suggested wording:

The document goes through parsing, chunking, and embedding as separate worker stages. This makes the ingestion path more reliable and easier to retry or recover.

### 5. Show Chat And Grounded Retrieval

- Open the chat page
- Ask a question directly related to the uploaded document
- Wait for the answer and highlight the retrieved references if visible

Suggested wording:

The answer is generated from retrieved knowledge, not only from the base model. Retrieval is hybrid: Milvus provides semantic recall, Elasticsearch handles keyword and phrase recall, and the merged results are passed to the LLM as grounded context.

### 6. Close With Operations Capability

- Mention `python backend/scripts/rag_stack.py start`, `python backend/scripts/rag_stack.py status`, `python backend/scripts/rag_stack.py logs`, and `python backend/scripts/rag_stack.py restart`
- Optional: show one status or health command in the terminal

Suggested wording:

The goal of the project is not just to build a demo. It is to provide a RAG system that can be started, monitored, validated, and recovered in a local environment with repeatable scripts.

## Demo Tips

- Use a short, clean sample document with obvious headings so the audience can understand retrieval quality quickly.
- Prefer questions that test both exact terminology and semantic understanding.
- Keep the browser zoom readable and avoid switching tabs too quickly.
- If ingestion finishes too fast, narrate the pipeline states rather than waiting for the UI alone to show each one.

## Optional Terminal Commands

```bash
python backend/scripts/rag_stack.py status
python backend/scripts/rag_stack.py logs --services backend parser splitter vectorizer --tail 20
```
