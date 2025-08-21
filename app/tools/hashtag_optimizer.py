"""
Hashtag optimization for improved targeting and engagement.

This module implements intelligent hashtag optimization to improve content discoverability
and engagement while avoiding overused generic tags. It applies platform-specific
strategies and content analysis to generate targeted hashtag recommendations.

Key features:
- Removal of generic overused hashtags that provide little value
- Content-based keyword extraction for targeted hashtag generation
- Platform-specific optimization strategies and limits
- Topic-aware hashtag suggestions
- Hashtag prioritization based on specificity and relevance
- Domain-specific hashtag generation for various industries

Why hashtag optimization matters:
- Generic hashtags are oversaturated and provide poor reach
- Platform algorithms favor specific, relevant hashtags
- Different platforms have different hashtag best practices
- Targeted hashtags reach more engaged audiences
- Proper hashtag strategy improves content discoverability
"""

from typing import Dict, List, Set
import re
from app.models import Platform, PlatformPost


def optimize_hashtags(platform_posts: Dict[Platform, PlatformPost], topic_hint: str = "") -> Dict[Platform, List[str]]:
    """
    Optimize hashtags for better targeting and reduced generic usage.
    
    This function processes hashtags across all platform posts to remove generic
    overused tags and replace them with more targeted, content-specific options
    that are likely to improve engagement and reach.
    
    Why hashtag optimization is needed:
    - Generic hashtags like #ai, #tech are oversaturated with millions of posts
    - Platform algorithms favor specific, relevant hashtags over generic ones
    - Targeted hashtags reach more engaged, interested audiences
    - Different platforms have different hashtag limits and best practices
    
    Args:
        platform_posts: Dictionary mapping platforms to their respective posts
        topic_hint: Optional context hint to improve hashtag relevance
        
    Returns:
        Dictionary of optimized hashtags per platform with generic tags removed
        and targeted alternatives added based on content analysis
    """
    optimized_hashtags = {}
    
    for platform, post in platform_posts.items():
        current_hashtags = post.hashtags
        optimized = _optimize_platform_hashtags(platform, current_hashtags, post.primary_text, topic_hint)
        optimized_hashtags[platform] = optimized
        
    return optimized_hashtags


def _optimize_platform_hashtags(platform: Platform, current_hashtags: List[str], 
                               content: str, topic_hint: str) -> List[str]:
    """Optimize hashtags for a specific platform."""
    
    # Remove generic overloaded hashtags
    generic_hashtags = {
        "#ai", "#tech", "#technology", "#business", "#innovation", "#digital",
        "#future", "#trends", "#news", "#social", "#marketing", "#content"
    }
    
    # Filter out generic hashtags
    filtered_hashtags = [tag for tag in current_hashtags if tag.lower() not in generic_hashtags]
    
    # Add platform-specific targeted hashtags based on content analysis
    content_keywords = _extract_content_keywords(content)
    targeted_hashtags = _generate_targeted_hashtags(platform, content_keywords, topic_hint)
    
    # Combine and deduplicate
    combined_hashtags = list(set(filtered_hashtags + targeted_hashtags))
    
    # Apply platform limits and prioritize by specificity
    if platform == "twitter":
        return _prioritize_hashtags(combined_hashtags, max_count=3)
    elif platform == "linkedin":
        return _prioritize_hashtags(combined_hashtags, max_count=5)
    elif platform == "instagram":
        return _prioritize_hashtags(combined_hashtags, max_count=10)
    
    return combined_hashtags[:5]


def _extract_content_keywords(content: str) -> Set[str]:
    """Extract meaningful keywords from content."""
    # Remove common words and extract meaningful terms
    stop_words = {"the", "and", "for", "are", "with", "will", "can", "this", "that", "from", "have"}
    
    # Extract words that could be hashtag candidates (3+ chars, alphanumeric)
    words = re.findall(r'\b[a-zA-Z]{3,}\b', content.lower())
    keywords = {word for word in words if word not in stop_words and len(word) > 3}
    
    return keywords


def _generate_targeted_hashtags(platform: Platform, keywords: Set[str], topic_hint: str) -> List[str]:
    """Generate platform-specific targeted hashtags."""
    targeted = []
    
    # Domain-specific hashtag mapping
    domain_hashtags = {
        "healthcare": ["#HealthTech", "#MedicalAI", "#DigitalHealth", "#PatientCare"],
        "travel": ["#TravelTech", "#Tourism", "#Wanderlust", "#TravelGuide"],
        "sustainability": ["#GreenTech", "#SustainableBusiness", "#ClimateAction", "#EcoFriendly"],
        "remote work": ["#RemoteWork", "#WorkFromHome", "#DigitalNomad", "#FutureOfWork"],
        "fintech": ["#FinTech", "#DigitalPayments", "#BlockChain", "#FinancialServices"]
    }
    
    # Add domain-specific hashtags based on topic hint
    topic_lower = topic_hint.lower()
    for domain, hashtags in domain_hashtags.items():
        if domain in topic_lower:
            targeted.extend(hashtags[:2])  # Add top 2 domain hashtags
    
    # Generate hashtags from keywords (most relevant ones)
    keyword_hashtags = []
    for keyword in list(keywords)[:5]:  # Top 5 keywords
        if len(keyword) >= 4 and len(keyword) <= 15:  # Good hashtag length
            hashtag = f"#{keyword.capitalize()}"
            if hashtag not in keyword_hashtags:
                keyword_hashtags.append(hashtag)
    
    targeted.extend(keyword_hashtags[:3])  # Add top 3 keyword hashtags
    
    # Platform-specific optimization
    if platform == "linkedin":
        # LinkedIn prefers professional hashtags
        professional_tags = ["#Professional", "#Industry", "#Leadership", "#Strategy"]
        targeted.extend([tag for tag in professional_tags if tag not in targeted][:2])
    elif platform == "instagram":
        # Instagram benefits from trending and visual hashtags
        visual_tags = ["#Inspiration", "#Community", "#Growth", "#Success"]
        targeted.extend([tag for tag in visual_tags if tag not in targeted][:2])
    
    return targeted


def _prioritize_hashtags(hashtags: List[str], max_count: int) -> List[str]:
    """Prioritize hashtags by specificity and relevance."""
    
    # Scoring function: longer, more specific hashtags get higher scores
    def score_hashtag(hashtag: str) -> float:
        base_score = len(hashtag) / 20  # Length score
        
        # Bonus for compound words (CamelCase)
        if re.search(r'[A-Z][a-z]+[A-Z]', hashtag):
            base_score += 0.3
            
        # Bonus for numbers (specific data/years)
        if re.search(r'\d+', hashtag):
            base_score += 0.2
            
        # Penalty for very common patterns
        common_patterns = ["Tech", "Digital", "Future", "Smart"]
        if any(pattern in hashtag for pattern in common_patterns):
            base_score -= 0.1
            
        return base_score
    
    # Sort by score (descending) and return top hashtags
    scored_hashtags = [(hashtag, score_hashtag(hashtag)) for hashtag in hashtags]
    scored_hashtags.sort(key=lambda x: x[1], reverse=True)
    
    return [hashtag for hashtag, _ in scored_hashtags[:max_count]]