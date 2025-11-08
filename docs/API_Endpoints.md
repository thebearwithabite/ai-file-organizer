# 📘 API Endpoints Reference

Generated automatically from **docs/openapi.json**

**Title:** AI File Organizer API  
**Version:** 1.0.0  

| Method | Path | Summary |
|--------|------|----------|
| `GET` | `/api/veo/prompts` | List Prompts |
| `POST` | `/api/veo/prompts` | Create Prompt |
| `POST` | `/api/clip/{clip_id}/reanalyze` | Reanalyze Clip |
| `GET` | `/api/clip/{clip_id}` | Get Clip |
| `GET` | `/` | Serve Web Interface |
| `GET` | `/health` | Health Check |
| `GET` | `/api/system/status` | Get System Status |
| `POST` | `/api/system/emergency_cleanup` | Emergency Cleanup |
| `GET` | `/api/system/monitor-status` | Get Monitor Status |
| `GET` | `/api/settings/learning-stats` | Get Learning Stats |
| `GET` | `/api/settings/database-stats` | Get Database Stats |
| `GET` | `/api/settings/confidence-mode` | Get Confidence Mode |
| `POST` | `/api/settings/confidence-mode` | Set Confidence Mode |
| `GET` | `/api/system/deduplicate` | Scan For Duplicates |
| `POST` | `/api/system/deduplicate` | Perform Deduplication Cleanup |
| `GET` | `/api/system/space-protection` | Get Space Protection Status |
| `POST` | `/api/system/space-protection` | Trigger Space Cleanup |
| `GET` | `/api/search` | Search Files |
| `GET` | `/api/triage/files_to_review` | Get Files To Review |
| `POST` | `/api/triage/trigger_scan` | Trigger Triage Scan |
| `POST` | `/api/triage/scan_folder` | Scan Custom Folder |
| `POST` | `/api/triage/upload` | Upload File |
| `POST` | `/api/triage/classify` | Classify File |
| `POST` | `/api/open-file` | Open File |
| `GET` | `/api/rollback/operations` | Get Rollback Operations |
| `POST` | `/api/rollback/undo/{operation_id}` | Undo Operation |
| `POST` | `/api/rollback/undo-today` | Undo Today |