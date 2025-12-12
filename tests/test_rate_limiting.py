#!/usr/bin/env python3
"""
Test script for Gemini API rate limiting
Verifies that rate limiting enforces 15 RPM and 1,500 daily limits
"""

import time
from pathlib import Path
from vision_analyzer import VisionAnalyzer

def test_rate_limiting():
    """Test that rate limiting enforces proper delays"""
    print("🧪 Testing Gemini API Rate Limiting\n")

    # Initialize analyzer
    analyzer = VisionAnalyzer()

    if not analyzer.api_initialized:
        print("⚠️  Gemini API not initialized - test requires valid API key")
        print("   Set GEMINI_API_KEY environment variable or create ~/.ai_organizer_config/gemini_api_key.txt")
        return

    print("✅ VisionAnalyzer initialized")
    print(f"   Rate limit: {analyzer.rate_limit_rpm} RPM")
    print(f"   Daily limit: {analyzer.rate_limit_daily} requests")
    print(f"   Min interval: {analyzer.min_request_interval}s between requests\n")

    # Test 1: Check rate limit validation
    print("Test 1: Rate limit checking")
    can_make_request = analyzer._check_rate_limit()
    print(f"   Can make request: {can_make_request}")
    print(f"   Current daily usage: {analyzer.daily_requests.get('requests', 0)}/{analyzer.rate_limit_daily}\n")

    # Test 2: Simulate multiple requests to test delay enforcement
    print("Test 2: Request spacing enforcement (3 simulated requests)")
    print("   Expected: ~4 second delay between each request")

    times = []
    for i in range(3):
        start = time.time()
        analyzer._wait_for_rate_limit()
        elapsed = time.time() - start
        times.append(elapsed)
        print(f"   Request {i+1}: {elapsed:.2f}s delay")

    # Verify delays (first request should be immediate, rest should wait ~4s)
    if times[0] < 0.5:  # First request should be fast
        print("   ✅ First request: no delay (expected)")
    else:
        print("   ⚠️  First request had unexpected delay")

    for i, delay in enumerate(times[1:], start=2):
        if 3.5 <= delay <= 4.5:  # Should be ~4 seconds
            print(f"   ✅ Request {i}: proper delay enforced")
        else:
            print(f"   ⚠️  Request {i}: delay was {delay:.2f}s (expected ~4s)")

    print("\n📊 Final Stats:")
    print(f"   Total API calls tracked: {analyzer.api_calls}")
    print(f"   Cache hits: {analyzer.cache_hits}")
    print(f"   Cache misses: {analyzer.cache_misses}")
    print(f"   Daily requests: {analyzer.daily_requests.get('requests', 0)}")

    print("\n✅ Rate limiting test complete!")

if __name__ == '__main__':
    test_rate_limiting()
