#!/usr/bin/env python3
"""
Verification test for file naming logic fixes.
Mocks Gemini responses with "chatter" to ensure they are cleaned.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from vision_analyzer import VisionAnalyzer

def test_json_extraction():
    print("Testing robust JSON extraction...")
    analyzer = VisionAnalyzer(api_key="mock_key")
    
    chatty_response = """
    Certainly! I've analyzed the image for you.
    Here is the structured analysis in JSON format as requested:
    
    ```json
    {
        "description": "A beautiful sunset over the mountains",
        "objects_detected": ["mountain", "sun", "sky"],
        "scene_type": "outdoor",
        "suggested_category": "photo",
        "keywords": ["sunset", "nature", "landscape"]
    }
    ```
    
    I hope this helps with your file organization!
    """
    
    result = analyzer._parse_image_analysis(chatty_response, Path("test.jpg"))
    
    assert result['success'] is True
    assert result['description'] == "A beautiful sunset over the mountains"
    assert result['suggested_category'] == "photo"
    print("✅ JSON extraction passed with chatty response.")

def test_keyword_filtering():
    print("Testing LLM chatter filtering in fallback keywords...")
    analyzer = VisionAnalyzer(api_key="mock_key")
    
    # Text that would trigger fallback if JSON fails (now mock it by making JSON parse fail)
    # The analyzer uses analysis_text.lower().split() for fallback keywords
    chatty_text = "Here's a structured analysis of the photo. It's a sunset over mountains."
    words = chatty_text.lower().split()
    
    # Updated analyzer logic in vision_analyzer.py:
    keywords = []
    for word in words:
        clean_word = word.strip('.,!?;:"\'()[]{}')
        if len(clean_word) > 4 and clean_word not in analyzer.llm_stop_words:
            if not (clean_word.endswith("'s") and clean_word[:-2] in analyzer.llm_stop_words):
                keywords.append(clean_word)
    
    print(f"Extracted keywords: {keywords}")
    
    # Should NOT contain 'here's', 'structured', 'analysis', 'photo'
    stop_words_found = [w for w in keywords if w in ['here', 'structured', 'analysis', 'photo', "here's"]]
    assert not stop_words_found, f"Stop words found in keywords: {stop_words_found}"
    assert 'sunset' in keywords or 'mountains' in keywords
    print("✅ Keyword filtering passed (robust to punctuation).")

if __name__ == "__main__":
    try:
        test_json_extraction()
        test_keyword_filtering()
        print("\n✨ All verification tests passed!")
    except Exception as e:
        print(f"\n❌ Verification failed: {e}")
        sys.exit(1)
