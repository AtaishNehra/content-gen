"""Test platform-specific content formatting."""

import pytest

from app.models import PlatformPost


def test_twitter_character_limit():
    """Test that Twitter posts respect the 280-character limit."""
    # Create a valid Twitter post
    short_text = "This is a short tweet that fits within the character limit."
    post = PlatformPost(
        platform="twitter",
        primary_text=short_text,
        hashtags=["#test"],
        mentions=["@example"],
        thread=None,
        notes=None
    )
    assert len(post.primary_text) <= 280

    # Test that validation catches overly long posts
    long_text = "x" * 281
    with pytest.raises(ValueError, match="Twitter posts must be ≤280 characters"):
        PlatformPost(
            platform="twitter",
            primary_text=long_text,
            hashtags=["#test"],
            mentions=["@example"],
            thread=None,
            notes=None
        )


def test_linkedin_character_range():
    """Test that LinkedIn posts respect the 500-1200 character range."""
    # Valid LinkedIn post
    medium_text = "x" * 800
    post = PlatformPost(
        platform="linkedin",
        primary_text=medium_text,
        hashtags=["#professional"],
        mentions=["@company"],
        thread=None,
        notes=None
    )
    assert 500 <= len(post.primary_text) <= 1200

    # Test too short
    short_text = "x" * 400
    with pytest.raises(ValueError, match="LinkedIn posts should be 500-1200 characters"):
        PlatformPost(
            platform="linkedin",
            primary_text=short_text,
            hashtags=["#test"],
            mentions=["@example"],
            thread=None,
            notes=None
        )

    # Test too long
    long_text = "x" * 1300
    with pytest.raises(ValueError, match="LinkedIn posts should be 500-1200 characters"):
        PlatformPost(
            platform="linkedin",
            primary_text=long_text,
            hashtags=["#test"],
            mentions=["@example"],
            thread=None,
            notes=None
        )


def test_instagram_character_range():
    """Test that Instagram posts respect the 125-2200 character range."""
    # Valid Instagram post
    medium_text = "x" * 1000
    post = PlatformPost(
        platform="instagram",
        primary_text=medium_text,
        hashtags=["#insta", "#social"],
        mentions=["@influencer"],
        thread=None,
        notes=None
    )
    assert 125 <= len(post.primary_text) <= 2200

    # Test too short
    short_text = "x" * 100
    with pytest.raises(ValueError, match="Instagram posts should be 125-2200 characters"):
        PlatformPost(
            platform="instagram",
            primary_text=short_text,
            hashtags=["#test"],
            mentions=["@example"],
            thread=None,
            notes=None
        )

    # Test too long
    long_text = "x" * 2300
    with pytest.raises(ValueError, match="Instagram posts should be 125-2200 characters"):
        PlatformPost(
            platform="instagram",
            primary_text=long_text,
            hashtags=["#test"],
            mentions=["@example"],
            thread=None,
            notes=None
        )
