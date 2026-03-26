# Showcase Capture Checklist

This checklist helps prepare clean screenshots, short recordings, and portfolio-ready visual material for the project.

## Before Capturing

- Ensure the stack is running and healthy.
- Confirm the frontend is reachable at `http://localhost:33004`.
- Confirm the backend is healthy at `http://localhost:38084/health`.
- Prepare one clean demo knowledge base and one representative sample document.
- Clear unrelated browser tabs, notifications, and terminal noise.
- Use a consistent browser zoom and terminal font size.

## Recommended Screenshots

- Login page or landing page after the stack is up.
- Knowledge-base list page.
- Knowledge-base detail page with uploaded documents.
- A document progressing or completed in the ingestion pipeline.
- Chat page with a grounded answer and references.
- API docs or health endpoint for technical credibility.
- Terminal view of `status-rag-stack.ps1` or `logs-rag-stack.ps1`.

## Recommended Short Recordings

- 20 to 30 seconds: stack availability and health check.
- 30 to 60 seconds: document upload and ingestion explanation.
- 30 to 60 seconds: chat answer with grounded retrieval explanation.
- 15 to 30 seconds: local operations script or status view.

## Visual Quality Checklist

- Keep the browser window clean and centered.
- Avoid exposing personal accounts, local usernames, or unrelated files.
- Use readable demo data and obvious document titles.
- Make sure terminal output is short enough to scan quickly.
- Prefer one consistent color theme across screenshots.

## Storytelling Checklist

- Explain the business problem first: private knowledge is hard to search and operationalize.
- Explain the workflow second: upload, parse, split, embed, retrieve, answer.
- Explain the technical depth third: Kafka workers, Milvus, Elasticsearch, DLQ, and local ops.
- End with the value statement: this is a deployable and operable RAG system, not just a model demo.

## Recording Checklist

- Record in 1080p if possible.
- Keep clips short and focused by topic.
- Speak in complete sentences and avoid over-explaining UI details.
- Use the same sample question across multiple takes for consistency.
- Re-record any segment with distracting loading glitches or notification popups.

## Post-Processing Checklist

- Trim dead time before and after each action.
- Add simple captions for ports, workflow stages, and hybrid retrieval if needed.
- Export one short demo clip and keep the raw clips for later editing.
- Name assets consistently, such as `showcase-login.png`, `showcase-chat-answer.png`, and `showcase-demo.mp4`.
