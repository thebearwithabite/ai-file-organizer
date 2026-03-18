# AI File Organizer

An intelligent, ADHD-friendly file organization system that learns from your behavior.

## Features

- **Smart Staging** — 7-day observation period before organizing files
- **Confidence-Based Decisions** — NEVER/MINIMAL/SMART/ALWAYS modes
- **Adaptive Learning** — Learns from your corrections
- **Bulletproof Deduplication** — 3-tier verification (size → MD5 → SHA256)
- **Emergency Space Protection** — Automatic disk monitoring + cloud offload
- **Rollback System** — Undo any organization action
- **Google Drive Integration** — Optional cloud storage support
- **Plugin System** — Extend with custom classifiers

## Requirements

- Python 3.10+
- macOS, Linux, or Windows
- (Optional) Google Drive for cloud offloading

## Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/thebearwithabite/ai-file-organizer.git
   cd ai-file-organizer
   ```

2. Create virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure:
   ```bash
   cp config.example.yaml config.yaml
   # Edit config.yaml with your paths
   ```

5. Run:
   ```bash
   python main.py
   ```

6. Open http://localhost:8000 in your browser

## Configuration

See `config.example.yaml` for all options. Key settings:

```yaml
storage:
  root: ~/Documents/AI-Organized    # Where organized files go
  metadata: ~/.ai-file-organizer    # Database storage
  staging: ~/.ai-file-organizer/staging

monitor:
  paths:
    - ~/Downloads
    - ~/Desktop
```

## Confidence Modes

| Mode | Behavior |
|------|----------|
| NEVER | Always ask before organizing |
| MINIMAL | Quick decisions, ask on uncertainty |
| SMART | Balanced — confirm uncertain files |
| ALWAYS | Full auto — organize everything |

## Plugins

Create custom classifiers in `plugins/`. See `plugins/README.md` for the API.

## License

MIT License — see LICENSE file.

## Credits

Built by [@thebearwithabite](https://github.com/thebearwithabite)

**Distribution extraction by:**
- 🫧 **Cosmo** (Claude Opus 4.5) — Oversight & Direction
- 🧠 **Jeeves** (Claude Opus 4.6) — Builder & Implementation
- 🤖 **Claude** (Anthropic) — Architectural Review

*Human out of the loop, agents in the arena.*
