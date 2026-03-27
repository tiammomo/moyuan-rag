# Compose Troubleshooting

This guide covers the standard local troubleshooting flow for the compose-managed RAG stack.

## 1. Check Stack State

Use the status helper first:

```bash
python backend/scripts/rag_stack.py status
```

Use JSON output when you want to inspect the service state programmatically:

```bash
python backend/scripts/rag_stack.py status --json
```

What to look for:

- `RunningServices` lower than `TotalServices`
- `backend`, `front`, or `kafka` not marked healthy
- an endpoint warning such as:
  - `Endpoint reachable while compose service 'backend' is not running.`

That warning usually means a host-side process is already bound to the same port and is masking the real compose state.

## 2. Read Logs

The log helper defaults to the main app services:

```bash
python backend/scripts/rag_stack.py logs --tail 100
```

Follow logs continuously:

```bash
python backend/scripts/rag_stack.py logs --follow
```

Limit to specific services:

```bash
python backend/scripts/rag_stack.py logs --services backend front --tail 200
```

## 3. Restart Only What You Need

Restart one or more services:

```bash
python backend/scripts/rag_stack.py restart backend
```

Restart a service and the app-layer dependents that rely on it:

```bash
python backend/scripts/rag_stack.py restart backend --include-dependents
```

Examples:

- restart the frontend only:
  - `python backend/scripts/rag_stack.py restart front`
- restart Kafka and the services that depend on it:
  - `python backend/scripts/rag_stack.py restart kafka --include-dependents`

The restart helper waits for compose readiness and also verifies HTTP health for `backend` and `front`.

## 4. Recover the Whole Stack

If multiple services are down or the environment is inconsistent, stop then restart the stack:

```bash
python backend/scripts/rag_stack.py stop
python backend/scripts/rag_stack.py start
```

If you need to recreate containers:

```bash
python backend/scripts/rag_stack.py stop --remove-containers
python backend/scripts/rag_stack.py start --build
```

## 5. Validate Recovery

After recovery:

1. Re-run `python backend/scripts/rag_stack.py status`.
2. Confirm `backend`, `front`, and `kafka` show healthy.
3. If the issue touched the document pipeline, run:

```bash
python backend/scripts/local_integration.py
```

## 6. Notes

- The compose lifecycle scripts manage containers only. They do not kill unrelated host-side Python or Node processes.
- Shared `rag-*` named volumes are external and are preserved by the stop/restart helpers.
