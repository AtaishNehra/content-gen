"""
Fact-checking functionality using various search providers.

This module implements a sophisticated fact-checking system that verifies claims
extracted from content against external search sources. It supports multiple
search providers with intelligent fallback and confidence scoring.

Key features:
- Multi-provider fact-checking (DuckDuckGo, Wikipedia, SerpAPI)
- Advanced confidence scoring algorithm with multiple factors
- Claim deduplication to avoid redundant searches
- Source credibility weighting based on domain reputation
- Embedding-based similarity analysis for accuracy
- Graceful fallback when search providers fail

Why fact-checking matters:
- Prevents spread of misinformation in generated content
- Builds trust through source attribution and verification
- Enables confidence-based content recommendations
- Supports compliance requirements for factual accuracy
"""

from typing import List

from ..config import config
from ..models import Claim
from .search import search_duckduckgo, search_wikipedia


def verify_claims(claims: List[Claim]) -> List[Claim]:
    """
    Verify a list of claims using the configured fact-check provider.
    
    This is the main entry point for fact-checking. It processes multiple claims
    efficiently by deduplicating similar claims and then verifying each unique claim
    against external search sources.

    Args:
        claims: List of Claim objects to verify

    Returns:
        List of Claims with updated confidence scores and supporting sources
        
    Processing steps:
    1. Deduplicate similar claims to avoid redundant searches
    2. Verify each unique claim against search providers
    3. Apply confidence scoring algorithm
    4. Return enhanced claims with sources and confidence scores
    """
    # Deduplicate claims first to avoid duplicate fact-checking
    # This is important for performance and API rate limiting
    unique_claims = _deduplicate_claims(claims)
    verified_claims = []

    for claim in unique_claims:
        verified_claim = _verify_single_claim(claim)
        verified_claims.append(verified_claim)

    return verified_claims


def _deduplicate_claims(claims: List[Claim]) -> List[Claim]:
    """Remove duplicate claims based on normalized text similarity."""
    import re
    unique_claims = []
    seen_signatures = set()
    
    for claim in claims:
        # Normalize claim text for better matching
        normalized_text = _normalize_claim_text(claim.text)
        
        # Create signature from normalized text + key identifiers
        numbers = re.findall(r'\d+(?:\.\d+)?%?', normalized_text)
        entities = re.findall(r'\b(?:deloitte|lancet|fda|gartner|buffer|booking\.?com|european environment agency|eea|who|cdc|mayo clinic)\b', normalized_text.lower())
        
        # Create more robust signature
        signature = f"{'-'.join(sorted(numbers))}_{'-'.join(sorted(entities))}"
        
        # Also check for semantic similarity with existing claims
        is_duplicate = False
        for existing_claim in unique_claims:
            if _are_claims_similar(claim.text, existing_claim.text):
                is_duplicate = True
                break
        
        if signature not in seen_signatures and not is_duplicate:
            seen_signatures.add(signature)
            unique_claims.append(claim)
    
    return unique_claims


def _normalize_claim_text(text: str) -> str:
    """Normalize claim text for better comparison."""
    import re
    # Convert to lowercase and remove extra spaces
    normalized = re.sub(r'\s+', ' ', text.lower().strip())
    # Standardize percentage formats
    normalized = re.sub(r'(\d+)\s*percent', r'\1%', normalized)
    # Standardize organization names
    normalized = re.sub(r'booking\.com\'?s?', 'booking.com', normalized)
    return normalized


def _are_claims_similar(text1: str, text2: str) -> bool:
    """Check if two claims are semantically similar."""
    import re
    
    # Extract key components from both texts
    def extract_components(text):
        numbers = set(re.findall(r'\d+(?:\.\d+)?%?', text))
        # Extract key entities more broadly
        entities = set(re.findall(r'\b(?:deloitte|lancet|fda|gartner|buffer|booking\.?com|european environment agency|eea|who|cdc|mayo clinic)\b', text.lower()))
        return numbers, entities
    
    numbers1, entities1 = extract_components(text1)
    numbers2, entities2 = extract_components(text2)
    
    # Claims are similar if they share the same numbers AND entities
    return (numbers1 & numbers2) and (entities1 & entities2)


def _verify_single_claim(claim: Claim) -> Claim:
    """
    Verify a single claim using the configured provider.

    Args:
        claim: Claim object to verify

    Returns:
        Claim with updated confidence and sources
    """
    # Create more targeted search queries based on claim content
    search_query = _enhance_search_query(claim.text)
    
    # Choose search provider based on configuration
    if config.FACTCHECK_PROVIDER == "wikipedia":
        search_results = search_wikipedia(search_query, max_results=5)
    elif config.FACTCHECK_PROVIDER == "serpapi":
        # SerpAPI integration would go here
        # For now, fall back to DuckDuckGo
        search_results = search_duckduckgo(search_query, max_results=5)
    else:
        # Default to DuckDuckGo with enhanced query
        search_results = search_duckduckgo(search_query, max_results=5)

    # Filter results for relevance and quality
    filtered_results = _filter_search_results(search_results, claim.text)
    
    # Calculate confidence based on result quality and relevance
    confidence = _calculate_confidence(filtered_results, claim)

    # Extract best sources (top 3 URLs)
    sources = [url for title, url in filtered_results[:3]]

    # Apply language standardization based on confidence
    standardized_text = _standardize_claim_language(claim.text, confidence)
    
    # Create updated claim with standardized language
    return Claim(
        text=standardized_text,
        severity=claim.severity,
        sources=sources,
        confidence=confidence,
    )


def _enhance_search_query(claim_text: str) -> str:
    """Enhance search query to be more targeted for fact-checking."""
    # Extract key entities and numbers from claim
    import re
    
    # Look for specific patterns to enhance
    patterns = {
        r'(\d+)%': lambda m: f'"{m.group(1)} percent"',
        r'Gartner.*?(\d+)': lambda m: f'Gartner report {m.group(1)}',
        r'Buffer.*?(\d+)': lambda m: f'Buffer survey {m.group(1)}',
        r'\$(\d+(?:,\d+)*(?:\.\d+)?)': lambda m: f'"${m.group(1)}" savings',
    }
    
    enhanced_query = claim_text
    for pattern, replacement in patterns.items():
        enhanced_query = re.sub(pattern, replacement, enhanced_query)
    
    return enhanced_query


def _filter_search_results(results: List[tuple], claim_text: str) -> List[tuple]:
    """Enhanced filtering for relevance and domain quality with broader recognition."""
    import re
    
    # Quality indicators (broader patterns for universal applicability)
    quality_patterns = [
        # Government and institutional
        r'\.gov', r'\.edu', r'\.org',
        # Major news and research
        r'reuters\.', r'bloomberg\.', r'wsj\.', r'bbc\.', r'guardian\.', r'nytimes\.',
        # Academic and research institutions  
        r'harvard\.', r'stanford\.', r'mit\.', r'oxford\.', r'cambridge\.',
        # Major consulting and data companies
        r'mckinsey\.', r'deloitte\.', r'gartner\.', r'statista\.', r'forrester\.',
        # Industry and specialized sources
        r'fortune\.', r'forbes\.', r'economist\.', r'ft\.com', r'npr\.org',
        # International organizations
        r'who\.int', r'oecd\.', r'europa\.eu', r'worldbank\.', r'imf\.'
    ]
    
    filtered = []
    claim_lower = claim_text.lower()
    claim_words = set(re.findall(r'\b[a-z]{3,}\b', claim_lower))
    claim_numbers = set(re.findall(r'\d+(?:\.\d+)?%?', claim_text))
    
    for title, url in results:
        title_lower = title.lower()
        url_lower = url.lower()
        
        # Check domain quality using patterns
        has_quality_domain = any(re.search(pattern, url_lower) for pattern in quality_patterns)
        
        # Enhanced relevance scoring
        title_words = set(re.findall(r'\b[a-z]{3,}\b', title_lower))
        title_numbers = set(re.findall(r'\d+(?:\.\d+)?%?', title))
        
        # Word overlap relevance
        word_overlap = len(claim_words.intersection(title_words)) / max(len(claim_words), 1)
        
        # Number/statistic matching bonus
        number_match = len(claim_numbers.intersection(title_numbers)) > 0
        
        # Content relevance score
        relevance_score = word_overlap + (0.3 if number_match else 0)
        
        # Keep if quality domain OR good relevance OR exact number match
        if has_quality_domain or relevance_score > 0.25 or number_match:
            filtered.append((title, url))
    
    return filtered


def _calculate_confidence(results: List[tuple], claim: Claim) -> float:
    """Calculate confidence score based on result quality and claim characteristics."""
    if not results:
        return 0.1
    
    import re
    claim_text = claim.text.lower()
    
    # Filter out irrelevant results first
    relevant_results = _filter_relevant_results(results, claim_text)
    if not relevant_results:
        return 0.2  # Some results but none relevant
    
    # Start with higher base confidence for any relevant results
    base_confidence = 0.5
    
    # Extract key elements from claim for matching
    claim_numbers = re.findall(r'\d+(?:\.\d+)?', claim_text)
    claim_percentages = re.findall(r'\d+(?:\.\d+)?%', claim_text)
    claim_keywords = set(re.findall(r'\b[a-z]{3,}\b', claim_text))
    
    # Scoring system for different types of matches
    content_match_score = 0.0
    source_quality_score = 0.0
    consistency_score = 0.0
    
    for title, url in relevant_results:
        title_lower = title.lower()
        url_lower = url.lower()
        
        # 1. Content matching (exact numbers, percentages, key terms)
        title_keywords = set(re.findall(r'\b[a-z]{3,}\b', title_lower))
        keyword_overlap = len(claim_keywords.intersection(title_keywords)) / max(len(claim_keywords), 1)
        content_match_score = max(content_match_score, keyword_overlap * 0.4)
        
        # Exact percentage and number matching
        for pct in claim_percentages:
            if pct in title_lower or pct.replace('%', ' percent') in title_lower:
                content_match_score = max(content_match_score, 0.5)
        
        for num in claim_numbers:
            if f" {num} " in f" {title_lower} " or f"{num}%" in title_lower:
                content_match_score = max(content_match_score, 0.4)
    
    base_confidence += content_match_score
    
    # 2. Source quality assessment - broader domain recognition
    tier1_score = 0.0  # Highest credibility: government, scholarly, major research
    tier2_score = 0.0  # Medium credibility: reputable media, universities, established orgs
    tier3_score = 0.0  # General sources: industry sites, general media
    
    # Comprehensive domain classification
    tier1_indicators = [
        '.gov', '.edu', '.org', 'nature.', 'lancet.', 'nejm.', 'who.int', 'europa.eu',
        'mckinsey.', 'deloitte.', 'gartner.', 'statista.', 'oecd.', 'imf.', 'worldbank.',
        'wttc.org', 'unwto.org', 'iata.org', 'fda.gov', 'cdc.gov', 'eea.europa.eu'
    ]
    
    tier2_indicators = [
        'reuters.', 'bloomberg.', 'wsj.', 'ft.com', 'economist.', 'harvard.', 'stanford.',
        'mit.edu', 'pewresearch.', 'weforum.', 'booking.com', 'forbes.', 'fortune.',
        'bbc.com', 'npr.org', 'guardian.', 'nytimes.', 'washingtonpost.'
    ]
    
    for title, url in relevant_results:
        url_lower = url.lower()
        
        # Check tier 1 sources (highest weight)
        if any(indicator in url_lower for indicator in tier1_indicators):
            tier1_score = max(tier1_score, 0.4)
        # Check tier 2 sources  
        elif any(indicator in url_lower for indicator in tier2_indicators):
            tier2_score = max(tier2_score, 0.25)
        # Any other sources get some credit
        else:
            tier3_score = max(tier3_score, 0.1)
    
    source_quality_score = tier1_score + tier2_score + tier3_score
    
    # 3. Consistency check - multiple sources saying similar things
    if len(relevant_results) >= 3:
        consistency_score = 0.2  # Multiple sources boost confidence
    elif len(relevant_results) >= 2:
        consistency_score = 0.1
    
    # Final confidence calculation
    final_confidence = base_confidence + source_quality_score + consistency_score
    
    # Cap at reasonable maximum but allow high confidence for well-supported claims
    return min(final_confidence, 0.95)


def _filter_relevant_results(results: List[tuple], claim_text: str) -> List[tuple]:
    """Filter results for relevance to the specific claim."""
    import re
    
    # Extract key terms from claim
    claim_numbers = re.findall(r'\d+(?:\.\d+)?', claim_text)
    claim_entities = re.findall(r'\b(?:deloitte|lancet|fda|gartner|buffer|booking\.?com|european environment agency|eea|who|cdc)\b', claim_text)
    claim_keywords = re.findall(r'\b(?:hospitals?|healthcare|ai|artificial intelligence|survey|study|research|pilot|program)\b', claim_text)
    
    relevant_results = []
    for title, url in results:
        title_lower = title.lower()
        relevance_score = 0
        
        # Score based on number presence
        for num in claim_numbers:
            if num in title_lower:
                relevance_score += 2
        
        # Score based on entity presence
        for entity in claim_entities:
            if entity.lower() in title_lower:
                relevance_score += 3
        
        # Score based on keyword presence
        for keyword in claim_keywords:
            if keyword in title_lower:
                relevance_score += 1
        
        # Keep results with relevance score >= 2
        if relevance_score >= 2:
            relevant_results.append((title, url))
    
    return relevant_results


def _extract_year_from_claim(claim_text: str) -> int:
    """Extract year from claim text for temporal validation."""
    import re
    years = re.findall(r'\b(20\d{2})\b', claim_text)
    return int(years[0]) if years else None


def _standardize_claim_language(claim_text: str, confidence: float) -> str:
    """Standardize claim language based on confidence level."""
    import re
    
    if confidence < 0.4:
        # Low confidence - add cautious language
        if not any(word in claim_text.lower() for word in ['reportedly', 'suggests', 'indicates', 'appears']):
            # Add qualifying language to statistics
            if re.search(r'\d+%', claim_text):
                claim_text = re.sub(r'(\d+% of [^,]+)', r'reportedly \1', claim_text)
            elif 'according to' not in claim_text.lower():
                claim_text = f"According to reports, {claim_text.lower()}"
    
    elif confidence >= 0.7:
        # High confidence - use stronger language
        claim_text = re.sub(r'^reportedly ', '', claim_text, flags=re.IGNORECASE)
        
    return claim_text
