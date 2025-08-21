"""
LangGraph workflow orchestration for content processing.

This module implements the core workflow orchestration using LangGraph to manage
the complex multi-step content processing pipeline. It coordinates all the different
analysis and generation steps while maintaining proper error handling and state management.

Key components:
- Multi-step workflow orchestration with LangGraph
- State management for complex data flow between nodes
- Error handling and graceful degradation
- Brand mention validation for safe social media posting
- JSON parsing utilities for LLM response processing
- Comprehensive workflow nodes for each processing step

Why use LangGraph for orchestration:
- Provides clear workflow visualization and debugging
- Enables complex conditional logic and branching
- Supports parallel processing of independent steps
- Maintains proper state management across workflow nodes
- Allows easy modification and extension of workflow logic
- Provides built-in error handling and retry mechanisms
"""

import json
import re
from typing import Any, Dict, List

# Handle optional dependencies with graceful fallbacks for testing
# This ensures the application can run in different environments
try:
    from langchain_openai import ChatOpenAI
    from langgraph.graph import END, StateGraph
except ImportError as e:
    print(f"Import error: {e}")
    # Fallback classes for testing environments without LangChain/LangGraph
    class ChatOpenAI:
        def __init__(self, **kwargs): pass
        def invoke(self, prompt): 
            class Response:
                content = '{"text": "test", "importance": 0.5}'
            return Response()
    
    class StateGraph:
        def __init__(self, state_type): pass
        def add_node(self, name, func): pass
        def set_entry_point(self, name): pass
        def add_edge(self, from_node, to_node): pass
        def compile(self): return self
        def invoke(self, state): return state
    
    END = "END"

from .config import config
from .models import Claim, KeyPoint, Platform, PlatformPost, State
from .prompts import CLAIM_EXTRACT_PROMPT, EDIT_SUGGESTIONS_PROMPT, KEYPOINTS_PROMPT, PLATFORM_PROMPT
from .tools.compliance import review_post
from .tools.factcheck import verify_claims
from .tools.schedule import suggest_times
from .tools.embeddings import analyze_content_embeddings


def _validate_brand_mentions(mentions: List[str]) -> List[str]:
    """
    Validate brand mentions and convert unverified handles to plain text.
    
    This function ensures social media posts only include verified brand handles
    to avoid tagging issues, brand impersonation, or mentioning non-existent accounts.
    Unverified handles are converted to plain text mentions for safety.
    
    Why brand mention validation is critical:
    - Prevents tagging non-existent or unverified social media accounts
    - Avoids brand impersonation issues that could cause legal problems
    - Ensures mentions reach the intended organizations
    - Maintains professional credibility by avoiding broken tags
    - Supports compliance with social media platform policies
    
    Args:
        mentions: List of brand mentions (with or without @ symbols)
        
    Returns:
        List of validated mentions with verified handles preserved as-is
        and unverified handles converted to plain text
    """
    # Allowlisted verified handles that are safe to mention
    # These are confirmed active accounts for major organizations
    # Regular maintenance needed to keep this list current
    verified_handles = {
        '@deloitte': 'Deloitte',
        '@fda': 'FDA', 
        '@who': 'WHO',
        '@cdc': 'CDC',
        '@gartner_inc': 'Gartner',
        '@bookingcom': 'Booking.com',
        '@buffer': 'Buffer',
        '@statista': 'Statista',
        # Add more verified handles as needed
    }
    
    validated = []
    for mention in mentions:
        mention_lower = mention.lower().strip()
        
        # If it's a verified handle, keep it as-is for tagging
        if mention_lower in verified_handles:
            validated.append(mention)
        # If it starts with @ but isn't verified, convert to safe plain text
        elif mention.startswith('@'):
            brand_name = verified_handles.get(mention_lower, mention[1:].title())
            validated.append(brand_name)
        else:
            # Keep plain text mentions as-is (already safe)
            validated.append(mention)
    
    return validated


def _parse_json(text: str) -> Any:
    """
    Extract and parse the last JSON block from text.

    Args:
        text: Text that may contain JSON

    Returns:
        Parsed JSON object or None if parsing fails
    """
    try:
        # Try to find JSON blocks in the text
        json_pattern = r'\{.*\}|\[.*\]'
        matches = re.findall(json_pattern, text, re.DOTALL)
        
        if matches:
            # Try the last (most complete) JSON block
            return json.loads(matches[-1])
        
        # If no JSON blocks found, try parsing the entire text
        return json.loads(text.strip())
    
    except (json.JSONDecodeError, IndexError) as e:
        print(f"JSON parsing failed: {e}")
        print(f"Text was: {text[:200]}...")
        return None


def extract_key_points(state: State) -> State:
    """
    Extract key points from blog text using OpenAI.

    Args:
        state: Current workflow state

    Returns:
        Updated state with key_points populated
    """
    import openai
    
    try:
        # Ensure we have text to process
        blog_text = state.get("text", "")
        if not blog_text:
            state["errors"].append("No text provided for key point extraction")
            state["key_points"] = []
            return state
        
        # Use direct OpenAI API call to avoid LangChain issues
        client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
        
        prompt = f"""Extract 5-8 key bullet points from the blog text below. Preserve numbers, dates, entities. No marketing fluff.

Return JSON array of objects with this exact format:
[
    {{"text": "specific key point", "importance": 0.8}},
    {{"text": "another key point", "importance": 0.6}}
]

Importance should be a float between 0 and 1, where 1 is most important.

Do not include any prose or explanation outside the JSON array.

Blog text:
{blog_text.strip()}"""
        
        print(f"Sending key points request, text length: {len(blog_text)}")
        
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        
        content = response.choices[0].message.content
        print(f"Key points response: {content[:200]}...")
        
        parsed = _parse_json(content)
        if parsed and isinstance(parsed, list) and len(parsed) > 0:
            key_points = []
            for item in parsed:
                if isinstance(item, dict) and "text" in item:
                    # Ensure importance is a valid float
                    importance = item.get("importance", 0.5)
                    if not isinstance(importance, (int, float)):
                        importance = 0.5
                    importance = max(0.0, min(1.0, float(importance)))
                    
                    key_points.append(KeyPoint(
                        text=str(item.get("text", "")).strip(),
                        importance=importance
                    ))
            
            if key_points:
                state["key_points"] = key_points
                print(f"Successfully extracted {len(key_points)} key points")
            else:
                state["errors"].append("No valid key points found in parsed response")
                state["key_points"] = []
        else:
            state["errors"].append(f"Failed to parse key points from response: {content[:100]}...")
            state["key_points"] = []
            
    except Exception as e:
        state["errors"].append(f"Key points extraction failed: {str(e)}")
        state["key_points"] = []
        print(f"Key point extraction error: {e}")
    
    return state


def generate_posts(state: State) -> State:
    """
    Generate platform-specific posts from key points or original content.

    Args:
        state: Current workflow state

    Returns:
        Updated state with drafts populated
    """
    # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
    # do not change this unless explicitly requested by the user
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3, api_key=config.OPENAI_API_KEY)
    
    platforms: List[Platform] = ["twitter", "linkedin", "instagram"]
    state["drafts"] = {}
    
    # Use key points if available, otherwise use original text for content generation
    if state["key_points"]:
        key_points_text = "\n".join([
            f"- {kp.text} (importance: {kp.importance})"
            for kp in state["key_points"]
        ])
        content_source = f"Key insights:\n{key_points_text}"
    else:
        # Fallback to original text with instruction to extract insights
        original_text = state.get("text", "")[:1000]  # Limit length for prompt
        content_source = f"Original blog content (extract key insights):\n{original_text}"
    
    for platform in platforms:
        try:
            prompt = PLATFORM_PROMPT.format(
                platform=platform,
                key_points=content_source,
                topic_hint=state.get("topic_hint", "")
            )
            
            response = llm.invoke(prompt)
            content = getattr(response, 'content', str(response)) or "" or ""
            print(f"{platform} post response: {content[:150]}...")
            
            parsed = _parse_json(content)
            
            if parsed and isinstance(parsed, dict):
                # Validate and filter mentions to avoid unverified handles
                raw_mentions = parsed.get("mentions", [])
                validated_mentions = _validate_brand_mentions(raw_mentions)
                
                post = PlatformPost(
                    platform=platform,
                    primary_text=parsed.get("primary_text", ""),
                    thread=parsed.get("thread"),
                    hashtags=parsed.get("hashtags", []),
                    mentions=validated_mentions,
                    notes=None,
                    metadata=None
                )
                state["drafts"][platform] = post
                print(f"Generated {platform} post: {len(post.primary_text)} chars")
            else:
                state["errors"].append(f"Failed to parse {platform} post: {content[:100]}...")
                
        except Exception as e:
            state["errors"].append(f"{platform} post generation failed: {str(e)}")
            print(f"Error generating {platform} post: {e}")
    
    return state


def extract_claims(state: State) -> State:
    """
    Extract factual claims from original blog and generated posts.

    Args:
        state: Current workflow state

    Returns:
        Updated state with claims populated
    """
    # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
    # do not change this unless explicitly requested by the user
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3, api_key=config.OPENAI_API_KEY)
    
    state["claims"] = {}
    original_text = state.get("text", "")
    
    for platform, post in state["drafts"].items():
        try:
            prompt = CLAIM_EXTRACT_PROMPT.format(
                original_text=original_text,
                post_text=post.primary_text
            )
            response = llm.invoke(prompt)
            
            parsed = _parse_json(response.content)
            if parsed and isinstance(parsed, list):
                claims = [
                    Claim(
                        text=item.get("text", ""),
                        severity=item.get("severity", "low")
                    )
                    for item in parsed
                    if isinstance(item, dict) and "text" in item
                ]
                state["claims"][platform] = claims
            else:
                state["claims"][platform] = []
                
        except Exception as e:
            state["errors"].append(f"Claim extraction failed for {platform}: {str(e)}")
            state["claims"][platform] = []
    
    return state


def fact_check(state: State) -> State:
    """
    Verify extracted claims using configured fact-check provider.

    Args:
        state: Current workflow state

    Returns:
        Updated state with verified claims
    """
    # Aggregate all claims for unified fact-checking to ensure consistency
    all_claims = []
    platform_claim_map = {}
    
    for platform, claims in state["claims"].items():
        platform_claim_map[platform] = len(all_claims)
        all_claims.extend(claims)
    
    try:
        # Fact-check all claims together 
        verified_claims = verify_claims(all_claims)
        
        # Redistribute verified claims back to platforms
        for platform in state["claims"].keys():
            start_idx = platform_claim_map[platform]
            end_idx = start_idx + len(state["claims"][platform])
            state["claims"][platform] = verified_claims[start_idx:end_idx]
            
    except Exception as e:
        state["errors"].append(f"Unified fact-checking failed: {str(e)}")
    
    return state


def compliance(state: State) -> State:
    """
    Review posts for compliance issues.

    Args:
        state: Current workflow state

    Returns:
        Updated state with reviews populated
    """
    state["reviews"] = {}
    
    for platform, post in state["drafts"].items():
        try:
            claims = state["claims"].get(platform, [])
            review = review_post(platform, post.primary_text, claims)
            state["reviews"][platform] = review
        except Exception as e:
            state["errors"].append(f"Compliance review failed for {platform}: {str(e)}")
    
    return state


def remediate_if_blocked(state: State) -> State:
    """
    Attempt to fix posts that are blocked by compliance issues.

    Args:
        state: Current workflow state

    Returns:
        Updated state with remediated posts
    """
    # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
    # do not change this unless explicitly requested by the user
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3, api_key=config.OPENAI_API_KEY)
    
    for platform, review in state["reviews"].items():
        if review.status == "block":
            try:
                post = state["drafts"][platform]
                issues_text = "\n".join([
                    f"- {issue.message}: {issue.suggestion}"
                    for issue in review.issues
                ])
                
                prompt = EDIT_SUGGESTIONS_PROMPT.format(
                    issues=issues_text,
                    post_text=post.primary_text
                )
                
                response = llm.invoke(prompt)
                revised_text = response.content.strip()
                
                # Update the post with revised text
                post.primary_text = revised_text
                post.notes = "Automatically revised for compliance"
                
                # Re-review the revised post
                claims = state["claims"].get(platform, [])
                new_review = review_post(platform, revised_text, claims)
                state["reviews"][platform] = new_review
                
            except Exception as e:
                state["errors"].append(f"Remediation failed for {platform}: {str(e)}")
    
    return state


def analyze_embeddings(state: State) -> State:
    """
    Perform embedding-based content analysis for similarity and quality scoring.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with embedding analysis results
    """
    try:
        original_text = state.get("text", "")
        key_points = state.get("key_points", [])
        platform_posts = state.get("drafts", {})
        
        if not original_text or not platform_posts:
            state["embedding_analysis"] = {"error": "Insufficient content for analysis"}
            return state
        
        # Convert platform posts to string keys for embeddings analysis
        string_key_posts = {str(platform): post for platform, post in platform_posts.items()}
        
        # Perform comprehensive embedding analysis
        analysis_results = analyze_content_embeddings(original_text, key_points, string_key_posts)
        state["embedding_analysis"] = analysis_results
        
        # Add quality insights to individual posts
        if "quality_scores" in analysis_results:
            for platform, post in state.get("drafts", {}).items():
                if platform in analysis_results["quality_scores"]:
                    # Add quality metadata to post
                    quality_score = analysis_results["quality_scores"][platform]
                    post.metadata = post.metadata or {}
                    post.metadata["quality_score"] = quality_score.get("overall_quality", 0.5)
                    post.metadata["content_density"] = quality_score.get("content_density", 0.5)
                    post.metadata["semantic_coherence"] = quality_score.get("semantic_coherence", 0.5)
        
    except Exception as e:
        state["errors"].append(f"Embedding analysis failed: {str(e)}")
        state["embedding_analysis"] = {"error": str(e)}
    
    return state


def schedule(state: State) -> State:
    """
    Generate context-aware optimal posting time suggestions.

    Args:
        state: Current workflow state

    Returns:
        Updated state with timings populated
    """
    try:
        platforms = list(state["drafts"].keys())
        content_text = state.get("text", "")
        topic_hint = state.get("topic_hint", "") or ""
        
        # Use enhanced scheduling with content context
        timings = suggest_times(platforms, content_text, topic_hint)
        state["timings"] = timings
    except Exception as e:
        state["errors"].append(f"Context-aware scheduling failed: {str(e)}")
        state["timings"] = []
    
    return state


def build_graph() -> StateGraph:
    """
    Build and compile the LangGraph workflow.

    Returns:
        Compiled StateGraph for content processing
    """
    # Create workflow graph
    workflow = StateGraph(State)
    
    # Add nodes
    workflow.add_node("extract_key_points", extract_key_points)
    workflow.add_node("generate_posts", generate_posts)
    workflow.add_node("analyze_embeddings", analyze_embeddings)
    workflow.add_node("extract_claims", extract_claims)
    workflow.add_node("fact_check", fact_check)
    workflow.add_node("compliance", compliance)
    workflow.add_node("remediate_if_blocked", remediate_if_blocked)
    workflow.add_node("schedule", schedule)
    
    # Set entry point
    workflow.set_entry_point("extract_key_points")
    
    # Add edges in sequence
    workflow.add_edge("extract_key_points", "generate_posts")
    workflow.add_edge("generate_posts", "analyze_embeddings")
    workflow.add_edge("analyze_embeddings", "extract_claims")
    workflow.add_edge("extract_claims", "fact_check")
    workflow.add_edge("fact_check", "compliance")
    workflow.add_edge("compliance", "remediate_if_blocked")
    workflow.add_edge("remediate_if_blocked", "schedule")
    workflow.add_edge("schedule", END)
    
    # Compile and return
    return workflow.compile()
