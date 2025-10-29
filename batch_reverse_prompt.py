"""
Phase 3b · Batch Reverse Prompt Processor
-----------------------------------------
Discovers and processes multiple video clips, generating VEO JSONs,
continuity data, and a project-level manifest.
"""

from __future__ import annotations
import argparse, concurrent.futures, logging, os, json, time
from pathlib import Path
from typing import List, Dict, Any

from veo_prompt_generator import VEOPromptGenerator
from continuity_analyzer import analyze_continuity
from manifest_builder import build_manifest

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")

# Initialize VEO generator globally
_veo_generator = None

def get_veo_generator() -> VEOPromptGenerator:
    """Lazy initialize VEO generator"""
    global _veo_generator
    if _veo_generator is None:
        _veo_generator = VEOPromptGenerator()
    return _veo_generator


def discover_videos(path: str, recursive: bool = True) -> List[Path]:
    """Return a list of video file paths within the given directory."""
    exts = {".mp4", ".mov", ".mkv"}
    base = Path(path).expanduser()
    if recursive:
        return [p for p in base.rglob("*") if p.suffix.lower() in exts]
    return [p for p in base.iterdir() if p.suffix.lower() in exts]


def process_video(video_path: Path) -> Dict[str, Any]:
    """Process a single video through the reverse-prompt generator."""
    try:
        generator = get_veo_generator()
        veo_json = generator.generate_reverse_veo_json(str(video_path))
        return {
            "path": str(video_path),
            "veo_json": veo_json,
            "confidence": veo_json.get("confidence_score", 0.0),
        }
    except Exception as e:
        logger.exception(f"Error processing {video_path}: {e}")
        return {"path": str(video_path), "error": str(e)}


def run_batch(input_dir: str, workers: int = 3) -> Dict[str, Any]:
    """Main entry point for batch execution."""
    start = time.time()
    videos = discover_videos(input_dir)
    logger.info(f"Discovered {len(videos)} video(s)")

    results: List[Dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        for r in ex.map(process_video, videos):
            results.append(r)

    # Compute continuity across sorted list
    continuity_data = analyze_continuity(results)

    # Build manifest
    manifest = build_manifest(results, continuity_data)
    elapsed = round(time.time() - start, 2)
    logger.info(f"Batch complete in {elapsed}s with {len(results)} clips.")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch Reverse Prompt Processor")
    parser.add_argument("input_dir", help="Folder containing videos")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--recursive", action="store_true")
    args = parser.parse_args()

    manifest = run_batch(args.input_dir, workers=args.workers)
    out_path = Path(args.input_dir) / "batch_manifest.json"
    with open(out_path, "w") as f:
        json.dump(manifest, f, indent=2)
    logger.info(f"✅ Manifest written to {out_path}")
