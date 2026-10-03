"""Structured-output enforcement for LLM jobs (PROMPT-MACHINE-DIRECTIVE v1.2).

Every LLM response that reaches a director job goes through this module before
it is handed back: parse, validate, and return **only** schema-conforming data.
The schema is the repository's existing ShotSpec model
(``backend.services.shot_spec``) — not a parallel definition — so a shot is one
shape across the director pass, the review loop, asset bindings, and the prompt
compiler.

The contract:

* a valid first response is returned as-is (one provider call, no repair);
* an invalid first response triggers **exactly one** repair request, sent to the
  **same** client that produced the invalid output. The repair prompt carries
  the original prompt verbatim plus the actionable validation errors, so prompt
  data (system framing, knowledge seeds, script text) is never dropped;
* a still-invalid repair response raises ``InvalidLLMOutputError`` carrying the
  validation summary and the retry count.

This module is provider-agnostic and deliberately knows nothing about routing,
vendor selection, or credentials. A contract violation is not a transport
failure: escalating a malformed reply to a different vendor hides the real
defect behind a different model's guesswork, so the typed error is the
deliverable and the caller decides what to do next. Transport exceptions
propagate untouched for the same reason.

Usage — with an already-selected client (what the router does)::

    enforce_structured_with_client(client, prompt, ShotListOutput, job=...)

Usage — with any callable that returns raw text (tests, alternate transports)::

    enforce_structured(lambda p: raw, prompt, ShotListOutput, provider=...)

Validation notes:

* ``ShotSpec`` validates through ``validate_shot_spec()`` so error paths use
  the repository's actionable ``entities[0].name`` form (not pydantic's
  ``entities.0.name``) and the ``Value error, `` prefix is stripped.
* ``ShotListOutput`` validates each shot independently and prefixes paths with
  ``shots[i]``, so a repair prompt names the exact offending shot.
* The ``shots`` wrapper itself is deliberately lenient about unknown top-level
  keys: strictness belongs to ``ShotSpec`` (whose contract forbids extras so a
  stale generation block cannot re-enter), and over-strict wrapper validation
  would burn repair retries on harmless annotations.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generic, List, Optional, Type, TypeVar

from pydantic import BaseModel

from backend.llm.base import LLMProvider
from backend.llm.errors import InvalidLLMOutputError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

#: Exactly one repair request is the contract; callers may lower it to 0.
MAX_REPAIRS = 1

#: How much of the rejected reply is echoed back in the repair prompt.
RAW_SNIPPET_LIMIT = 2000

#: Cap on validation errors rendered into the typed error's message. The full
#: set always stays on ``InvalidLLMOutputError.errors``.
MAX_ISSUES_IN_MESSAGE = 12


# ---------------------------------------------------------------------------
# Result / attempt records
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StructuredAttempt:
    """One provider call made by the enforcer, primary or repair."""

    label: str  # "primary" | "repair"
    raw: str
    ok: bool
    issues: List[Dict[str, str]] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "attempt": self.label,
            "ok": self.ok,
            "issues": [dict(i) for i in self.issues],
        }


@dataclass(frozen=True)
class StructuredResult(Generic[T]):
    """A validated value plus the audit trail of how it was obtained."""

    value: T
    raw: str
    attempts: List[StructuredAttempt] = field(default_factory=list)

    @property
    def attempt_count(self) -> int:
        return len(self.attempts)

    @property
    def repairs_used(self) -> int:
        return sum(1 for a in self.attempts if a.label == "repair")

    @property
    def repaired(self) -> bool:
        return self.repairs_used > 0

    def as_dict(self) -> Dict[str, Any]:
        return {
            "attempts": [a.as_dict() for a in self.attempts],
            "repairs_used": self.repairs_used,
        }


class _Rejected(Exception):
    """Internal: output did not conform. Never escapes this module."""

    def __init__(self, issues: List[Dict[str, str]], raw: str) -> None:
        super().__init__("output rejected")
        self.issues = issues
        self.raw = raw


# ---------------------------------------------------------------------------
# Validation — ShotSpec-aware
# ---------------------------------------------------------------------------


def _issue(path: str, reason: str, type_: str) -> Dict[str, str]:
    return {"path": path or "$", "reason": reason, "type": type_}


def _validate_shot_spec_payload(data: Any) -> BaseModel:
    from backend.services.shot_spec import validate_shot_spec

    try:
        return validate_shot_spec(data, source="llm output")
    except Exception as exc:
        issues = getattr(exc, "errors", None)
        if not issues:
            raise _Rejected([_issue("$", str(exc), "type_error")], "") from None
        raise _Rejected([dict(i) for i in issues], "") from None


def _validate_shot_list_payload(data: Any) -> BaseModel:
    """Validate ``{"shots": [...]}`` shot-by-shot so repair paths are precise."""
    from backend.services.shot_spec import ShotListOutput, ShotSpecValidationError

    if not isinstance(data, dict):
        raise _Rejected(
            [_issue("$", f"expected a JSON object with a 'shots' array, got {type(data).__name__}", "type_error")],
            "",
        )
    if "shots" not in data:
        raise _Rejected([_issue("shots", "field required", "missing")], "")

    shots = data["shots"]
    if not isinstance(shots, list):
        raise _Rejected(
            [_issue("shots", f"expected an array of ShotSpec objects, got {type(shots).__name__}", "type_error")],
            "",
        )

    issues: List[Dict[str, str]] = []
    validated = []
    for i, raw_shot in enumerate(shots):
        try:
            validated.append(_validate_shot_spec_payload(raw_shot))
        except _Rejected as rejected:
            for issue in rejected.issues:
                prefix = issue["path"]
                path = f"shots[{i}]" if prefix == "$" else f"shots[{i}].{prefix}"
                issues.append(_issue(path, issue["reason"], issue["type"]))
        except ShotSpecValidationError as exc:  # defensive: raw raise from validator
            for issue in exc.errors:
                issues.append(_issue(f"shots[{i}].{issue['path']}", issue["reason"], issue["type"]))
        except Exception as exc:
            issues.append(_issue(f"shots[{i}]", str(exc), "type_error"))

    if issues:
        raise _Rejected(issues, "")
    # Unknown top-level keys are ignored on purpose — see the module docstring.
    return ShotListOutput(shots=validated)


#: schema class -> validator. Populated lazily to keep this module free of a
#: services-layer import at module scope.
_VALIDATORS: Dict[type, Callable[[Any], BaseModel]] = {}
_VALIDATORS_READY = False


def _ensure_validators() -> None:
    global _VALIDATORS_READY
    if _VALIDATORS_READY:
        return
    from backend.services.shot_spec import ShotListOutput, ShotSpec

    _VALIDATORS[ShotSpec] = _validate_shot_spec_payload
    _VALIDATORS[ShotListOutput] = _validate_shot_list_payload
    _VALIDATORS_READY = True


def register_validator(schema: type, validator: Callable[[Any], BaseModel]) -> None:
    """Register a validator for a custom schema (used by tests and extensions)."""
    _ensure_validators()
    _VALIDATORS[schema] = validator


def validator_for(schema: Type[BaseModel]) -> Callable[[Any], BaseModel]:
    """The validator used for ``schema``: registered if any, else ``model_validate``."""
    _ensure_validators()
    registered = _VALIDATORS.get(schema)
    if registered is not None:
        return registered
    return lambda data: schema.model_validate(data)


# ---------------------------------------------------------------------------
# Parse + validate
# ---------------------------------------------------------------------------


def parse_json_payload(raw: Any) -> Dict[str, Any]:
    """Extract the JSON object from a raw reply (markdown fences tolerated).

    Raises ``_Rejected`` with a single ``json_invalid`` issue on failure.
    """
    if not isinstance(raw, str):
        raise _Rejected(
            [_issue("$", f"expected a text reply, got {type(raw).__name__}", "type_error")],
            raw if isinstance(raw, str) else "",
        )
    try:
        data = LLMProvider._extract_json(raw)
    except Exception as exc:
        raise _Rejected([_issue("$", f"invalid JSON: {exc}", "json_invalid")], raw) from None
    if not isinstance(data, dict):
        raise _Rejected(
            [_issue("$", f"expected a JSON object, got {type(data).__name__}", "type_error")],
            raw,
        )
    return data


def validate_payload(data: Any, schema: Type[T]) -> T:
    """Validate ``data`` against ``schema``; raise ``_Rejected`` on any failure."""
    validator = validator_for(schema)
    try:
        value = validator(data)
    except _Rejected:
        raise
    except Exception as exc:
        raise _Rejected([_issue("$", f"{schema.__name__}: {exc}", "validation_error")], "") from None
    # The registered validator for a custom schema may not honour its contract.
    if not isinstance(value, schema):
        raise _Rejected(
            [_issue("$", f"validator returned {type(value).__name__}, expected {schema.__name__}", "type_error")],
            "",
        )
    return value


def parse_and_validate(raw: Any, schema: Type[T]) -> T:
    """Parse then validate one raw reply. Raises ``_Rejected``."""
    return validate_payload(parse_json_payload(raw), schema)


# ---------------------------------------------------------------------------
# Repair prompt
# ---------------------------------------------------------------------------


def format_issues(issues: List[Dict[str, str]], limit: int = MAX_ISSUES_IN_MESSAGE) -> str:
    """Render validation issues as ``- <path>: <reason>`` lines."""
    lines = [f"- {i.get('path', '$')}: {i.get('reason', '')}" for i in issues[:limit]]
    if len(issues) > limit:
        lines.append(f"- ... and {len(issues) - limit} further validation error(s)")
    return "\n".join(lines) or "- (none reported)"


def build_repair_prompt(
    original: str,
    raw: str,
    issues: List[Dict[str, str]],
    schema: Type[BaseModel],
    *,
    raw_limit: int = RAW_SNIPPET_LIMIT,
) -> str:
    """Build the single repair request: original prompt preserved verbatim.

    The original prompt is included unchanged so the model keeps every piece of
    prompt data it was given (role framing, knowledge seeds, script body). The
    rejected reply is echoed for reference, truncated to ``raw_limit``.
    """
    return (
        f"{original}\n\n"
        "=== OUTPUT REJECTED — CORRECT IT ===\n"
        f"Your previous reply was not valid {schema.__name__} JSON. "
        "Validation errors:\n"
        f"{format_issues(issues)}\n\n"
        "Previous reply (for reference):\n"
        f"{(raw or '').strip()[:raw_limit]}\n\n"
        f"Return ONLY a corrected JSON object matching {schema.__name__}. "
        "Keep every field you already had that validated. No markdown fences, "
        "no commentary, no trailing text."
    )


# ---------------------------------------------------------------------------
# Enforcement
# ---------------------------------------------------------------------------


def _typed_error(
    *,
    job: str,
    schema: Type[BaseModel],
    provider: str,
    model: str,
    raw: str,
    issues: List[Dict[str, str]],
    attempts: int,
    repairs: int,
    prior_issues: Optional[List[List[Dict[str, str]]]] = None,
) -> InvalidLLMOutputError:
    """Build the typed contract failure.

    ``errors`` carries the FINAL attempt's issues — that is the blocking set a
    caller should act on. Earlier attempts' issues are rendered into the message
    as history so the first rejection (often the most diagnostic one, e.g. the
    emotion-label rule) is not lost.
    """
    label = job or "llm"
    who = provider or "<unknown provider>"
    noun = "retry" if repairs == 1 else "retries"
    sections = [format_issues(issues)]
    for i, earlier in enumerate(prior_issues or []):
        sections.append(
            f"(rejected on the earlier attempt {i + 1} of {attempts}:\n"
            f"{format_issues(earlier)})"
        )
    message = (
        f"{label}: provider {who!r} returned output that failed {schema.__name__} "
        f"validation after {attempts} attempt(s) ({repairs} repair {noun} used, "
        f"{len(issues)} validation error(s) outstanding). The repair request reused "
        f"the same client; no other route was taken for this contract violation.\n"
        + "\n".join(sections)
    )
    return InvalidLLMOutputError(
        message,
        provider=provider,
        model=model,
        raw=raw,
        errors=issues,
        attempts=attempts,
        job=job,
    )


def enforce_structured(
    generate: Callable[[str], str],
    prompt: str,
    schema: Type[T],
    *,
    provider: str = "",
    model: str = "",
    job: str = "",
    max_repairs: int = MAX_REPAIRS,
) -> StructuredResult[T]:
    """Return validated ``schema`` data, making exactly one repair request.

    ``generate`` is called with the prompt and must return raw text. It is the
    *same* callable for the primary attempt and the repair — a contract
    violation never changes provider. Transport exceptions from ``generate``
    propagate unchanged (they are the caller's routing concern).

    Raises ``InvalidLLMOutputError`` when the repair response is still invalid.
    """
    repairs_left = max(0, int(max_repairs))
    attempts: List[StructuredAttempt] = []

    attempt_prompt = prompt
    label = "primary"

    while True:
        raw = generate(attempt_prompt)
        try:
            value = parse_and_validate(raw, schema)
        except _Rejected as rejected:
            attempts.append(
                StructuredAttempt(label=label, raw=raw or "", ok=False, issues=list(rejected.issues))
            )
            logger.warning(
                "llm.structured_output %s %s attempt rejected (%d validation error(s)): %s",
                job or "llm",
                schema.__name__,
                len(rejected.issues),
                format_issues(rejected.issues, limit=3),
            )
            if repairs_left > 0:
                repairs_left -= 1
                label = "repair"
                attempt_prompt = build_repair_prompt(prompt, raw or "", rejected.issues, schema)
                continue
            attempts_used = len(attempts)
            raise _typed_error(
                job=job,
                schema=schema,
                provider=provider,
                model=model,
                raw=raw or "",
                issues=rejected.issues,
                attempts=attempts_used,
                repairs=attempts_used - 1,
                prior_issues=[a.issues for a in attempts[:-1] if a.issues],
            ) from None

        attempts.append(StructuredAttempt(label=label, raw=raw or "", ok=True, issues=[]))
        return StructuredResult(value=value, raw=raw or "", attempts=attempts)


def client_label(client: Any) -> str:
    """Best-effort provider label for an arbitrary client object.

    The router owns canonical provider naming; this is the fallback used when a
    caller does not pass one explicitly.
    """
    for attr in ("provider_name", "name", "provider"):
        value = getattr(client, attr, None)
        if isinstance(value, str) and value:
            return value
    stem = type(client).__name__.lower()
    for suffix in ("client", "provider"):
        if stem.endswith(suffix):
            return stem[: -len(suffix)]
    return stem


def enforce_structured_with_client(
    client: Any,
    prompt: str,
    schema: Type[T],
    *,
    job: str = "",
    provider: Optional[str] = None,
    max_repairs: int = MAX_REPAIRS,
    **generate_kwargs: Any,
) -> StructuredResult[T]:
    """Enforce structured output against an already-selected provider client.

    Both the primary attempt and the repair go through ``client.generate``, so
    the repair reuses the same provider/client and the same call kwargs.
    """
    return enforce_structured(
        lambda p: client.generate(p, **generate_kwargs),
        prompt,
        schema,
        provider=provider if provider is not None else client_label(client),
        model=str(getattr(client, "model", "") or ""),
        job=job,
        max_repairs=max_repairs,
    )


__all__ = [
    "MAX_REPAIRS",
    "StructuredAttempt",
    "StructuredResult",
    "build_repair_prompt",
    "client_label",
    "enforce_structured",
    "enforce_structured_with_client",
    "format_issues",
    "parse_and_validate",
    "parse_json_payload",
    "register_validator",
    "validate_payload",
    "validator_for",
]