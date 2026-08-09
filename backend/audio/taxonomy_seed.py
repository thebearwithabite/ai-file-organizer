"""
Phase 2.1 — Seed the audio taxonomy into the knowledge table.

Inserts the Audio/ tree from AUDIO-INTELLIGENCE-DIRECTIVE.
Categories are hierarchical: "Audio/Voice/Recorded" etc.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from core.paths import get_metadata_root

TAXONOMY = {
    "Audio/Voice/Recorded": {
        "display_name": "Recorded Voice",
        "description": "Live-recorded human speech: interviews, memos, meetings, field voiceover. Natural room tone, breathing, pauses.",
        "keywords": ["interview", "memo", "meeting", "field recording", "voice note", "dictation", "lecture", "podcast"],
        "examples": ["interview_john_2024.mp3", "meeting_notes_march.wav", "field_vo_take3.wav"],
        "naming_rules": "Type code: VOXR. Keep original descriptor words.",
    },
    "Audio/Voice/Generated": {
        "display_name": "Generated Voice",
        "description": "AI-generated speech: TTS, ElevenLabs, clone outputs. Artifacts: uniform pacing, clean background, no breath noise.",
        "keywords": ["tts", "elevenlabs", "generated", "synthetic", "clone", "ai voice", "text to speech"],
        "examples": ["ElevenLabs_avatar_intro.mp3", "tts_narration_ch3.wav"],
        "naming_rules": "Type code: VOXG. Always provenance=generated.",
    },
    "Audio/Voice/Character_Banks": {
        "display_name": "Character Voice Banks",
        "description": "Per-character voice samples for cloning or reference: protagonist, narrator, supporting cast. May be near-silent takes.",
        "keywords": ["character", "voice bank", "clone training", "protagonist", "narrator", "voice sample", "reference"],
        "examples": ["voice_takes.mp3", "narrator_samples.wav"],
        "naming_rules": "Type code: VOXC. Include character name in filename.",
    },
    "Audio/Voice/Production_VO": {
        "display_name": "Production Voiceover",
        "description": "Clean studio voiceover, raw dialogue takes, ADR lines. Professional recording environment.",
        "keywords": ["voiceover", "vo", "dialogue", "adr", "narration", "studio", "clean"],
        "examples": ["ch3_vo_final.wav", "dialogue_scene4_take2.wav"],
        "naming_rules": "Type code: VOXR or VOXC depending on context.",
    },
    "Audio/Music/Tracks": {
        "display_name": "Music Tracks",
        "description": "Full songs or complete musical pieces. Sub-categorized by mood: contemplative, dark, tension, wonder.",
        "keywords": ["song", "track", "full", "composition", "complete", "album"],
        "examples": ["dark_ambient_track.wav", "wonder_theme_full.mp3"],
        "naming_rules": "Type code: MUS. Include BPM and mood qualifier.",
    },
    "Audio/Music/Stems_Loops": {
        "display_name": "Stems & Loops",
        "description": "Isolated instrument tracks or loopable segments: drums, bass, melodic, vocal chops.",
        "keywords": ["stem", "loop", "drum", "bass", "melodic", "vocal chop", "isolated", "layer"],
        "examples": ["drums_loop_120bpm.wav", "bass_stem_verse.wav"],
        "naming_rules": "Type code: STEM. Include BPM.",
    },
    "Audio/Music/Elements": {
        "display_name": "Music Elements",
        "description": "One-shots, hits, motifs, stingers — the dark-piano class. Short, impactful, not full tracks.",
        "keywords": ["one-shot", "hit", "motif", "stinger", "element", "piano", "dark", "atonal"],
        "examples": ["ES_Piano_Destructed_Dark_Keys.wav"],
        "naming_rules": "Type code: ELEM. Include centroid-derived darkness tag if applicable.",
    },
    "Audio/SFX/UI_Digital": {
        "display_name": "UI & Digital SFX",
        "description": "Interface sounds: buttons, clicks, glitches, notifications, transitions. Typically <3s.",
        "keywords": ["button", "click", "glitch", "ui", "interface", "notification", "digital", "beep"],
        "examples": ["ES_Miniature_Button.wav"],
        "naming_rules": "Type code: SFX. NEVER auto-file sub-3s. Licensed files NEVER renamed.",
    },
    "Audio/SFX/Human_Foley": {
        "display_name": "Human Foley",
        "description": "Body sounds: footsteps, reactions, breath, cloth movement.",
        "keywords": ["foley", "footstep", "breath", "cloth", "body", "reaction", "movement"],
        "examples": ["footsteps_concrete.wav", "breath_exertion.wav"],
        "naming_rules": "Type code: SFX.",
    },
    "Audio/SFX/Environment": {
        "display_name": "Environment SFX",
        "description": "Ambient environmental sounds: weather, rooms, nature, city, crowd walla.",
        "keywords": ["ambient", "environment", "weather", "rain", "wind", "room tone", "nature", "city", "crowd"],
        "examples": ["rain_gentle.wav", "city_traffic_distant.wav"],
        "naming_rules": "Type code: AMB or SFX.",
    },
    "Audio/SFX/Design": {
        "display_name": "Sound Design",
        "description": "Designed effects: risers, impacts, drones, ambience beds, whooshes, braams.",
        "keywords": ["riser", "impact", "drone", "whoosh", "braam", "design", "cinematic", "transition"],
        "examples": ["riser_tension_8bar.wav", "impact_cinematic_heavy.wav"],
        "naming_rules": "Type code: SFX.",
    },
    "Audio/Field_Raw": {
        "display_name": "Field Raw",
        "description": "Unprocessed field recordings, staging area. Needs human review before classification.",
        "keywords": ["field", "raw", "unprocessed", "recording", "staging", "unclassified"],
        "examples": ["recording_20240101_001.wav"],
        "naming_rules": "Type code: FLD. Always needs review.",
    },
}

LICENSE_PREFIXES = [
    "ES_",           # Epidemic Sound
    "Artlist_",      # Artlist
    "Musicbed_",     # Musicbed
    "Soundstripe_",  # Soundstripe
    "Pond5_",        # Pond5
]

GENERATED_PREFIXES = [
    "ElevenLabs_",
    "tts_",
    "clone_",
    "generated_",
    "synthetic_",
]


def seed_taxonomy(db_path: Path | None = None) -> int:
    """Insert audio taxonomy into knowledge table. Returns count of entries."""
    if db_path is None:
        db_path = get_metadata_root() / "organizer.db"
    
    with sqlite3.connect(str(db_path)) as conn:
        # Clear existing audio entries
        conn.execute("DELETE FROM knowledge WHERE category_id LIKE 'Audio/%'")
        
        count = 0
        for category_id, data in TAXONOMY.items():
            conn.execute(
                """INSERT INTO knowledge 
                   (category_id, display_name, description, keywords, examples, naming_rules)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    category_id,
                    data["display_name"],
                    data["description"],
                    json.dumps(data["keywords"]),
                    json.dumps(data["examples"]),
                    data.get("naming_rules", ""),
                ),
            )
            count += 1
        
        conn.commit()
    
    return count


def detect_license_prefix(filename: str) -> str | None:
    """Detect if a filename matches a known license prefix."""
    for prefix in LICENSE_PREFIXES:
        if filename.startswith(prefix):
            return prefix.rstrip("_").lower()
    return None


def detect_generated_prefix(filename: str) -> bool:
    """Detect if a filename indicates generated content."""
    return any(filename.startswith(p) for p in GENERATED_PREFIXES)


if __name__ == "__main__":
    count = seed_taxonomy()
    print(f"Seeded {count} audio taxonomy entries")
