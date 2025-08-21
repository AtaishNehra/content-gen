"""Test scheduling functionality."""

import pytest
from datetime import datetime
from zoneinfo import ZoneInfo

from app.tools.schedule import suggest_times


def test_suggest_times_returns_sufficient_suggestions():
    """Test that suggest_times returns enough suggestions for all platforms."""
    platforms = ["twitter", "linkedin", "instagram"]
    timings = suggest_times(platforms)

    # Should return at least 6 suggestions (3 platforms × 2+ times each minimum)
    assert len(timings) >= 6, f"Expected at least 6 timings, got {len(timings)}"

    # Should have suggestions for each platform
    platform_counts = {}
    for timing in timings:
        platform_counts[timing.platform] = platform_counts.get(timing.platform, 0) + 1

    for platform in platforms:
        assert platform in platform_counts, f"Missing suggestions for {platform}"
        assert platform_counts[platform] > 0, f"No suggestions for {platform}"


def test_suggest_times_returns_valid_iso_strings():
    """Test that all returned times are valid ISO format strings."""
    platforms = ["twitter", "linkedin"]
    timings = suggest_times(platforms)

    for timing in timings:
        # Should be able to parse as ISO datetime
        try:
            parsed_time = datetime.fromisoformat(timing.local_datetime_iso)
            assert parsed_time is not None
        except ValueError:
            pytest.fail(f"Invalid ISO string: {timing.local_datetime_iso}")


def test_suggest_times_includes_rationale():
    """Test that each timing includes a meaningful rationale."""
    platforms = ["twitter"]
    timings = suggest_times(platforms)

    for timing in timings:
        assert timing.rationale, "Each timing should have a rationale"
        assert len(timing.rationale) > 10, "Rationale should be meaningful"


def test_suggest_times_respects_timezone():
    """Test that suggested times are in the configured timezone."""
    from app.config import config

    platforms = ["instagram"]
    timings = suggest_times(platforms)

    # Parse one timing to check timezone
    if timings:
        sample_time = datetime.fromisoformat(timings[0].local_datetime_iso)
        
        # Should have timezone info
        assert sample_time.tzinfo is not None, "Times should be timezone-aware"
        
        # Should match configured timezone
        expected_tz = ZoneInfo(config.DEFAULT_TZ)
        assert sample_time.tzinfo == expected_tz, f"Expected {expected_tz}, got {sample_time.tzinfo}"


def test_suggest_times_future_times():
    """Test that suggested times are in the future."""
    from app.config import config

    platforms = ["linkedin"]
    timings = suggest_times(platforms)
    
    current_time = datetime.now(ZoneInfo(config.DEFAULT_TZ))

    for timing in timings:
        suggested_time = datetime.fromisoformat(timing.local_datetime_iso)
        assert suggested_time > current_time, f"Time {suggested_time} should be in the future"


def test_suggest_times_empty_platforms():
    """Test handling of empty platform list."""
    timings = suggest_times([])
    assert timings == [], "Empty platform list should return empty suggestions"
