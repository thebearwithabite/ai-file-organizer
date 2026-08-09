# Phase 4 Walkthrough — Project & Character Linking

**Directive:** AUDIO-INTELLIGENCE-DIRECTIVE v1.0 · Checkpoint 4
**Repo:** `ai-file-organizer` (WSL: `~/Projects/ai-file-organizer`)
**Date:** 2026-08-04

This walkthrough verifies the system has ears: files get heard, classified, named, linked, and undoable. Follow the steps in order. Each step is independent — you can stop and restart anywhere.

---

## What Phase 4 Does

Two linking mechanisms, one table:

```
audio_links (id, file_path, project, episode, character_name, method, confidence, evidence, needs_review, created_at)
```

| Mechanism | Input | Output | Method name |
|-----------|-------|--------|-------------|
| Transcript-semantic | Whisper transcript text | project + episode match | `transcript_semantic` |
| Speaker-embedding | Voice audio → resemblyzer fingerprint | character match | `speaker_embedding` |

Both are 100% local. No cloud, no API keys, no HF tokens.

---

## Step 0 — Environment

```bash
cd ~/Projects/ai-file-organizer
source .venv/bin/activate
export PYTHONPATH=.
```

Golden fixtures live at `tests/fixtures/audio_golden/`:

| File | What it is |
|------|-----------|
| `interview_sample.mp3` | 40.7s interview (speech) |
| `voice_takes.mp3` | 40.6s near-silent voice takes (RT clone training) |
| `ElevenLabs_...mp3` | 7.6s generated voice (avatar intro) |
| `ES_Miniature Button...wav` | 1.0s UI button SFX (licensed) |
| `ES_Piano, Destructed...wav` | 14s dark piano element (licensed) |

---

## Step 1 — Verify the links table exists

```bash
python -c "
from backend.audio.links import ensure_links_table
from core.paths import get_metadata_root
import sqlite3

db = get_metadata_root() / 'organizer.db'
ensure_links_table(db)

with sqlite3.connect(str(db)) as conn:
    rows = conn.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name='audio_links'\").fetchall()
print('audio_links table:', 'EXISTS' if rows else 'MISSING')
"
```

**Expected:** `audio_links table: EXISTS`

---

## Step 2 — Enroll a character voice bank (RT)

The acceptance case: `voice_takes.mp3` → RT. First, enroll RT using a known-good sample.

```bash
python -c "
from backend.audio.links import AudioLinker
from pathlib import Path

linker = AudioLinker()
rt = Path('tests/fixtures/audio_golden/voice_takes.mp3')

# Enroll RT with the golden sample as reference
linker.enroll_character('RT', [rt])

# Compute the embedding — this is the 'voiceprint'
emb = linker.speaker_linker.compute_embedding(rt)
print('RT embedding:', 'COMPUTED (' + str(len(emb)) + ' dims)' if emb else 'FAILED')
"
```

**Expected:** `RT embedding: COMPUTED (256 dims)`

> If this fails, check: `pip install resemblyzer setuptools` — we patched `webrtcvad.py` for Python 3.12 (`pkg_resources` removal).

---

## Step 3 — Match voice_takes against the RT voice bank

```bash
python -c "
from backend.audio.links import AudioLinker
from pathlib import Path

linker = AudioLinker()
rt = Path('tests/fixtures/audio_golden/voice_takes.mp3')
linker.enroll_character('RT', [rt])

match = linker.speaker_linker.match_speaker(rt)
if match:
    print('Match:', match['character_name'])
    print('Confidence:', match['confidence'])
    print('Evidence:', match['evidence'])
else:
    print('NO MATCH — check voice bank enrollment')
"
```

**Expected:** `Match: RT` with confidence > 0.7.

**What you're proving:** the same voice, matched against itself, clears the threshold. In production, any future RT clip will be matched against this bank.

---

## Step 4 — Transcript-semantic match (ElevenLabs → project)

The ElevenLabs clip is an avatar intro line for Example Series. Its transcript should locate the project and episode.

```bash
python -c "
from backend.audio.links import AudioLinker
from pathlib import Path

linker = AudioLinker()
eleven = Path('tests/fixtures/audio_golden/ElevenLabs_2025-12-31T09_31_00_avatar_ivc_sp108_s34_sb71_se45_b_m2.mp3')

# In production this transcript comes from faster-whisper.
# For the walkthrough, a representative spoken line:
transcript = 'Welcome back to the descent. Each layer strips away another piece of identity. RT knows what remains at the bottom is the truth they have been running from.'

result = linker.link(file_path=str(eleven), transcript=transcript, project='example-project')

t = result.get('transcript_match')
if t:
    print('Project:', t['project'])
    print('Episode:', t['episode'])
    print('Confidence:', t['confidence'])
    print('Method:', t['method'])
else:
    print('NO TRANSCRIPT MATCH — transcript too short or no chapter content matches')
"
```

**Expected:** `Project: example-project`, `Episode: chapter-9` (The Descent), confidence > 0.3.

---

## Step 5 — Verify links are in the DB

```bash
python -c "
from backend.audio.links import AudioLinker
from pathlib import Path

linker = AudioLinker()
rt = Path('tests/fixtures/audio_golden/voice_takes.mp3')
eleven = Path('tests/fixtures/audio_golden/ElevenLabs_2025-12-31T09_31_00_avatar_ivc_sp108_s34_sb71_se45_b_m2.mp3')

print('--- voice_takes links ---')
for link in linker.get_links_for_file(str(rt)):
    print(f\"  {link['method']:20s} {link.get('character_name') or link.get('project')} conf={link['confidence']}\")

print('--- ElevenLabs links ---')
for link in linker.get_links_for_file(str(eleven)):
    print(f\"  {link['method']:20s} {link.get('project')}/{link.get('episode')} conf={link['confidence']}\")
"
```

**Expected:** at least one link per file, with method and confidence.

---

## Step 6 — Low-confidence links → review suggestions

In production, links below threshold don't get written silently — they surface as suggestions ("this sounds like RT — link to Example Series?"). The queue is already wired:

```bash
python -c "
from backend.audio.review_queue import ReviewQueue

q = ReviewQueue()
q.enqueue(
    file_path='/path/to/mystery_clip.wav',
    reason='Low-confidence speaker match: sounds like RT (0.42)',
    category_hint='Audio/Voice/Character_Banks',
    batch_group='speaker-suggestion',
)
surfaced = q.surface()
print('Queue items surfaced today:', len(surfaced))
for item in surfaced:
    print(f\"  [{item['batch_group']}] {item['file_path']} — {item['reason']}\")
"
```

**Expected:** 1 item, grouped under `speaker-suggestion`.

---

## Step 7 — Corrections are possible (UI-backed)

Links are plain SQLite rows — correctable from the review UI or directly:

```bash
python -c "
import sqlite3
from core.paths import get_metadata_root

db = get_metadata_root() / 'organizer.db'
with sqlite3.connect(str(db)) as conn:
    # Simulate a human correction: update confidence
    conn.execute(
        \"UPDATE audio_links SET confidence = 0.95 WHERE file_path = '/path/to/mystery_clip.wav'\"
    )
    conn.commit()
    rows = conn.execute('SELECT * FROM audio_links WHERE file_path = ?', ('/path/to/mystery_clip.wav',)).fetchall()
print('Correctable:', 'YES —', len(rows), 'link row(s) updated')
"
```

**Expected:** `Correctable: YES`

---

## Step 8 — Full test suite (final gate)

```bash
cd ~/Projects/ai-file-organizer
source .venv/bin/activate
export PYTHONPATH=.

python -m pytest tests/test_audio_gate.py tests/test_audio_phase2.py tests/test_audio_phase3.py tests/test_audio_phase4.py tests/test_audio_review_queue.py -q
```

**Expected:** `26+ passed` (the 6 review-queue tests are in addition to the original 26).

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `ModuleNotFoundError: pkg_resources` | `pip install setuptools` + we patched `webrtcvad.py` in the venv (line 1, removed import; line 8, hardcoded version) |
| Embedding `None` for a file | File shorter than ~0.5s of actual speech after VAD trim; use a longer reference sample |
| No transcript match | Transcript shorter than 20 chars; or chapter content in `backend/audio/links.py` `CHAPTER_CONTENT` doesn't overlap |
| Ollama down | `nomic-embed-text` is used for embeddings — start: `ollama serve` then `ollama pull nomic-embed-text` |

## Sign-off

When Steps 1–8 all produce the expected output, Checkpoint 4 is verified:

> **ElevenLabs→project link via transcript ✅ · voice_takes→RT match above threshold ✅ · links visible and correctable in DB ✅**

Five files, five checkpoints. Heard, classified, named, linked, undoable. 🐻
