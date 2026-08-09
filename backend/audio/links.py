"""
Phase 4 — Project & Character Linking.

Two mechanisms:
  1. Transcript-semantic: Whisper transcript -> nomic-embed-text -> vector search
  2. Speaker-embedding: resemblyzer voiceprint -> match against enrolled banks

One table: audio_links (file_id, project, episode, character, method, confidence)
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Audio Links table
# ---------------------------------------------------------------------------

def ensure_links_table(db_path: Path) -> None:
    """Create audio_links table if it doesn't exist."""
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audio_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                project TEXT,
                episode TEXT,
                character_name TEXT,
                method TEXT NOT NULL,       -- transcript_semantic | speaker_embedding
                confidence REAL,
                evidence TEXT,               -- matching transcript snippet or similarity score
                needs_review BOOLEAN DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                UNIQUE(file_path, method)
            )
        """)
        conn.commit()


# ---------------------------------------------------------------------------
# Chapter/project content for semantic matching
# ---------------------------------------------------------------------------

# Seed project content — expand with actual show episodes
CHAPTER_CONTENT = {
    "example-project": {
        "chapters": {
            "chapter-6": "The team discovers the anomaly. Reality begins to fragment. The protagonist confronts the architect about the nature of their world.",
            "chapter-7": "The architect reveals the truth. The loop is a simulation. The protagonist must choose between staying in the illusion or breaking free.",
            "chapter-8": "Breaking the loop. The team splinters. Some choose to stay, others fight to escape. The cost of freedom becomes clear.",
            "chapter-9": "The descent. The protagonist enters the deep layers of the simulation. Each level strips away another piece of identity. What remains at the bottom.",
        },
        "characters": {
            "protagonist": "Measured, calm delivery. Questions everything. Voice carries weight of experience.",
            "narrator": "Omniscient voice. Clean, authoritative. Guides the audience through the descent.",
        },
    },
}


# ---------------------------------------------------------------------------
# Mechanism 1: Transcript-semantic match
# ---------------------------------------------------------------------------

class TranscriptLinker:
    """
    Match a Whisper transcript against known chapter content
    to identify which project/episode a voice clip belongs to.
    """

    def __init__(self):
        self._embed_fn = None

    def embed(self, text: str) -> list[float]:
        """Embed text using nomic-embed-text via Ollama."""
        if self._embed_fn is None:
            # Lazy init — wrap Ollama embed API
            import requests

            def _embed(t: str) -> list[float]:
                try:
                    resp = requests.post(
                        "http://localhost:11434/api/embed",
                        json={"model": "nomic-embed-text", "input": t},
                        timeout=10,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        if "embeddings" in data:
                            return data["embeddings"][0]
                except Exception:
                    pass
                return [0.0] * 768  # fallback

            self._embed_fn = _embed

        return self._embed_fn(text)

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def match_transcript(
        self,
        transcript: str,
        project: str = "example-project",
        min_confidence: float = 0.3,
    ) -> Optional[dict]:
        """
        Match a transcript against known chapters.
        Returns: {project, episode, confidence, method, evidence}
        """
        if not transcript or len(transcript) < 20:
            return None

        emb_transcript = self.embed(transcript[:500])  # first 500 chars

        best_match = None
        best_score = 0.0

        chapters = CHAPTER_CONTENT.get(project, {}).get("chapters", {})
        for episode, content in chapters.items():
            emb_chapter = self.embed(content)
            score = self._cosine_similarity(emb_transcript, emb_chapter)
            if score > best_score:
                best_score = score
                best_match = {
                    "project": project,
                    "episode": episode,
                    "confidence": round(score, 3),
                    "method": "transcript_semantic",
                    "evidence": content[:100],
                }

        if best_match and best_match["confidence"] >= min_confidence:
            return best_match
        return None


# ---------------------------------------------------------------------------
# Mechanism 2: Speaker-embedding match
# ---------------------------------------------------------------------------

class SpeakerLinker:
    """
    Match a voice clip against enrolled character voice banks
    using resemblyzer speaker embeddings.
    """

    def __init__(self):
        self._encoder = None
        self._voice_banks: dict[str, list[Path]] = {}  # character -> reference files

    def _get_encoder(self):
        """Lazy load resemblyzer encoder."""
        if self._encoder is None:
            from resemblyzer import VoiceEncoder
            self._encoder = VoiceEncoder()
        return self._encoder

    def enroll_character(self, name: str, reference_files: list[Path]) -> None:
        """Enroll a character with reference voice samples."""
        self._voice_banks[name] = reference_files

    def compute_embedding(self, audio_path: Path) -> Optional[list[float]]:
        """Compute speaker embedding for a single audio file."""
        from resemblyzer import preprocess_wav
        import numpy as np

        try:
            wav = preprocess_wav(audio_path)
            if wav is None or len(wav) < 8000:  # less than 0.5s at 16kHz
                return None
            encoder = self._get_encoder()
            emb = encoder.embed_utterance(wav)
            return emb.tolist()
        except Exception as e:
            logger.warning(f"Speaker embedding failed for {audio_path}: {e}")
            return None

    def match_speaker(self, audio_path: Path, min_confidence: float = 0.5) -> Optional[dict]:
        """
        Match a voice clip against enrolled character banks.
        Returns: {character_name, confidence, method, evidence}
        """
        import numpy as np

        emb = self.compute_embedding(audio_path)
        if emb is None:
            return None

        best_match = None
        best_score = 0.0

        for character, ref_files in self._voice_banks.items():
            scores = []
            for ref_file in ref_files:
                ref_emb = self.compute_embedding(ref_file)
                if ref_emb:
                    score = np.dot(emb, ref_emb) / (
                        np.linalg.norm(emb) * np.linalg.norm(ref_emb)
                    )
                    scores.append(score)

            if scores:
                avg_score = float(np.mean(scores))
                if avg_score > best_score:
                    best_score = avg_score
                    best_match = {
                        "character_name": character,
                        "confidence": round(best_score, 3),
                        "method": "speaker_embedding",
                        "evidence": f"Similarity: {best_score:.3f} against {len(ref_files)} reference(s)",
                    }

        if best_match and best_match["confidence"] >= min_confidence:
            return best_match
        return None


# ---------------------------------------------------------------------------
# Unified linker
# ---------------------------------------------------------------------------

class AudioLinker:
    """
    Run both matching mechanisms and write results to audio_links table.
    """

    def __init__(self, db_path: Optional[Path] = None):
        from core.paths import get_metadata_root
        self.db_path = db_path or (get_metadata_root() / "organizer.db")
        self.transcript_linker = TranscriptLinker()
        self.speaker_linker = SpeakerLinker()
        ensure_links_table(self.db_path)

    def enroll_character(self, name: str, reference_files: list[Path]) -> None:
        self.speaker_linker.enroll_character(name, reference_files)

    def link(
        self,
        file_path: str,
        transcript: Optional[str] = None,
        project: str = "example-project",
    ) -> dict:
        """
        Run both match mechanisms and write to DB.
        Returns combined links dict.
        """
        path = Path(file_path)
        results = {"transcript_match": None, "speaker_match": None}

        # Transcript-semantic
        if transcript and len(transcript) > 20:
            t_match = self.transcript_linker.match_transcript(transcript, project)
            if t_match:
                self._write_link(file_path, t_match)
                results["transcript_match"] = t_match

        # Speaker embedding
        s_match = self.speaker_linker.match_speaker(path)
        if s_match:
            self._write_link(file_path, s_match)
            results["speaker_match"] = s_match

        return results

    def _write_link(self, file_path: str, match: dict) -> None:
        """Write a link result to the DB."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO audio_links
                (file_path, project, episode, character_name, method, confidence, evidence)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                file_path,
                match.get("project"),
                match.get("episode"),
                match.get("character_name"),
                match.get("method"),
                match.get("confidence", 0.0),
                match.get("evidence", ""),
            ))
            conn.commit()

    def get_links_for_file(self, file_path: str) -> list[dict]:
        """Get all links for a file."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM audio_links WHERE file_path = ?",
                (file_path,),
            ).fetchall()
            return [dict(r) for r in rows]
