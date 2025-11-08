#!/usr/bin/env python3
"""
Performance Test Suite for Sprint 3.4

Tests API latency and stability under load.
Target: <150ms median latency for critical endpoints

Created by: Task Orchestrator / Claude Code
"""

import pytest
import httpx
import time
import statistics
from typing import List, Dict

# API base URL
BASE_URL = "http://localhost:8000"

class PerformanceMetrics:
    """Helper class to track and analyze performance metrics"""

    def __init__(self):
        self.latencies: List[float] = []

    def add(self, latency_ms: float):
        """Add a latency measurement in milliseconds"""
        self.latencies.append(latency_ms)

    def median(self) -> float:
        """Calculate median latency"""
        return statistics.median(self.latencies) if self.latencies else 0

    def mean(self) -> float:
        """Calculate mean latency"""
        return statistics.mean(self.latencies) if self.latencies else 0

    def p95(self) -> float:
        """Calculate 95th percentile latency"""
        if not self.latencies:
            return 0
        sorted_latencies = sorted(self.latencies)
        index = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[index]

    def summary(self) -> Dict[str, float]:
        """Get performance summary"""
        return {
            "count": len(self.latencies),
            "median_ms": round(self.median(), 2),
            "mean_ms": round(self.mean(), 2),
            "p95_ms": round(self.p95(), 2),
            "min_ms": round(min(self.latencies), 2) if self.latencies else 0,
            "max_ms": round(max(self.latencies), 2) if self.latencies else 0
        }


@pytest.mark.asyncio
async def test_health_endpoint_latency():
    """Test /health endpoint latency (should be fast)"""
    metrics = PerformanceMetrics()

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # Warm-up request
        await client.get("/health")

        # Run 100 requests
        for _ in range(100):
            start = time.time()
            response = await client.get("/health")
            latency_ms = (time.time() - start) * 1000

            assert response.status_code == 200
            metrics.add(latency_ms)

    summary = metrics.summary()
    print(f"\n/health performance: {summary}")

    # Health endpoint should be very fast (< 50ms median)
    assert summary["median_ms"] < 50, f"Health endpoint too slow: {summary['median_ms']}ms"


@pytest.mark.asyncio
async def test_system_status_latency():
    """Test /api/system/status endpoint latency"""
    metrics = PerformanceMetrics()

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # Warm-up request
        await client.get("/api/system/status")

        # Run 50 requests
        for _ in range(50):
            start = time.time()
            response = await client.get("/api/system/status")
            latency_ms = (time.time() - start) * 1000

            assert response.status_code == 200
            metrics.add(latency_ms)

    summary = metrics.summary()
    print(f"\n/api/system/status performance: {summary}")

    # Target: <150ms median
    assert summary["median_ms"] < 150, f"System status too slow: {summary['median_ms']}ms"


@pytest.mark.asyncio
async def test_confidence_mode_get_latency():
    """Test GET /api/settings/confidence-mode latency"""
    metrics = PerformanceMetrics()

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # Warm-up request
        await client.get("/api/settings/confidence-mode")

        # Run 50 requests
        for _ in range(50):
            start = time.time()
            response = await client.get("/api/settings/confidence-mode")
            latency_ms = (time.time() - start) * 1000

            assert response.status_code == 200
            metrics.add(latency_ms)

    summary = metrics.summary()
    print(f"\nGET /api/settings/confidence-mode performance: {summary}")

    # Target: <150ms median
    assert summary["median_ms"] < 150, f"Confidence mode GET too slow: {summary['median_ms']}ms"


@pytest.mark.asyncio
async def test_space_protection_get_latency():
    """Test GET /api/system/space-protection latency"""
    metrics = PerformanceMetrics()

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # Warm-up request
        await client.get("/api/system/space-protection")

        # Run 50 requests
        for _ in range(50):
            start = time.time()
            response = await client.get("/api/system/space-protection")
            latency_ms = (time.time() - start) * 1000

            assert response.status_code == 200
            metrics.add(latency_ms)

    summary = metrics.summary()
    print(f"\nGET /api/system/space-protection performance: {summary}")

    # Target: <150ms median
    assert summary["median_ms"] < 150, f"Space protection GET too slow: {summary['median_ms']}ms"


@pytest.mark.asyncio
async def test_rollback_operations_latency():
    """Test GET /api/rollback/operations latency"""
    metrics = PerformanceMetrics()

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # Warm-up request
        await client.get("/api/rollback/operations")

        # Run 50 requests
        for _ in range(50):
            start = time.time()
            response = await client.get("/api/rollback/operations")
            latency_ms = (time.time() - start) * 1000

            assert response.status_code == 200
            metrics.add(latency_ms)

    summary = metrics.summary()
    print(f"\nGET /api/rollback/operations performance: {summary}")

    # Target: <150ms median
    assert summary["median_ms"] < 150, f"Rollback operations GET too slow: {summary['median_ms']}ms"


@pytest.mark.asyncio
async def test_monitor_status_latency():
    """Test GET /api/system/monitor-status latency"""
    metrics = PerformanceMetrics()

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # Warm-up request
        await client.get("/api/system/monitor-status")

        # Run 50 requests
        for _ in range(50):
            start = time.time()
            response = await client.get("/api/system/monitor-status")
            latency_ms = (time.time() - start) * 1000

            assert response.status_code == 200
            metrics.add(latency_ms)

    summary = metrics.summary()
    print(f"\nGET /api/system/monitor-status performance: {summary}")

    # Target: <150ms median
    assert summary["median_ms"] < 150, f"Monitor status GET too slow: {summary['median_ms']}ms"


@pytest.mark.asyncio
async def test_combined_endpoint_load():
    """Test multiple endpoints under simultaneous load"""
    print("\n\nCombined load test - hitting multiple endpoints")

    endpoints = [
        "/health",
        "/api/system/status",
        "/api/settings/confidence-mode",
        "/api/system/space-protection",
        "/api/rollback/operations",
        "/api/system/monitor-status"
    ]

    overall_metrics = PerformanceMetrics()

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # Run 300 total requests across all endpoints
        for i in range(50):
            for endpoint in endpoints:
                start = time.time()
                response = await client.get(endpoint)
                latency_ms = (time.time() - start) * 1000

                assert response.status_code == 200
                overall_metrics.add(latency_ms)

    summary = overall_metrics.summary()
    print(f"\nCombined load test (300 requests): {summary}")

    # Target: <150ms median even under load
    assert summary["median_ms"] < 150, f"Combined load test too slow: {summary['median_ms']}ms"

    # P95 should still be reasonable
    assert summary["p95_ms"] < 300, f"P95 latency too high: {summary['p95_ms']}ms"


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "-s", "--asyncio-mode=auto"])
