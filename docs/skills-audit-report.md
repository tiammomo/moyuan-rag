# Skills Audit Report

## Summary

This repository does not yet contain a true front-to-back `skills` domain model or delivery workflow.
There is no dedicated `skills` page in the frontend, no `skills` API in the backend, and no storage or installer pipeline for pulling remote skills into local state.

The audit did, however, surface two concrete interaction gaps that affected the current product experience, and both have now been fixed:

- the user menu linked to `/profile`, but the route did not exist
- the recall testing feature had backend worker code, but the `recall` worker was not wired into Docker Compose or the stack operator scripts

## What Was Audited

### Frontend

- audited `front/src/app` routes for `skills` pages and entry points
- audited layout and navigation for visible buttons that could be dead links or partially wired actions
- cross-checked current pages against available API clients

### Backend

- audited `backend/app/api/v1` for `skills` routes
- audited services, workers, and storage helpers for any `skills` implementation
- checked whether there was already a remote-download capability that could fetch skills from external sources

## Findings

### 1. No current `skills` workflow exists

The current project focuses on RAG ingestion, retrieval, recall evaluation, and chat. There is no existing `skills` entity in the product.

That means the following are currently absent:

- `skills` list or detail pages
- `skills` CRUD APIs
- `skills` persistence schema
- remote `skills` sync or download jobs
- install/update/remove lifecycle for local skills

### 2. Remote skills should not be bolted directly onto the current RAG app by default

The audit conclusion is that remote skill download should be treated as a separate installer or controlled sync workflow, not as an implicit runtime side effect inside the current RAG request path.

Recommended boundary:

- keep the RAG app focused on knowledge, chat, retrieval, and evaluation
- if `skills` become a real feature, add a dedicated backend service boundary and explicit install flow
- if remote pull is needed, require allowlists, source validation, checksum tracking, and a writable install directory policy

### 3. Interaction completeness issues found during the audit

These issues were found and resolved during the audit:

- `/profile` now has a real page and no longer dead-ends from the avatar menu
- `recall` is now part of Compose and the local operator scripts, so the recall test page has an actual managed worker behind it
- the top navigation and profile menu text were cleaned up to remove user-visible mojibake in the most visible shared layout

## Changes Completed During This Audit

- added `front/src/app/profile/page.tsx`
- wired `recall` into `backend/docker-compose.yaml`
- updated `start-rag-stack.ps1`, `restart-rag-stack.ps1`, and `logs-rag-stack.ps1` to include `recall`
- updated `README.md`, `docs/README.md`, and `docs/full-stack-compose.md`
- normalized visible text in the shared frontend layout used by authenticated pages

## Validation

The audit fixes should be validated with:

- `docker compose -f .\backend\docker-compose.yaml config`
- `npm run type-check`
- Compose start or targeted `recall` service bring-up
- frontend route check for `/profile`
- recall API or worker log verification

## Recommended Next Step

The bootstrap slice is now in place. Continue with:

- [skills-bootstrap-slice.md](./skills-bootstrap-slice.md)
- [skills-runtime-integration-plan.md](./skills-runtime-integration-plan.md)
