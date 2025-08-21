"""Test fact-checking functionality."""

import pytest

from app.models import Claim
from app.tools.factcheck import verify_claims


def test_verify_claims_increases_confidence():
    """Test that verify_claims increases confidence for claims."""
    # Create a benign claim that should find search results
    claims = [
        Claim(text="Python is a programming language", severity="low", confidence=0.0),
        Claim(text="OpenAI created GPT models", severity="medium", confidence=0.0),
    ]

    verified_claims = verify_claims(claims)

    # Confidence should increase from the baseline 0.25 + search results boost
    for claim in verified_claims:
        assert claim.confidence >= 0.25, f"Confidence {claim.confidence} should be at least 0.25"
        assert claim.confidence <= 1.0, f"Confidence {claim.confidence} should not exceed 1.0"

    # Should have some sources
    assert any(claim.sources for claim in verified_claims), "At least one claim should have sources"


def test_verify_claims_preserves_claim_properties():
    """Test that verification preserves original claim properties."""
    original_claims = [
        Claim(text="Test claim about technology", severity="high", confidence=0.1),
        Claim(text="Another test claim", severity="low", confidence=0.0),
    ]

    verified_claims = verify_claims(original_claims)

    assert len(verified_claims) == len(original_claims)

    for original, verified in zip(original_claims, verified_claims):
        assert verified.text == original.text
        assert verified.severity == original.severity
        assert verified.confidence >= original.confidence  # Should not decrease


def test_verify_claims_empty_list():
    """Test that verify_claims handles empty input gracefully."""
    empty_claims = []
    verified_claims = verify_claims(empty_claims)
    assert verified_claims == []


def test_verify_claims_with_obscure_claim():
    """Test verification with a claim that might not find many results."""
    obscure_claims = [
        Claim(
            text="XYZ123 is the best unknown product ever created in 2089",
            severity="high",
            confidence=0.0,
        )
    ]

    verified_claims = verify_claims(obscure_claims)

    # Even obscure claims should get at least the baseline confidence
    assert verified_claims[0].confidence >= 0.25
