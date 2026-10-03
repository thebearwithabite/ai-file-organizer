"""Template + six-override discipline tests (renderer boundary)."""
from __future__ import annotations

import json

import pytest

from backend.integrations.wangp_settings import (
    ALLOWED_OVERRIDE_KEYS,
    ResolvedSettings,
    SettingsDisciplineError,
    TemplateDeviationError,
    UnknownOverrideError,
    apply_overrides,
    build_generation_settings,
    enforce_bounded_settings,
    load_template,
    merge_job_inputs,
)

TEMPLATE = {
    "model_type": "ltx2_22B_distilled_gguf_q4_k_m",
    "resolution": "1280x720",
    "video_length": 241,
    "num_inference_steps": 8,
    "guidance_phases": 2,
    "prompt": "template prompt",
    "settings_version": 2.7,
}


class TestOverrideAllowList:
    def test_exactly_the_six_canonical_keys(self):
        assert set(ALLOWED_OVERRIDE_KEYS) == {"width", "height", "frames", "fps", "steps", "loras"}

    def test_all_six_map_to_native_fields(self):
        result = apply_overrides(
            TEMPLATE,
            {
                "width": 512,
                "height": 320,
                "frames": 9,
                "fps": 24,
                "steps": 12,
                "loras": ["Ltx2.3-Licon.safetensors"],
            },
        )
        assert result["resolution"] == "512x320"
        assert result["video_length"] == 9
        assert result["force_fps"] == 24
        assert result["num_inference_steps"] == 12
        assert result["activated_loras"] == ["Ltx2.3-Licon.safetensors"]
        # everything else is untouched
        assert result["guidance_phases"] == 2
        assert result["prompt"] == "template prompt"
        assert result["settings_version"] == 2.7

    def test_partial_dimension_override_uses_template_other_axis(self):
        assert apply_overrides(TEMPLATE, {"width": 640})["resolution"] == "640x720"
        assert apply_overrides(TEMPLATE, {"height": 360})["resolution"] == "1280x360"

    def test_dimension_override_without_parsable_template_resolution(self):
        with pytest.raises(SettingsDisciplineError):
            apply_overrides({"model_type": "x"}, {"width": 640})

    def test_unknown_override_key_is_rejected(self):
        with pytest.raises(UnknownOverrideError) as excinfo:
            apply_overrides(TEMPLATE, {"guidance_scale": 3.0})
        message = str(excinfo.value)
        assert "guidance_scale" in message
        for allowed in ALLOWED_OVERRIDE_KEYS:
            assert allowed in message

    @pytest.mark.parametrize("value", [0, -1, "abc", True])
    def test_invalid_integer_values_rejected(self, value):
        with pytest.raises(UnknownOverrideError):
            apply_overrides(TEMPLATE, {"steps": value})

    def test_numeric_strings_accepted(self):
        assert apply_overrides(TEMPLATE, {"steps": "12"})["num_inference_steps"] == 12


class TestLoras:
    def test_string_becomes_single_name(self):
        assert apply_overrides(TEMPLATE, {"loras": "a.safetensors"})["activated_loras"] == [
            "a.safetensors"
        ]

    def test_dict_with_multipliers(self):
        result = apply_overrides(
            TEMPLATE,
            {"loras": {"names": ["a.safetensors", "b.safetensors"], "multipliers": "1;0.5"}},
        )
        assert result["activated_loras"] == ["a.safetensors", "b.safetensors"]
        assert result["loras_multipliers"] == "1;0.5"

    def test_dict_with_unknown_keys_rejected(self):
        with pytest.raises(UnknownOverrideError):
            apply_overrides(TEMPLATE, {"loras": {"names": ["a"], "bogus": 1}})

    def test_non_list_object_rejected(self):
        with pytest.raises(UnknownOverrideError):
            apply_overrides(TEMPLATE, {"loras": 12})


class TestJobInputs:
    def test_job_inputs_are_attached(self):
        result = merge_job_inputs(
            TEMPLATE, {"prompt": "hi", "seed": 7, "image_start": "D:\\a.png"}
        )
        assert result["prompt"] == "hi"
        assert result["seed"] == 7
        assert result["image_start"] == "D:\\a.png"

    def test_native_setting_keys_rejected_as_job_inputs(self):
        with pytest.raises(UnknownOverrideError):
            merge_job_inputs(TEMPLATE, {"resolution": "512x320"})

    def test_unknown_keys_rejected(self):
        with pytest.raises(SettingsDisciplineError):
            merge_job_inputs(TEMPLATE, {"vibes": "good"})

    def test_build_generation_settings_is_the_sanctioned_path(self):
        payload = build_generation_settings(TEMPLATE, {"frames": 9}, {"prompt": "hi"})
        assert payload["video_length"] == 9
        assert payload["prompt"] == "hi"
        assert payload["resolution"] == "1280x720"  # untouched template field


class TestEnforceBoundedSettings:
    def test_accepts_template_plus_overrides_plus_job_inputs(self):
        overrides = {"width": 512, "height": 320, "steps": 12}
        payload = build_generation_settings(TEMPLATE, overrides, {"prompt": "hi", "seed": 7})
        enforce_bounded_settings(payload, TEMPLATE, overrides)  # must not raise

    def test_rejects_changed_template_field(self):
        payload = build_generation_settings(TEMPLATE, {}, {"prompt": "hi"})
        payload["guidance_phases"] = 5
        with pytest.raises(TemplateDeviationError, match="guidance_phases"):
            enforce_bounded_settings(payload, TEMPLATE, {})

    def test_rejects_missing_template_field(self):
        payload = build_generation_settings(TEMPLATE, {}, {"prompt": "hi"})
        del payload["settings_version"]
        with pytest.raises(TemplateDeviationError, match="settings_version"):
            enforce_bounded_settings(payload, TEMPLATE, {})

    def test_rejects_smuggled_native_setting(self):
        payload = build_generation_settings(TEMPLATE, {}, {"prompt": "hi"})
        payload["force_fps"] = 30
        with pytest.raises(TemplateDeviationError, match="force_fps"):
            enforce_bounded_settings(payload, TEMPLATE, {})

    def test_rejects_unknown_payload_field(self):
        payload = build_generation_settings(TEMPLATE, {}, {"prompt": "hi"})
        payload["vibes"] = "good"
        with pytest.raises(SettingsDisciplineError, match="vibes"):
            enforce_bounded_settings(payload, TEMPLATE, {})

    def test_rejects_payload_that_ignored_its_own_overrides(self):
        payload = build_generation_settings(TEMPLATE, {}, {"prompt": "hi"})
        with pytest.raises(TemplateDeviationError, match="resolution"):
            enforce_bounded_settings(payload, TEMPLATE, {"width": 512, "height": 320})


class TestTemplateFiles:
    def test_load_template_tolerates_bom(self, tmp_path):
        path = tmp_path / "t.json"
        path.write_bytes(json.dumps(TEMPLATE).encode("utf-8-sig"))
        assert load_template(path) == TEMPLATE

    def test_load_template_rejects_non_object(self, tmp_path):
        path = tmp_path / "t.json"
        path.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
        with pytest.raises(SettingsDisciplineError):
            load_template(path)


class TestResolvedSettings:
    def test_from_file_roundtrip(self, tmp_path):
        path = tmp_path / "t.json"
        path.write_text(json.dumps(TEMPLATE), encoding="utf-8")
        resolved = ResolvedSettings.from_file(path, {"width": 640, "height": 360})
        assert resolved.resolved_settings()["resolution"] == "640x360"
        payload = resolved.build_payload({"prompt": "x"})
        assert payload["prompt"] == "x"
        assert payload["video_length"] == 241
        assert resolved.as_manifest()["template_path"] == str(path)
        assert resolved.as_manifest()["overrides"] == {"width": 640, "height": 360}

    def test_bad_overrides_rejected_at_construction(self):
        with pytest.raises(UnknownOverrideError):
            ResolvedSettings.from_template(TEMPLATE, {"guidance_scale": 3.0})

    def test_from_template_keeps_template_intact(self):
        template = dict(TEMPLATE)
        resolved = ResolvedSettings.from_template(template, {"frames": 9})
        assert template["video_length"] == 241  # not mutated
        assert resolved.resolved_settings()["video_length"] == 9
