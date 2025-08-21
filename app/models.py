"""
Pydantic models for data validation and API contracts.

This module defines all the data structures used throughout the Content Workflow Agent.
These models serve multiple purposes:
1. Data validation - ensure all data meets expected formats and constraints
2. API contracts - define clear input/output schemas for REST endpoints
3. Type safety - provide compile-time type checking with mypy
4. Documentation - auto-generate OpenAPI schemas for interactive documentation

All models use Pydantic v2 which provides excellent performance and validation.
"""

from typing import Any, Dict, List, Literal, Optional, TypedDict

from pydantic import BaseModel, Field, validator

# Type alias for supported social media platforms
# Using Literal ensures only valid platforms can be specified at compile time
# This prevents typos and makes adding new platforms explicit
Platform = Literal["twitter", "linkedin", "instagram"]


class KeyPoint(BaseModel):
    """
    A key insight extracted from blog content.
    
    Key points represent the most important information from source content
    that should be highlighted in social media posts. The importance score
    helps prioritize which points to emphasize in limited-character formats.
    
    Why we need importance scoring:
    - Different platforms have different character limits
    - Some insights are more engaging than others
    - Allows smart truncation when space is limited
    """
    
    # The actual text of the key insight, extracted from source content
    text: str = Field(..., description="The key point text")
    
    # Importance score from 0.0 to 1.0, used for prioritization
    # Higher scores indicate more important or engaging content
    # Constraints ensure valid range and prevent invalid values
    importance: float = Field(..., ge=0.0, le=1.0, description="Importance score from 0 to 1")


class PlatformPost(BaseModel):
    """
    Platform-specific social media post with validation.
    
    This model encapsulates all the information needed for a social media post
    on a specific platform. It enforces platform-specific rules (character limits,
    formatting requirements) while providing flexibility for platform features.
    
    Why separate models per platform instead of generic post:
    - Each platform has unique constraints and features
    - Validation can be platform-specific and accurate
    - Type safety prevents mixing platform features incorrectly
    """
    
    # Target platform - determines validation rules and available features
    platform: Platform
    
    # Main post content - this is what users will see first
    # Validation ensures it meets platform-specific character limits
    primary_text: str = Field(..., description="Main post content")
    
    # Optional thread for Twitter - allows longer content via multiple tweets
    # Only applicable to Twitter, null for other platforms
    thread: Optional[List[str]] = Field(None, description="Optional thread for Twitter")
    
    # Hashtags for discovery and categorization
    # Default to empty list so posts can exist without hashtags
    hashtags: List[str] = Field(default_factory=list, description="Relevant hashtags")
    
    # User mentions for engagement and attribution
    # Default to empty list as not all posts need mentions
    mentions: List[str] = Field(default_factory=list, description="User mentions")
    
    # Optional notes for additional context or processing information
    # Useful for reviewers or for tracking generation decisions
    notes: Optional[str] = Field(None, description="Additional notes or context")
    
    # Metadata for quality analysis and performance tracking
    # Can store embedding scores, confidence ratings, etc.
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata for analysis")

    @validator("primary_text")
    def validate_character_limits(cls, v, values):
        """
        Validate platform-specific character limits.
        
        Each social media platform has different character limits and conventions.
        This validator ensures generated content meets platform requirements
        before it's submitted for posting.
        
        Why these specific limits:
        - Twitter: 280 characters is the hard limit
        - LinkedIn: 500-1200 range optimizes for engagement (too short looks lazy, too long reduces engagement)
        - Instagram: 125-2200 range balances caption visibility with detail
        
        Args:
            v: The primary_text value being validated
            values: Dict of other field values (used to check platform)
            
        Returns:
            str: The validated text if it passes all constraints
            
        Raises:
            ValueError: If text doesn't meet platform-specific requirements
        """
        platform = values.get("platform")
        
        # Twitter has a hard character limit enforced by the platform
        if platform == "twitter" and len(v) > 280:
            raise ValueError("Twitter posts must be ≤280 characters")
        
        # LinkedIn posts perform best in the professional range
        # Allow shorter posts but encourage longer professional content
        elif platform == "linkedin" and (len(v) < 100 or len(v) > 1300):
            raise ValueError("LinkedIn posts should be 100-1300 characters")
        
        # Instagram captions have complex visibility rules
        # First 125 characters always visible, beyond 2200 gets truncated
        elif platform == "instagram" and (len(v) < 125 or len(v) > 2200):
            raise ValueError("Instagram posts should be 125-2200 characters")
        
        return v


class Claim(BaseModel):
    """
    A factual claim extracted from content that requires verification.
    
    Claims represent statements that can be fact-checked against external sources.
    The system extracts these from both original content and generated posts to
    ensure accuracy and provide proper attribution.
    
    Why we need claim tracking:
    - Prevents spread of misinformation in generated content
    - Provides audit trail for factual statements
    - Enables automatic source citation and attribution
    - Supports confidence-based content recommendations
    """
    
    # The actual claim text as extracted from content
    # This should be a complete, factual statement that can be verified
    text: str = Field(..., description="The claim text")
    
    # Severity indicates how important it is to verify this claim
    # High severity claims (with specific sources/numbers) get priority in fact-checking
    # Low severity claims (general statements) may not need verification
    severity: Literal["low", "medium", "high"] = Field(
        default="low", description="Claim severity level"
    )
    
    # URLs of sources that support or contradict this claim
    # Populated during fact-checking process by search providers
    sources: List[str] = Field(default_factory=list, description="Supporting source URLs")
    
    # Confidence score from fact-checking algorithm (0.0 = unverified, 1.0 = highly confident)
    # Used to determine if claims need conditional language or source attribution
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Verification confidence")


class ComplianceIssue(BaseModel):
    """
    A compliance issue found in content during review.
    
    Compliance issues represent violations of content policies that need to be
    addressed before publication. These can range from minor style issues to
    critical legal or ethical problems.
    
    Why structured compliance tracking:
    - Provides clear feedback for content improvement
    - Enables automatic remediation suggestions
    - Supports audit trails for regulated industries
    - Allows graduated response based on severity
    """
    
    # Unique identifier for the violated rule (e.g., "profanity_detection", "absolute_claims")
    # Used for tracking, reporting, and debugging rule effectiveness
    rule_id: str = Field(..., description="Unique identifier for the rule")
    
    # Severity determines how the issue should be handled
    # minor: warning only, major: requires attention, critical: blocks publication
    severity: Literal["minor", "major", "critical"] = Field(..., description="Issue severity")
    
    # Human-readable description of what went wrong
    # Helps content reviewers understand the specific problem
    message: str = Field(..., description="Description of the issue")
    
    # Actionable suggestion for how to fix the issue
    # Used by auto-remediation system and human reviewers
    suggestion: str = Field(..., description="Suggested resolution")


class PostReview(BaseModel):
    """
    Complete review results for a platform post.
    
    This model aggregates all analysis results for a single platform post,
    including compliance issues and fact-checking results. It provides a
    single source of truth for the post's readiness for publication.
    
    Why aggregate review results:
    - Single decision point for publication readiness
    - Clear audit trail of all analysis performed
    - Enables graduated response (pass/flag/block)
    - Supports both automated and human review workflows
    """
    
    # Overall status determining what action to take with this post
    # pass: ready for publication, flag: needs human review, block: cannot publish
    status: Literal["pass", "flag", "block"] = Field(..., description="Overall review status")
    
    # List of all compliance issues found during review
    # Empty list indicates no compliance problems detected
    issues: List[ComplianceIssue] = Field(
        default_factory=list, description="Found compliance issues"
    )
    
    # List of all verified factual claims in the post
    # Includes confidence scores and supporting sources
    claims: List[Claim] = Field(default_factory=list, description="Verified claims")


class PostingTime(BaseModel):
    """
    Suggested optimal posting time for a specific platform.
    
    PostingTime recommendations are based on research-driven heuristics that
    consider platform engagement patterns, content type, and audience geography.
    The rationale provides transparency into why this time was chosen.
    
    Why intelligent scheduling matters:
    - Different platforms have different peak engagement times
    - Content type affects optimal timing (breaking news vs evergreen)
    - Audience geography determines relevant timezones
    - Proper spacing prevents platform algorithm penalties
    """
    
    # Target platform for this posting recommendation
    platform: Platform
    
    # ISO 8601 datetime string in the target audience's local timezone
    # Format: "2025-08-21T14:30:00" (no timezone suffix means local)
    local_datetime_iso: str = Field(..., description="ISO datetime string in local timezone")
    
    # Human-readable explanation of why this time was chosen
    # Helps users understand the recommendation and build trust in the system
    rationale: str = Field(..., description="Reasoning for this timing")


class ContentPlan(BaseModel):
    """
    Complete content plan with all analysis results.
    
    This is the main output model that aggregates all workflow results into
    a single comprehensive plan. It contains everything needed to understand,
    review, and execute the content strategy.
    
    Why aggregate all results:
    - Single source of truth for the entire content plan
    - Enables comprehensive review and approval workflows
    - Provides complete audit trail for content decisions
    - Supports both API and UI consumption patterns
    """
    
    # Key insights extracted from the original blog content
    # These form the foundation for all platform-specific adaptations
    key_points: List[KeyPoint] = Field(..., description="Extracted key insights")
    
    # Platform-specific posts ready for publication or review
    # Each post is optimized for its target platform's constraints and audience
    posts: List[PlatformPost] = Field(..., description="Platform-specific posts")
    
    # Review results for each platform post
    # Includes compliance status, fact-checking results, and any issues found
    reviews: Dict[Platform, PostReview] = Field(..., description="Review results per platform")
    
    # Optimal posting times for each platform
    # Based on content analysis, platform research, and audience geography
    timings: List[PostingTime] = Field(..., description="Suggested posting times")


class PlanRequest(BaseModel):
    """
    Request payload for content planning API endpoint.
    
    This model defines the input contract for the main content planning workflow.
    It validates that users provide sufficient content and optional context.
    
    Why minimum length requirement:
    - Ensures enough content for meaningful key point extraction
    - Prevents low-quality inputs that would produce poor results
    - 100 characters is roughly 15-20 words, minimum for coherent content
    """
    
    # Original blog post or article content to be processed
    # Must be substantial enough for meaningful analysis and extraction
    text: str = Field(..., min_length=100, description="Blog post content to process")
    
    # Optional context hint to improve targeting and relevance
    # Examples: "healthcare", "technology", "travel", "finance"
    # Helps with audience detection and platform optimization
    topic_hint: Optional[str] = Field(None, description="Optional topic hint for targeting")


class State(TypedDict):
    """
    State dictionary for LangGraph workflow orchestration.
    
    This TypedDict defines the shape of data that flows between workflow nodes.
    Each node can read from and write to this shared state, enabling complex
    multi-step processing with proper data flow management.
    
    Why use TypedDict instead of regular dict:
    - Provides type safety during development
    - Enables better IDE autocomplete and error detection
    - Documents expected state structure for new developers
    - Compatible with LangGraph's state management system
    """
    
    # Original input content from the user
    text: str
    
    # Optional topic context provided by the user
    topic_hint: Optional[str]
    
    # Key insights extracted from the original content
    # Populated by the extract_key_points node
    key_points: List[KeyPoint]
    
    # Draft posts for each platform before final review
    # Populated by the generate_posts node
    drafts: Dict[Platform, PlatformPost]
    
    # Factual claims extracted from each platform post
    # Populated by the extract_claims node, enhanced by fact_check node
    claims: Dict[Platform, List[Claim]]
    
    # Final review results for each platform post
    # Populated by the compliance node, updated by remediate_if_blocked node
    reviews: Dict[Platform, PostReview]
    
    # Optimal posting times for all platforms
    # Populated by the schedule node
    timings: List[PostingTime]
    
    # Errors and warnings collected during workflow execution
    # Used for debugging and user feedback
    errors: List[str]
    
    # Optional embedding analysis results for content quality assessment
    # Populated by the analyze_embeddings node if enabled
    embedding_analysis: Optional[Dict[str, Any]]
