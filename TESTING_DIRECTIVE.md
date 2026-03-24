# Antigravity AI File Organizer — Full System Test Directive
**For:** Browser-based testing agent (Claude in Chrome or equivalent)
**Server:** http://localhost:8000
**UI:** http://localhost:8000 (React SPA, served from frontend_v2/dist/)
**Do not simulate results. Do not assume success. Verify every claim by checking the actual response.**

---

## RULES OF ENGAGEMENT

1. Every test must produce a PASS, FAIL, or BROKEN verdict with the exact error or response observed.
2. If a UI widget does not render, say so exactly — do not skip it.
3. If an API returns a non-200, record the status code and body.
4. Do not move on from a FAIL without logging it. Do not fix anything — just report.
5. You are building a ground-truth snapshot of what works and what doesn't. Ryan will use this to prioritize fixes.

---

## PHASE 1 — SERVER & API HEALTH

Test each endpoint directly via fetch() or curl. Record status code and whether the response shape makes sense.

| Endpoint | Method | Expected | Verdict |
|---|---|---|---|
| /health | GET | 200 + some JSON | |
| /api/system/status | GET | 200 + monitor running state | |
| /api/system/monitor-status | GET | 200 + background monitor details | |
| /api/taxonomy/ | GET | 200 + list of categories | |
| /api/triage/files_to_review | GET | 200 + list of files | |
| /api/triage/projects | GET | 200 + project list | |
| /api/settings/confidence-mode | GET | 200 + current mode | |
| /api/settings/database-stats | GET | 200 + stats object | |
| /api/settings/learning-stats | GET | 200 + learning data | |
| /api/system/space-protection | GET | 200 + protection status | |
| /api/rollback/operations | GET | 200 + list of operations | |
| /api/recent-activity | GET | 200 + activity list | |
| /api/search?q=test | GET | 200 + results array | |
| /api/identities/ | GET | 200 + identity list | |
| /api/identities/stats/summary | GET | 200 + summary object | |
| /api/veo/prompts | GET | 200 + prompts | |
| /api/veo-studio/projects | GET | 200 + projects | |

---

## PHASE 2 — UI NAVIGATION (Open http://localhost:8000 in browser)

Navigate to each section. For each one record:
- Does it load without a white screen or JS error?
- Are the main widgets/tables/cards visible and populated, or empty?
- Are there any console errors? (Check DevTools)

### Pages to test:
1. **Dashboard** (/) — Does it show system status, recent activity, confidence mode?
2. **Triage** (/triage) — Does it show files to review? Can you click approve/reject on one?
3. **Organize** (/organize) — Does it load? Any scan controls visible?
4. **Duplicates** (/duplicates) — Does it show duplicate groups or empty state?
5. **Search** (/search) — Does the search bar work? Type "pdf" and observe results.
6. **Rollback Center** (/rollback) — Does it list operations? Is undo button present?
7. **Settings** (/settings) — Does confidence mode selector work? Can you toggle it?
8. **Analysis** (/analysis) — Does it load charts or show empty state?
9. **Veo Studio** (/veo-studio) — Does it load? (Expected: may not be functional yet)
10. **Forensic Vault** — Does it appear in nav? Does it load?

---

## PHASE 3 — TRIAGE FLOW (Core Feature)

This is the most important test. The system should be classifying files and presenting them for review.

1. Call `POST /api/triage/trigger_scan` — does it return 200 and start a scan?
2. Call `GET /api/triage/files_to_review` — are there files waiting?
3. In the UI, go to Triage page — do the files appear as cards?
4. Click approve on one file — does the UI respond? Does the file disappear from the queue?
5. Call `POST /api/triage/classify` with a test payload — does it return a classification?
6. Check that the taxonomy categories shown in Triage match what `/api/taxonomy/` returns. **This is a known bug — hardcoded vs live categories. Document exactly what you see.**

---

## PHASE 4 — ADAPTIVE LEARNING VERIFICATION

The system should be learning from user actions. This has been broken (events recorded as wrong type).

1. Call `GET /api/settings/learning-stats` — how many observations are recorded? What types?
2. Call `GET /api/settings/database-stats` — is adaptive_learning.db showing rows?
3. After approving a file in Triage (Phase 3), re-call learning-stats — did the count increase?
4. Check if any rules have been promoted (look for non-seed rules in the response).
5. Verdict: is the learning pipeline alive or dead?

---

## PHASE 5 — CONFIDENCE SYSTEM

1. `GET /api/settings/confidence-mode` — what mode is it in?
2. In Settings UI, toggle the confidence mode — does the API reflect the change?
3. `GET /api/system/status` — does confidence mode appear in system status?
4. Check that the monitor is NOT in emergency mode (this was being falsely triggered by the APFS disk space bug — fixed tonight, verify it's clear).

---

## PHASE 6 — ROLLBACK SAFETY NET

1. `GET /api/rollback/operations` — are past operations listed?
2. In Rollback Center UI — does the list render?
3. Is the undo button present per operation?
4. Do NOT execute an undo — just verify the controls exist and the data is there.

---

## PHASE 7 — SETTINGS & TAXONOMY

1. `GET /api/taxonomy/` — how many categories are returned? List the top 10.
2. In Settings UI — does the taxonomy section show the live list or is it empty?
3. Compare to what Triage shows — **are they the same categories?** This is the known bug.
4. `GET /api/settings/database-stats` — record all values shown.

---

## DELIVERABLE

At the end, produce a single report in this format:

```
SYSTEM STATUS: [HEALTHY / DEGRADED / BROKEN]

WORKING:
- List every feature confirmed working

BROKEN:
- List every feature that failed, with exact error

EMPTY (not broken, just no data yet):
- List features that load but have nothing to show

CRITICAL BUGS CONFIRMED:
- Triage categories: hardcoded vs live? [YES/NO]
- Learning pipeline: alive? [YES/NO]  
- Confidence mode: stable? [YES/NO]
- Emergency trigger: clear? [YES/NO]

RECOMMENDED FIX ORDER:
1.
2.
3.
```

Do not editorialize. Do not speculate. Only report what you directly observed.
