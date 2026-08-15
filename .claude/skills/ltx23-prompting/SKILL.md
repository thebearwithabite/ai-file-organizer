---
name: ltx23-prompting
description: Write LTX 2.3 video generation prompts the way the Prompt Machine compiler does — single flowing paragraph, fixed element order, physical cues not emotion labels, quoted dialogue, token guard. Use when authoring or reviewing LTX prompts (shots, keyframes, QA).
---

# LTX 2.3 Prompting (emitter rules as a writing guide)

> **Authority:** the Hermes skill store (`ltx-prompting`) is the living source and its newest edits TRUMP this file. These rules are also seeded as `LTX23_PROMPT_GUIDE` in the knowledge table and enforced by `prompt_compiler.emit_ltx_prompt()`.

## The fixed order (all six elements)

1. **Establish the shot** — framing, subject, location. Cinematography terms matching genre (shot scale, category-specific characteristics).
2. **Set the scene** — lighting, color palette, surface textures, atmosphere, mood. ONE coherent lighting key.
3. **Describe the action** — natural sequence, clear flow beginning to end. **Present tense.**
4. **Define the character(s)** — age, hairstyle, clothing, distinguishing features. Emotion through **physical cues**, never labels.
5. **Camera movement** — how and when it moves; describe how the subject appears **after** the movement completes.
6. **Describe the audio** — ambient, music, speech. Spoken dialogue in **quotation marks**. Language/accent if needed.

## Format

- **Single flowing prose paragraph.**
- **Present tense** verbs.
- **4–8 descriptive sentences** (match detail to shot scale — close-ups carry more detail).
- Describe camera movement relative to the subject.
- Iterate freely — LTX is designed for fast experimentation.

## Never emit

| Avoid | Why |
|---|---|
| Readable text or logos in frame | Not reliable in LTX |
| Emotion labels ("sad", "confused", "angry") | Render the physical evidence instead |
| Conflicting lighting ("soft window light" + "harsh neon glare") | Confuses interpretation |
| Overloaded multi-action scenes | One action per shot; more shots if needed |
| Complex physics / chaotic motion | Artifacts |
| Overcomplicated prompts | Start simple, layer gradually |

## Token guard (compiler-enforced)

Estimate tokens BEFORE emitting; enforce the per-engine max (stored in `knowledge`). Over the limit → run an LLM compression pass that preserves the ordered structure → re-validate. **Never silently truncate.**

## Good example (THE LETTER, sc01_sh02)

> A medium close-up of a woman in her mid-thirties with dark hair in a grey knit sweater, standing at a kitchen counter in the morning. Soft window light from the left across her face, the room quiet and still. She sets down a coffee pot, then notices an unopened cream envelope on the counter and stops mid-movement. Her eyebrows draw together, her hand pauses above the envelope, fingers hesitating an inch away. The camera slowly pushes in as she picks it up with both hands. Faint street traffic outside, refrigerator hum, the soft rustle of paper.

Why it works: establishes framing → lighting → action → character physical cues (no emotion words) → camera movement (subject described after) → audio. 6 sentences.

## Bad example (same beat, broken)

> A sad woman is upset about a mysterious letter that has arrived. She feels confused and worried as she looks at the envelope in the brightly lit kitchen with neon lights. The camera does a cool dramatic zoom while she is emotional and thinking about her dad, and there are texts and logos everywhere in the background, with intense music playing loudly. She is scared and it is very dramatic and exciting.

Why it fails: emotion labels (sad, upset, confused, worried, scared, emotional), conflicting lighting (bright + neon), no physical cues, camera movement described before the subject, readable text in frame, overloaded action, no quoted dialogue, tense inconsistent.
