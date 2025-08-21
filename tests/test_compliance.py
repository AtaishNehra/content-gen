"""Test compliance review functionality."""

import pytest

from app.models import Claim
from app.tools.compliance import review_post


def test_compliance_flags_problematic_content():
    """Test that compliance review flags obviously problematic content."""
    # Text with multiple compliance issues
    problematic_text = "We guarantee 100% results in 7 days with our amazing cure!"

    # Create a low-confidence numeric claim
    low_confidence_claims = [
        Claim(
            text="100% success rate in clinical trials",
            severity="high",
            confidence=0.3,  # Low confidence
        )
    ]

    review = review_post("twitter", problematic_text, low_confidence_claims)

    # Should be flagged or blocked due to multiple issues
    assert review.status in ["flag", "block"], f"Expected flag/block, got {review.status}"

    # Should have multiple issues identified
    assert len(review.issues) > 0, "Should identify compliance issues"

    # Check for expected issue types
    issue_types = [issue.rule_id for issue in review.issues]
    assert "absolute_claims" in issue_types, "Should detect absolute claims"
    assert "low_confidence_claim" in issue_types, "Should detect low-confidence claims"


def test_compliance_passes_clean_content():
    """Test that compliance review passes clean content."""
    clean_text = "Our product may help improve your workflow efficiency based on user feedback."

    clean_claims = [
        Claim(
            text="User feedback shows potential efficiency improvements",
            severity="low",
            confidence=0.8,  # High confidence
        )
    ]

    review = review_post("linkedin", clean_text, clean_claims)

    # Should pass with no major issues
    assert review.status == "pass", f"Expected pass, got {review.status}"


def test_compliance_strict_mode():
    """Test strict mode catches additional issues."""
    # Import and temporarily modify config for this test
    from app.config import config

    original_mode = config.COMPLIANCE_MODE
    try:
        config.COMPLIANCE_MODE = "strict"

        # Text with medical claims (should be critical in strict mode)
        medical_text = "This treatment can cure diabetes and diagnose heart conditions."

        review = review_post("instagram", medical_text, [])

        # Should be blocked in strict mode
        assert review.status == "block", f"Expected block in strict mode, got {review.status}"

        # Should have critical issues
        critical_issues = [issue for issue in review.issues if issue.severity == "critical"]
        assert len(critical_issues) > 0, "Should have critical issues in strict mode"

    finally:
        # Restore original mode
        config.COMPLIANCE_MODE = original_mode


def test_compliance_issue_suggestions():
    """Test that compliance issues include helpful suggestions."""
    problematic_text = "We guarantee immediate success!"

    review = review_post("twitter", problematic_text, [])

    # Should have issues with suggestions
    assert len(review.issues) > 0, "Should identify issues"

    for issue in review.issues:
        assert issue.suggestion, f"Issue {issue.rule_id} should have a suggestion"
        assert len(issue.suggestion) > 10, "Suggestions should be meaningful"
