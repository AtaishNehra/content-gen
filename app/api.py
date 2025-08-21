"""
FastAPI application for Content Workflow Agent.

This module provides the main REST API interface for the Content Workflow Agent.
It exposes endpoints for content processing, health checks, and serves the web UI.
The API is designed to be production-ready with proper error handling, documentation,
and health monitoring capabilities.

Key features:
- RESTful API with automatic OpenAPI documentation
- Comprehensive error handling with user-friendly messages
- Static file serving for web interface
- Health check endpoints for monitoring
- Type-safe request/response validation with Pydantic
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, PlainTextResponse
from datetime import datetime

from .graph import build_graph
from .models import ContentPlan, PlanRequest, State

# Initialize FastAPI application with metadata for OpenAPI documentation
# This creates automatic interactive docs at /docs and /redoc endpoints
app = FastAPI(
    title="Content Workflow Agent",
    description="Convert blog posts to platform-specific social media content",
    version="1.0.0",
)


@app.middleware("http")
async def add_server_header(request, call_next):
    """
    Add custom server header for security and branding.
    
    This middleware replaces the default server header with a generic one
    to avoid revealing specific server technology for security purposes.
    Standard practice for production applications.
    """
    response = await call_next(request)
    response.headers["Server"] = "app"
    return response

# Mount static files for serving the web interface
# This allows serving HTML, CSS, JS files from the static/ directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Build the LangGraph workflow on startup
# This initializes the entire content processing pipeline
# Done once at startup for better performance vs building per request
graph = build_graph()


@app.get("/")
async def web_interface():
    """
    Serve the main web interface.
    
    This endpoint serves the static HTML file that provides the user interface
    for interacting with the Content Workflow Agent. The interface allows users
    to input blog content and receive generated social media posts.
    
    Returns:
        FileResponse: The main HTML interface file
    """
    return FileResponse("static/index.html")


@app.get("/health")
async def health_check() -> str:
    """
    Health check endpoint for monitoring and load balancers.
    
    This endpoint provides a simple way to verify that the application is running
    and responsive. It's used by monitoring systems, load balancers, and deployment
    pipelines to ensure the service is healthy.
    
    Returns:
        str: Simple confirmation message that the service is operational
    """
    return "Content Workflow Agent is running."


@app.post("/v1/plan", response_model=ContentPlan)
async def create_content_plan(request: PlanRequest) -> ContentPlan:
    """
    Create a comprehensive content plan from blog text.
    
    This is the main API endpoint that orchestrates the entire content workflow.
    It takes blog content as input and produces a complete content strategy with
    platform-specific posts, fact-checking results, compliance reviews, and
    optimal posting times.
    
    The workflow includes:
    1. Key point extraction from original content
    2. Platform-specific post generation (Twitter, LinkedIn, Instagram)
    3. Factual claim extraction and verification
    4. Compliance review and content safety checks
    5. Intelligent scheduling recommendations
    6. Optional embedding-based quality analysis

    Args:
        request: PlanRequest containing blog text and optional topic hint
                The text must be at least 100 characters for meaningful processing

    Returns:
        ContentPlan: Complete content strategy including:
        - key_points: Extracted insights with importance scores
        - posts: Platform-optimized social media posts
        - reviews: Compliance status and fact-check results per platform
        - timings: Optimal posting times with rationales

    Raises:
        HTTPException: If processing fails due to:
        - Invalid input (text too short, malformed request)
        - API failures (OpenAI, search providers)
        - Configuration issues (missing API keys)
        - Workflow execution errors
    """
    try:
        # Initialize workflow state with user input and empty containers
        # This state dictionary flows through all workflow nodes
        initial_state: State = {
            "text": request.text,
            "topic_hint": request.topic_hint,
            "key_points": [],          # Populated by extract_key_points node
            "drafts": {},              # Populated by generate_posts node
            "claims": {},              # Populated by extract_claims and fact_check nodes
            "reviews": {},             # Populated by compliance node
            "timings": [],             # Populated by schedule node
            "errors": [],              # Collected throughout workflow for debugging
        }

        # Execute the complete LangGraph workflow
        # This runs all nodes in the defined order with proper error handling
        final_state = graph.invoke(initial_state)

        # Check for critical errors
        if final_state["errors"]:
            print("Workflow errors:", final_state["errors"])

        # Convert state to response model
        content_plan = ContentPlan(
            key_points=final_state["key_points"],
            posts=list(final_state["drafts"].values()),
            reviews=final_state["reviews"],
            timings=final_state["timings"],
        )

        return content_plan

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Content processing failed: {str(e)}")


@app.post("/v1/export", response_class=PlainTextResponse)
async def export_plan_as_text(request: PlanRequest) -> str:
    """Export content plan as formatted text with all details and sources."""
    try:
        # Initialize state
        initial_state: State = {
            "text": request.text,
            "topic_hint": request.topic_hint,
            "key_points": [],
            "drafts": {},
            "claims": {},
            "reviews": {},
            "timings": [],
            "errors": [],
        }

        # Process through workflow with debugging
        print(f"Export: Starting workflow with {len(initial_state['text'])} chars")
        final_state = graph.invoke(initial_state)
        print(f"Export: Workflow completed successfully")
        
        # Generate formatted text report
        return _generate_text_report(final_state, request.text)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


def _generate_text_report(final_state: State, original_content: str) -> str:
    """Generate a comprehensive formatted text report."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report = f"""CONTENT WORKFLOW AGENT - SOCIAL MEDIA CONTENT REPORT
Generated on: {timestamp}
================================================================

ORIGINAL BLOG CONTENT:
================================================================
{original_content}

KEY INSIGHTS EXTRACTED:
================================================================
"""
    
    for i, point in enumerate(final_state["key_points"], 1):
        importance_stars = "★" * int(point.importance * 5)
        report += f"{i}. {point.text}\n"
        report += f"   Importance: {point.importance:.2f} {importance_stars}\n\n"

    report += """
GENERATED SOCIAL MEDIA POSTS:
================================================================
"""
    
    posts = list(final_state["drafts"].values())
    for post in posts:
        platform_name = post.platform.upper()
        review = final_state["reviews"].get(post.platform)
        status = review.status if review else 'unknown'
        status_icon = "✓" if status == 'pass' else "⚠" if status == 'flag' else "✗"
        
        report += f"\n{platform_name} POST {status_icon}:\n"
        report += "-" * (len(platform_name) + 10) + "\n"
        report += f"Content: {post.primary_text}\n"
        report += f"Length: {len(post.primary_text)} characters\n"
        
        if post.hashtags:
            report += f"Hashtags: {' '.join(post.hashtags)}\n"
        if post.mentions:
            report += f"Mentions: {' '.join(post.mentions)}\n"
        
        if post.thread and len(post.thread) > 1:
            report += f"\nThread ({len(post.thread)} tweets):\n"
            for i, tweet in enumerate(post.thread, 1):
                report += f"  {i}. {tweet}\n"
        
        # Add compliance issues if any
        review = final_state["reviews"].get(post.platform)
        if review and review.issues:
            report += "\nCompliance Issues:\n"
            for issue in review.issues:
                report += f"  - {issue.rule_id}: {issue.message}\n"
                if issue.suggestion:
                    report += f"    Suggestion: {issue.suggestion}\n"
        
        report += "\n"

    report += """
FACT-CHECKING RESULTS:
================================================================
"""
    
    # Get all verified claims from reviews
    all_claims = []
    for platform_review in final_state["reviews"].values():
        if platform_review and hasattr(platform_review, 'claims'):
            all_claims.extend(platform_review.claims)
    
    if all_claims:
        for i, claim in enumerate(all_claims, 1):
            confidence_percent = claim.confidence * 100 if hasattr(claim, 'confidence') else 0
            severity = getattr(claim, 'severity', 'medium')
            severity_indicator = "🔴" if severity == "high" else "🟡" if severity == "medium" else "🟢"
            
            report += f"{i}. {claim.text}\n"
            report += f"   Severity: {severity.upper()} {severity_indicator}\n"
            report += f"   Confidence: {confidence_percent:.1f}%\n"
            
            if hasattr(claim, 'sources') and claim.sources:
                report += "   Sources:\n"
                for j, source in enumerate(claim.sources, 1):
                    report += f"     {j}. {source}\n"
            report += "\n"
    else:
        report += "No factual claims required verification.\n\n"

    # Add embedding analysis results if available
    if "embedding_analysis" in final_state and "error" not in final_state["embedding_analysis"]:
        report += """
CONTENT QUALITY & SIMILARITY ANALYSIS:
================================================================
"""
        
        embedding_results = final_state["embedding_analysis"]
        
        # Content alignment scores
        if "alignment_scores" in embedding_results:
            report += "Content Alignment Scores (Original → Platform Posts):\n"
            for platform, score in embedding_results["alignment_scores"].items():
                score_percent = score * 100
                rating = "Excellent" if score >= 0.8 else "Good" if score >= 0.6 else "Fair" if score >= 0.4 else "Poor"
                report += f"  {platform.upper()}: {score_percent:.1f}% ({rating})\n"
            report += "\n"
        
        # Quality scores
        if "quality_scores" in embedding_results:
            report += "Content Quality Assessment:\n"
            for platform, scores in embedding_results["quality_scores"].items():
                overall_quality = scores.get("overall_quality", 0) * 100
                content_density = scores.get("content_density", 0) * 100
                semantic_coherence = scores.get("semantic_coherence", 0) * 100
                
                report += f"  {platform.upper()}:\n"
                report += f"    Overall Quality: {overall_quality:.1f}%\n"
                report += f"    Content Density: {content_density:.1f}%\n"
                report += f"    Semantic Coherence: {semantic_coherence:.1f}%\n\n"
        
        # Cross-platform similarity
        if "cross_platform_similarity" in embedding_results:
            report += "Cross-Platform Similarity:\n"
            for comparison, similarity in embedding_results["cross_platform_similarity"].items():
                similarity_percent = similarity * 100
                platforms = comparison.replace("_vs_", " vs ").upper()
                report += f"  {platforms}: {similarity_percent:.1f}%\n"
            report += "\n"
        
        # Content gaps
        if "content_gaps" in embedding_results:
            gaps_found = False
            for platform, gaps in embedding_results["content_gaps"].items():
                if gaps:
                    if not gaps_found:
                        report += "Content Gap Analysis:\n"
                        gaps_found = True
                    report += f"  {platform.upper()}:\n"
                    for gap in gaps:
                        report += f"    - {gap}\n"
            if gaps_found:
                report += "\n"
            else:
                report += "Content Gap Analysis: No significant gaps detected.\n\n"

    report += """
OPTIMAL POSTING SCHEDULE:
================================================================
"""
    
    for timing in final_state["timings"]:
        platform_name = timing.platform.upper()
        try:
            datetime_obj = datetime.fromisoformat(timing.local_datetime_iso.replace('Z', '+00:00'))
            formatted_time = datetime_obj.strftime("%A, %B %d, %Y at %I:%M %p")
        except:
            formatted_time = timing.local_datetime_iso
        
        report += f"{platform_name}:\n"
        report += f"  Date & Time: {formatted_time}\n"
        report += f"  Rationale: {timing.rationale}\n\n"

    report += """
SUMMARY STATISTICS:
================================================================
"""
    
    total_posts = len(final_state["drafts"])
    total_claims = len(all_claims)
    high_confidence_claims = len([c for c in all_claims if hasattr(c, 'confidence') and c.confidence > 0.7])
    
    # Get all unique sources
    all_sources = set()
    for claim in all_claims:
        if hasattr(claim, 'sources'):
            all_sources.update(claim.sources)
    
    report += f"Total Posts Generated: {total_posts}\n"
    report += f"Key Points Extracted: {len(final_state['key_points'])}\n"
    report += f"Claims Fact-Checked: {total_claims}\n"
    report += f"High-Confidence Claims: {high_confidence_claims}\n"
    report += f"Unique Sources Consulted: {len(all_sources)}\n"

    if all_sources:
        report += """

ALL FACT-CHECK SOURCES:
================================================================
"""
        for i, source in enumerate(sorted(all_sources), 1):
            report += f"{i}. {source}\n"

    report += """

================================================================
END OF REPORT

This report was generated by Content Workflow Agent.
All links and sources can be clicked directly if viewing in a text editor that supports hyperlinks.
For questions or support, please contact your system administrator.
================================================================
"""
    
    return report


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
