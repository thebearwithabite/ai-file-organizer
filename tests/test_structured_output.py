"""Structured-output enforcement tests (ShotSpec contract + one repair retry).

Covers the three mandated cases and the surrounding guarantees:

* valid output returns on the first attempt, with no repair call;
* an invalid first response is repaired exactly once and succeeds, on the SAME
  client, with the original prompt data preserved;
* two invalid responses raise the typed ``InvalidLLMOutputError`` carrying an
  actionable validation summary and the retry count — and never a route change.

Plus the mechanics the contract depends on: JSON fence tolerance, per-shot error
paths in the repair prompt, transport errors propagating untouched, and the
reusable callable form.
"""
from __future__ import annotations

import json
import logging

import pytest

from backend.llm.base import LLMProvider
from backend.llm.errors import InvalidLLMOutputError
from backend.llm.structured_output import (
    MAX_REPAIRS,
    build_repair_prompt,
    enforce_structured,
    enforce_structured_with_client,
    parse_json_payload,
)
from backend.services.shot_spec import ShotListOutput, ShotSpec


# ---------------------------------------------------------------------------
# Fixtures / stubs
# ---------------------------------------------------------------------------


VALID_SHOT = {
    "shot_id": "sc01_sh01",
    "narrative_intent": "Establish that Maya is alone in the kitchen before the call lands.",
    "setting": "Small kitchen, early morning, overcast window light",
    "action": "Maya sets the phone face-down on the counter.",
    "lighting": "Flat grey daylight from a single window",
    "style_grade": "Muted naturalistic, low contrast",
    "duration_seconds": 4.5,
    "camera": {"framing": "Eye-Level Medium", "movement": "slow dolly in"},
    "entities": [
        {
            "entity_id": "char_maya",
            "name": "Maya",
            "kind": "character",
            "description": "Woman, 30s, dark hair pulled back, grey knit jumper",
            "expression_cues": "jaw tightening, eyes fixed on the counter",
        }
    ],
}

# schema-invalid: emotion label in a physical-cue field
EMOTION_SHOT = json.loads(json.dumps(VALID_SHOT))
EMOTION_SHOT["entities"][0]["expression_cues"] = "happy and excited"

# schema-invalid: negative duration
NEGATIVE_DURATION_SHOT = json.loads(json.dumps(VALID_SHOT))
NEGATIVE_DURATION_SHOT["duration_seconds"] = -3.0

# contract-invalid: unknown key (ShotSpec forbids extras)
EXTRA_KEY_SHOT = json.loads(json.dumps(VALID_SHOT))
EXTRA_KEY_SHOT["engine"] = "ltx-2.3"


class ScriptedProvider(LLMProvider):
    """Deterministic client: queued replies, recorded prompts, no network."""

    def __init__(self, outputs: list[str], *, model: str = "scripted-local") -> None:
        super().__init__(model=model, max_retries=1)
        self.outputs = list(outputs)
        self.calls: list[str] = []
        self.kwargs_seen: list[dict] = []

    def _generate_raw(self, prompt: str, **kwargs) -> str:
        self.calls.append(prompt)
        self.kwargs_seen.append(dict(kwargs))
        idx = min(len(self.calls) - 1, len(self.outputs) - 1)
        return self.outputs[idx]

    def health_check(self) -> bool:
        return True


def shot_list(*shots) -> str:
    return json.dumps({"shots": list(shots)})


ORIGINAL_PROMPT = (
    "You are a director breaking a script into discrete shots.\n"
    "FILMMAKING PRINCIPLES:\n  - one beat per shot\n"
    "KNOWLEDGE SEED LTX23_PROMPT_GUIDE: engine-neutral fields\n\n"
    "TASK: Produce STRICT JSON {\"shots\": [...]}\n\n"
    "SCRIPT:\nMAYA: I didn't tell you to call me.\n"
)


# ---------------------------------------------------------------------------
# 1. Valid output — returned as-is on the first attempt
# ---------------------------------------------------------------------------


def test_valid_output_returns_on_first_attempt_without_repair():
    client = ScriptedProvider([shot_list(VALID_SHOT)])

    result = enforce_structured_with_client(
        client, ORIGINAL_PROMPT, ShotListOutput, job="director.shot_list"
    )

    assert isinstance(result.value, ShotListOutput)
    assert len(result.value.shots) == 1
    assert result.value.shots[0].shot_id == "sc01_sh01"
    assert result.value.shots[0].camera.framing == "Eye-Level Medium"

    # exactly one provider call, and it was the untouched original prompt
    assert len(client.calls) == 1
    assert client.calls[0] == ORIGINAL_PROMPT
    assert result.attempt_count == 1
    assert result.repairs_used == 0
    assert result.repaired is False
    assert result.attempts[0].ok is True
    assert result.attempts[0].issues == []


def test_valid_output_tolerates_markdown_fenced_json():
    fenced = f"```json\n{shot_list(VALID_SHOT)}\n```"
    client = ScriptedProvider([fenced])

    result = enforce_structured_with_client(client, ORIGINAL_PROMPT, ShotListOutput)

    assert len(result.value.shots) == 1
    assert len(client.calls) == 1


def test_direct_shotspec_schema_is_validated_not_just_the_wrapper():
    """A bare ShotSpec payload validates against the repo's ShotSpec model."""
    client = ScriptedProvider([json.dumps(VALID_SHOT)])

    result = enforce_structured_with_client(client, ORIGINAL_PROMPT, ShotSpec)

    assert isinstance(result.value, ShotSpec)
    assert result.value.duration_seconds == 4.5
    assert len(client.calls) == 1


# ---------------------------------------------------------------------------
# 2. Invalid first response — exactly one repair, same client, success
# ---------------------------------------------------------------------------


def test_invalid_first_response_is_repaired_once_on_same_client():
    client = ScriptedProvider([shot_list(EMOTION_SHOT), shot_list(VALID_SHOT)])

    result = enforce_structured_with_client(
        client, ORIGINAL_PROMPT, ShotListOutput, job="director.shot_list"
    )

    # repaired and usable
    assert len(result.value.shots) == 1
    assert result.value.shots[0].entities[0].expression_cues == "jaw tightening, eyes fixed on the counter"
    assert result.repaired is True
    assert result.repairs_used == 1
    assert result.attempt_count == 2

    # audit trail: first attempt failed with the actionable issue, second passed
    assert result.attempts[0].ok is False
    assert result.attempts[0].label == "primary"
    assert result.attempts[0].issues[0]["path"] == "shots[0].entities[0].expression_cues"
    assert "emotion labels" in result.attempts[0].issues[0]["reason"]
    assert result.attempts[1].ok is True
    assert result.attempts[1].label == "repair"

    # exactly two calls to the SAME client, and the repair prompt preserved the
    # original prompt data verbatim
    assert len(client.calls) == 2
    repair_prompt = client.calls[1]
    assert repair_prompt.startswith(ORIGINAL_PROMPT)
    assert "SCRIPT:\nMAYA: I didn't tell you to call me." in repair_prompt
    assert "one beat per shot" in repair_prompt  # knowledge seed survived
    assert "LTX23_PROMPT_GUIDE" in repair_prompt
    assert "OUTPUT REJECTED" in repair_prompt
    assert "shots[0].entities[0].expression_cues" in repair_prompt


def test_repair_prompt_repeats_validation_errors_and_echoes_rejected_reply():
    issues = [
        {"path": "shots[1].duration_seconds", "reason": "Input should be greater than 0", "type": "greater_than"},
        {"path": "shots[0].engine", "reason": "Extra inputs are not permitted", "type": "extra_forbidden"},
    ]
    prompt = build_repair_prompt(ORIGINAL_PROMPT, '{"shots": [{"engine": "wan"}]}', issues, ShotListOutput)

    assert prompt.startswith(ORIGINAL_PROMPT)
    assert "- shots[1].duration_seconds: Input should be greater than 0" in prompt
    assert "- shots[0].engine: Extra inputs are not permitted" in prompt
    assert "ShotListOutput" in prompt
    assert '{"shots": [{"engine": "wan"}]}' in prompt


def test_repair_prompt_truncates_a_huge_rejected_reply():
    issues = [{"path": "$", "reason": "invalid JSON", "type": "json_invalid"}]
    huge = "x" * 9000
    prompt = build_repair_prompt(ORIGINAL_PROMPT, huge, issues, ShotListOutput, raw_limit=100)
    assert "x" * 100 in prompt
    assert "x" * 200 not in prompt


# ---------------------------------------------------------------------------
# 3. Second invalid response — typed error with summary + retry count
# ---------------------------------------------------------------------------


def test_two_invalid_responses_raise_typed_error_with_summary_and_retry_count():
    client = ScriptedProvider([shot_list(EMOTION_SHOT), shot_list(NEGATIVE_DURATION_SHOT)])

    with pytest.raises(InvalidLLMOutputError) as excinfo:
        enforce_structured_with_client(
            client, ORIGINAL_PROMPT, ShotListOutput, job="director.shot_list"
        )

    err = excinfo.value

    # typed, and the family is catchable as one
    assert isinstance(err, InvalidLLMOutputError)
    assert err.job == "director.shot_list"
    # provider label is class-derived ("scripted"); model is the client's own
    assert err.provider == "scripted"
    assert err.model == "scripted-local"

    # retry count: initial + exactly one repair
    assert err.attempts == 2
    assert "2 attempt(s)" in str(err)
    assert "1 repair retry" in str(err)

    # `errors` is the outstanding blocking set = the FINAL attempt's issues
    assert err.errors
    assert any("duration_seconds" in i["path"] for i in err.errors)
    assert "greater than 0" in str(err)

    # the first attempt's failure is preserved as history, not discarded
    assert "rejected on the earlier attempt 1 of 2" in str(err)
    assert "shots[0].entities[0].expression_cues" in str(err)
    assert "emotion labels" in str(err)

    # the rejected reply is retained for diagnosis
    assert NEGATIVE_DURATION_SHOT["duration_seconds"] == -3.0
    assert err.raw

    # exactly one repair request — no third call, no looping
    assert len(client.calls) == 2


def test_typed_error_does_not_switch_provider_or_retry_forever():
    """A contract violation must not escalate to another route or repeat."""
    client = ScriptedProvider(["not json at all", "still not json"])

    with pytest.raises(InvalidLLMOutputError) as excinfo:
        enforce_structured_with_client(client, ORIGINAL_PROMPT, ShotListOutput, job="director.shot_list")

    assert len(client.calls) == 2
    assert excinfo.value.attempts == 2
    assert excinfo.value.errors[0]["type"] == "json_invalid"
    assert "invalid JSON" in str(excinfo.value)


def test_max_repairs_zero_raises_typed_error_after_a_single_attempt():
    client = ScriptedProvider([shot_list(EXTRA_KEY_SHOT), shot_list(VALID_SHOT)])

    with pytest.raises(InvalidLLMOutputError) as excinfo:
        enforce_structured_with_client(
            client, ORIGINAL_PROMPT, ShotListOutput, max_repairs=0
        )

    assert len(client.calls) == 1
    assert excinfo.value.attempts == 1
    assert "0 repair retries" in str(excinfo.value)


def test_repeated_failures_are_logged_as_warnings(caplog):
    client = ScriptedProvider(["{", "{"])
    with caplog.at_level(logging.WARNING, logger="backend.llm.structured_output"):
        with pytest.raises(InvalidLLMOutputError):
            enforce_structured_with_client(client, ORIGINAL_PROMPT, ShotListOutput, job="director.shot_list")
    assert any("attempt rejected" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Mechanics the contract leans on
# ---------------------------------------------------------------------------


def test_enforce_structured_uses_the_reusable_callable_form():
    """Any raw-text callable works — provider-agnostic by construction."""
    replies = iter([shot_list(EMOTION_SHOT), shot_list(VALID_SHOT)])
    prompts: list[str] = []

    def generate(prompt: str) -> str:
        prompts.append(prompt)
        return next(replies)

    result = enforce_structured(generate, ORIGINAL_PROMPT, ShotListOutput, provider="ollama")

    assert len(result.value.shots) == 1
    assert result.repairs_used == 1
    assert len(prompts) == 2
    assert prompts[1].startswith(ORIGINAL_PROMPT)


def test_transport_errors_propagate_untouched_and_make_no_repair_request():
    """A transport failure is the caller's routing concern, not a contract one."""

    def generate(prompt: str) -> str:
        raise ConnectionError("ollama unreachable")

    with pytest.raises(ConnectionError):
        enforce_structured(generate, ORIGINAL_PROMPT, ShotListOutput)

    # max_repairs contract still holds for the callable form
    assert MAX_REPAIRS == 1


def test_transport_failure_on_the_first_call_makes_no_repair_request():
    calls: list[str] = []

    def generate(prompt: str) -> str:
        calls.append(prompt)
        raise ConnectionError("ollama unreachable")

    with pytest.raises(ConnectionError):
        enforce_structured(generate, ORIGINAL_PROMPT, ShotListOutput)
    assert len(calls) == 1


def test_generate_kwargs_are_reused_for_the_repair_request():
    client = ScriptedProvider([shot_list(EMOTION_SHOT), shot_list(VALID_SHOT)])

    enforce_structured_with_client(
        client, ORIGINAL_PROMPT, ShotListOutput, options={"temperature": 0.1}
    )

    assert len(client.kwargs_seen) == 2
    assert client.kwargs_seen[0] == {"options": {"temperature": 0.1}}
    assert client.kwargs_seen[1] == {"options": {"temperature": 0.1}}


def test_shot_list_wrapper_shape_errors_are_actionable():
    client = ScriptedProvider([json.dumps({"shots": {}}), shot_list(VALID_SHOT)])

    result = enforce_structured_with_client(client, ORIGINAL_PROMPT, ShotListOutput)

    assert result.repairs_used == 1
    assert result.attempts[0].issues[0]["path"] == "shots"
    assert "array" in result.attempts[0].issues[0]["reason"]


def test_missing_shots_key_is_actionable_and_repaired():
    client = ScriptedProvider([json.dumps({"scene": []}), shot_list(VALID_SHOT)])

    result = enforce_structured_with_client(client, ORIGINAL_PROMPT, ShotListOutput)

    assert result.repairs_used == 1
    assert result.attempts[0].issues[0]["path"] == "shots"
    assert "field required" in result.attempts[0].issues[0]["reason"]


def test_shot_list_tolerates_unknown_top_level_keys():
    payload = json.dumps({"shots": [VALID_SHOT], "notes": "internal annotation"})
    client = ScriptedProvider([payload])

    result = enforce_structured_with_client(client, ORIGINAL_PROMPT, ShotListOutput)

    assert len(result.value.shots) == 1
    assert len(client.calls) == 1


def test_only_schema_conforming_data_is_returned():
    """Every returned value is the validated schema, never raw text."""
    client = ScriptedProvider([f"prose before {shot_list(VALID_SHOT)} prose after"])

    result = enforce_structured_with_client(client, ORIGINAL_PROMPT, ShotListOutput)

    assert isinstance(result.value, ShotListOutput)
    assert isinstance(result.value.shots[0], ShotSpec)
    assert result.value.shots[0].entities[0].name == "Maya"
    # the returned value carries no trace of the surrounding prose
    assert not hasattr(result.value, "raw_text")


def test_parse_json_payload_rejects_non_text_and_non_objects():
    from backend.llm.structured_output import _Rejected

    with pytest.raises(_Rejected):
        parse_json_payload(None)
    with pytest.raises(_Rejected):
        parse_json_payload("[1, 2, 3]")


def test_multi_error_summary_is_bounded_but_complete():
    shots = [json.loads(json.dumps(VALID_SHOT)) for _ in range(15)]
    for i, s in enumerate(shots):
        s["duration_seconds"] = -float(i + 1)
    client = ScriptedProvider([shot_list(*shots), shot_list(VALID_SHOT)])

    result = enforce_structured_with_client(client, ORIGINAL_PROMPT, ShotListOutput)

    assert len(result.attempts[0].issues) == 15
    # the repair prompt truncates the rendered list but says so
    assert "further validation error(s)" in client.calls[1]