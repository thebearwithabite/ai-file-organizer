---
title: "Sprint 3.4 — API Completion & Integration Testing"
date: 2025-11-05
status: Planned
phase: 3.4
owner: user
---

# ⚙️ Sprint 3.4 — API Completion & Integration Testing

**Objective:**
Finalize and verify all backend endpoints powering the new UI (Sprint 3.3) and guarantee production-ready stability through automated tests and deployment prep.

---

## 🧠 Context Summary
- Backend v3.2: All services implemented and documented
- Frontend v3.3: Six UI modules operational
- Remaining: endpoint validation, integration tests, and deployment packaging

---

## 🔧 Backend Tasks

### Task 1 — Finalize Endpoints
| Endpoint | Action | Requirement |
|-----------|---------|-------------|
| `/api/rollback/list` | GET | Return recent ops (≤ 30 days) |
| `/api/rollback/undo/<id>` | POST | Restore file → log entry |
| `/api/system/monitor-status` | GET | Return active paths + last event |
| `/api/system/space-protection` | POST | Trigger cleanup + report freed space |
| `/api/system/deduplicate` | POST | Perform safe cleanup with rollback |
| `/api/settings/confidence-mode` | GET/POST | Return & update mode |

**Acceptance:** All routes return `{status,message,data}` and HTTP 200 on success.

---

### Task 2 — Integration Test Suite
**Tools:** `pytest + httpx`, optional Playwright for UI.

Tests:
- Learning stats increment after triage
- Rollback undo restores file
- Disk usage drops after protect()
- Duplicates cleanup removes copies
- Confidence mode switch persists
- Monitor status active within 5 s of startup

---

### Task 3 — API Docs Generation
Use FastAPI OpenAPI export:

```bash
uvicorn main:app --reload &
curl http://localhost:8000/openapi.json > docs/openapi.json
python scripts/generate_api_docs.py
```

Output → `docs/API_Endpoints.md`.

---

### Task 4 — Deployment Prep
- Add `Dockerfile` for backend + frontend
- Add `docker-compose.yml` for full stack
- Update `.env.example` (clean of any tokens)
- Create `init.sh` to bootstrap DBs and run safety checks
- Implement PII/secret scanner pre-push hook
  (`.git/hooks/pre-push` → `detect-secrets scan`)

---

### Task 5 — Regression & Performance Testing
- Run Playwright tests on critical flows
- Simulate 1000 file classifications for stability
- Ensure API latency < 150 ms median
- All tests pass → tag `v3.4.0-rc1`

---

## 🧩 Acceptance Matrix
| # | Feature | Validation | Result |
|---|---------|------------|--------|
| 1 | All API routes respond | curl/httpx | ✅ 200 OK + structured JSON |
| 2 | Integration tests | pytest suite | ✅ All pass |
| 3 | Docs generated | docs/API_Endpoints.md exists | ✅ |
| 4 | Docker stack builds | docker-compose up | ✅ |
| 5 | Pre-push PII scan | hook blocks unsafe commits | ✅ |

---

## 🔗 References
- [`docs/Sprint_3.3_Directive.md`](./Sprint_3.3_Directive.md)
- [`docs/Adaptive_Monitor_Spec.md`](./Adaptive_Monitor_Spec.md)
- `tests/test_api_endpoints.py`
- `docker-compose.yml`

---

## 🧱 Commit Log (placeholder)
| Commit | Message | Status |
|---------|----------|--------|
| ( ) | `feat: Sprint 3.4 Task 1 — Finalize Endpoints` | ⬜ |
| ( ) | `test: Sprint 3.4 Task 2 — Integration Suite` | ⬜ |
| ( ) | `docs: Generate API Docs and OpenAPI Spec` | ⬜ |
| ( ) | `build: Add Docker and Pre-Push PII Scanner` | ⬜ |
| ( ) | `perf: Load Test and v3.4.0-rc1 tag` | ⬜ |

---

## 🏁 Next Steps
1. Add this directive → `docs/Sprint_3.4_Directive.md`
2. Run PII/secret sweeps before any remote push
3. Branch `feature/sprint-3-4-api-testing`
4. Implement Tasks 1–5 → Tag `v3.4.0-rc1` on completion
5. Push only after clean PII scan ✅

---

*Drafted by Max — Verified by user — Focus: Security & Reliability Alignment.*
