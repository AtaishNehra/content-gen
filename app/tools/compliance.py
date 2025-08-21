"""
Compliance review functionality with configurable rule sets.

This module implements content compliance checking to ensure generated social media posts
meet organizational policies and regulatory requirements. It provides a flexible rule-based
system that can be configured for different compliance modes and industries.

Key features:
- Configurable rule sets for different compliance levels
- Support for standard vs strict compliance modes
- Industry-specific restrictions (healthcare, finance)
- Graduated response system (warn, flag, block)
- Automatic remediation suggestions for common issues

Why compliance matters:
- Prevents legal issues from problematic content
- Maintains brand reputation and trust
- Supports regulatory requirements in regulated industries
- Enables content review workflows for sensitive organizations
"""

from typing import List

from ..config import config
from ..models import Claim, ComplianceIssue, Platform, PostReview

# Basic profanity detection list
# This is a simplified list for demonstration - production systems should use
# more comprehensive profanity detection libraries or services
# These words are flagged as unprofessional for business content
PROFANITY_WORDS = {
    "damn",
    "hell",
    "crap",
    "stupid",
    "idiot",
    "hate",
    # Add more as needed for your organization's standards
}

# Absolute claim phrases that should be avoided in marketing content
# These phrases can create legal liability by making guarantees
# that cannot be backed up or may violate advertising standards
ABSOLUTE_PHRASES = {
    "guarantee",
    "guaranteed",
    "100%",
    "always works",
    "never fails",
    "instant results",
    "immediate",
}

# Additional restrictions for strict compliance mode
# These are typically used in regulated industries like healthcare/finance
# where specific terminology can have legal implications
STRICT_RESTRICTED = {
    "cure",
    "cures",
    "diagnose",
    "diagnosis",
    "treatment",
    "financial advice",
    "returns",
    "roi",
    "profit guaranteed",
    "investment",
}


def review_post(platform: Platform, text: str, claims: List[Claim]) -> PostReview:
    """
    Review a platform post for compliance issues.

    Args:
        platform: Target platform
        text: Post text content
        claims: List of factual claims in the post

    Returns:
        PostReview with status and identified issues
    """
    issues = []

    # Check for profanity
    issues.extend(_check_profanity(text))

    # Check for absolute claims
    issues.extend(_check_absolute_claims(text))

    # Check claim confidence
    issues.extend(_check_claim_confidence(claims))

    # Strict mode additional checks
    if config.COMPLIANCE_MODE == "strict":
        issues.extend(_check_strict_mode(text))

    # Determine overall status
    status = _determine_status(issues)

    return PostReview(status=status, issues=issues, claims=claims)


def _check_profanity(text: str) -> List[ComplianceIssue]:
    """Check for profanity in text."""
    issues = []
    text_lower = text.lower()

    for word in PROFANITY_WORDS:
        if word in text_lower:
            issues.append(
                ComplianceIssue(
                    rule_id="profanity_check",
                    severity="minor",
                    message=f"Potential profanity detected: '{word}'",
                    suggestion=f"Consider replacing '{word}' with a more professional alternative",
                )
            )

    return issues


def _check_absolute_claims(text: str) -> List[ComplianceIssue]:
    """Check for absolute guarantee claims."""
    issues = []
    text_lower = text.lower()

    for phrase in ABSOLUTE_PHRASES:
        if phrase in text_lower:
            issues.append(
                ComplianceIssue(
                    rule_id="absolute_claims",
                    severity="major",
                    message=f"Absolute claim detected: '{phrase}'",
                    suggestion=f"Soften the claim by replacing '{phrase}' with more qualified language like 'may help' or 'typically'",
                )
            )

    return issues


def _check_claim_confidence(claims: List[Claim]) -> List[ComplianceIssue]:
    """Check for low-confidence claims with tiered severity."""
    issues = []

    for claim in claims:
        confidence = claim.confidence
        severity = claim.severity
        
        # More nuanced confidence thresholds
        if severity == "high":
            if confidence < 0.3:
                # Very low confidence - major issue
                issues.append(
                    ComplianceIssue(
                        rule_id="low_confidence_claim",
                        severity="major",
                        message=f"Low confidence claim: '{claim.text}' (confidence: {confidence:.2f})",
                        suggestion="Add a reliable source or soften the claim with qualifying language",
                    )
                )
            elif confidence < 0.5 and not claim.sources:
                # Medium confidence but no sources - minor issue
                issues.append(
                    ComplianceIssue(
                        rule_id="unsourced_claim",
                        severity="minor", 
                        message=f"Medium confidence claim without sources: '{claim.text}' (confidence: {confidence:.2f})",
                        suggestion="Consider adding supporting sources to strengthen the claim",
                    )
                )
            elif confidence < 0.6 and claim.sources and len(claim.sources) >= 2:
                # Medium confidence with multiple sources - just informational
                issues.append(
                    ComplianceIssue(
                        rule_id="attribution_note",
                        severity="minor",
                        message=f"Attribution available: '{claim.text}' (confidence: {confidence:.2f})",
                        suggestion="Claim has supporting sources with partial verification",
                    )
                )
        elif severity == "medium":
            if confidence < 0.25:
                # Very low confidence for medium claims
                issues.append(
                    ComplianceIssue(
                        rule_id="low_confidence_claim",
                        severity="minor",
                        message=f"Low confidence claim: '{claim.text}' (confidence: {confidence:.2f})",
                        suggestion="Consider adding supporting sources",
                    )
                )

    return issues


def _check_strict_mode(text: str) -> List[ComplianceIssue]:
    """Additional checks for strict compliance mode."""
    issues = []
    text_lower = text.lower()

    for word in STRICT_RESTRICTED:
        if word in text_lower:
            issues.append(
                ComplianceIssue(
                    rule_id="strict_mode_restricted",
                    severity="critical",
                    message=f"Restricted term in strict mode: '{word}'",
                    suggestion=f"Remove or replace '{word}' to avoid potential regulatory issues",
                )
            )

    return issues


def _determine_status(issues: List[ComplianceIssue]) -> str:
    """Determine overall review status based on issues."""
    if not issues:
        return "pass"

    # Check for critical issues (block)
    if any(issue.severity == "critical" for issue in issues):
        return "block"

    # Check for major issues (flag)
    if any(issue.severity == "major" for issue in issues):
        return "flag"

    # Only minor issues (pass)
    return "pass"
