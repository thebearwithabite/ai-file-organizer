"""
Phase 3b · Test Suite · Continuity Analyzer
"""

from continuity_analyzer import analyze_continuity

def test_analyze_continuity_basic():
    batch_results = [
        {"veo_json": {"shot_id": "A", "scene": {"visual_style": "noir"}, "audio": {"ambience": "rain"}}},
        {"veo_json": {"shot_id": "B", "scene": {"visual_style": "noir"}, "audio": {"ambience": "rain"}}},
    ]
    result = analyze_continuity(batch_results)
    assert len(result) == 1
    item = result[0]
    assert 0 <= item["continuity_score"] <= 1
    assert item["recommend_extend"] in [True, False]
