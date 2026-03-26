# Compose Troubleshooting

This guide covers the standard local troubleshooting flow for the compose-managed RAG stack.

## 1. Check Stack State

Use the status helper first:

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\scripts\status-rag-stack.ps1
```

Use JSON output when you want to inspect the service state programmatically:

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\scripts\status-rag-stack.ps1 -Json
```

What to look for:

- `RunningServices` lower than `TotalServices`
- `backend`, `front`, or `kafka` not marked healthy
- an endpoint warning such as:
  - `Endpoint reachable while compose service 'backend' is not running.`

That warning usually means a host-side process is already bound to the same port and is masking the real compose state.

## 2. Read Logs

The log helper defaults to the main app services:

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\scripts\logs-rag-stack.ps1 -Tail 100
```

Follow logs continuously:

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\scripts\logs-rag-stack.ps1 -Follow
```

Limit to specific services:

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\scripts\logs-rag-stack.ps1 -Services backend,front -Tail 200
```

## 3. Restart Only What You Need

Restart one or more services:

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\scripts\restart-rag-stack.ps1 -Services backend
```

Restart a service and the app-layer dependents that rely on it:

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\scripts\restart-rag-stack.ps1 -Services backend -IncludeDependents
```

Examples:

- restart the frontend only:
  - `powershell -ExecutionPolicy Bypass -File .\backend\scripts\restart-rag-stack.ps1 -Services front`
- restart Kafka and the services that depend on it:
  - `powershell -ExecutionPolicy Bypass -File .\backend\scripts\restart-rag-stack.ps1 -Services kafka -IncludeDependents`

The restart helper waits for compose readiness and also verifies HTTP health for `backend` and `front`.

## 4. Recover the Whole Stack

If multiple services are down or the environment is inconsistent, stop then restart the stack:

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\scripts\stop-rag-stack.ps1
powershell -ExecutionPolicy Bypass -File .\backend\scripts\start-rag-stack.ps1
```

If you need to recreate containers:

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\scripts\stop-rag-stack.ps1 -RemoveContainers
powershell -ExecutionPolicy Bypass -File .\backend\scripts\start-rag-stack.ps1 -Build
```

## 5. Validate Recovery

After recovery:

1. Re-run `status-rag-stack.ps1`.
2. Confirm `backend`, `front`, and `kafka` show healthy.
3. If the issue touched the document pipeline, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\scripts\local-integration.ps1
```

## 6. Notes

- The compose lifecycle scripts manage containers only. They do not kill unrelated host-side Python or Node processes.
- Shared `rag-*` named volumes are external and are preserved by the stop/restart helpers.
