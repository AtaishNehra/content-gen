"""
Standalone Streamlit UI for Content Workflow Agent (GitHub Deployment).

This module provides a complete standalone interface that directly integrates
with the content workflow without requiring a separate FastAPI backend.
Perfect for local deployment and GitHub-based usage.

Key features:
- Direct integration with workflow graph
- No external API dependencies
- Real-time processing with progress indicators
- Complete content generation pipeline
- Downloadable results
- Error handling with user-friendly messages
"""

import json
import os
import sys
from datetime import datetime
from typing import Optional

import streamlit as st

# Add the app module to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import application components directly
from app.graph import build_graph
from app.models import State

# Configure Streamlit page settings for optimal user experience
st.set_page_config(
    page_title="Content Workflow Agent",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better styling
st.markdown("""
<style>
.stAlert > div {
    padding: 1rem;
    margin: 1rem 0;
}
.post-container {
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 1rem;
    margin: 0.5rem 0;
    background-color: #fafafa;
}
.platform-header {
    font-weight: 600;
    font-size: 1.1rem;
    margin-bottom: 0.5rem;
    color: #1f77b4;
}
.post-content {
    background: white;
    padding: 0.8rem;
    border-radius: 4px;
    border-left: 4px solid #1f77b4;
    margin: 0.5rem 0;
}
.metadata {
    font-size: 0.8rem;
    color: #666;
    margin-top: 0.5rem;
}
.timing-card {
    background: #f0f8ff;
    border: 1px solid #bee3f8;
    padding: 0.8rem;
    border-radius: 4px;
    margin: 0.3rem 0;
}
.fact-check-high {
    background: #fff5f5;
    border-left: 4px solid #f56565;
    padding: 0.5rem;
    margin: 0.25rem 0;
}
.fact-check-medium {
    background: #fffaf0;
    border-left: 4px solid #ed8936;
    padding: 0.5rem;
    margin: 0.25rem 0;
}
.fact-check-low {
    background: #f0fff4;
    border-left: 4px solid #48bb78;
    padding: 0.5rem;
    margin: 0.25rem 0;
}
</style>
""", unsafe_allow_html=True)

def initialize_workflow():
    """Initialize the workflow graph once per session."""
    if 'workflow_graph' not in st.session_state:
        with st.spinner("Initializing Content Workflow Agent..."):
            st.session_state.workflow_graph = build_graph()
    return st.session_state.workflow_graph

def process_content_directly(text: str, topic_hint: Optional[str] = None) -> Optional[dict]:
    """Process content directly using the workflow graph."""
    try:
        # Get the workflow graph
        graph = initialize_workflow()
        
        # Initialize state with proper typing
        initial_state = {
            "text": text,
            "topic_hint": topic_hint or "",
            "key_points": [],
            "drafts": {},
            "claims": {},
            "reviews": {},
            "timings": [],
            "errors": [],
            "embedding_analysis": {},
        }
        
        # Process through workflow with progress updates
        final_state = graph.invoke(initial_state)
        
        # Convert to response format
        return {
            "key_points": final_state["key_points"],
            "posts": list(final_state["drafts"].values()),
            "reviews": final_state["reviews"],
            "timings": final_state["timings"],
            "errors": final_state["errors"]
        }
        
    except Exception as e:
        st.error(f"Processing failed: {str(e)}")
        return None

def display_key_points(key_points):
    """Display extracted key points with importance scores."""
    if not key_points:
        st.warning("No key points were extracted.")
        return
        
    st.subheader("📝 Extracted Key Points")
    
    for i, point in enumerate(key_points, 1):
        importance = getattr(point, 'importance', 0.5)
        importance_text = f"{importance:.1f}" if hasattr(point, 'importance') else "N/A"
        
        # Color code by importance
        if importance >= 0.8:
            importance_color = "🔴"
        elif importance >= 0.6:
            importance_color = "🟡"
        else:
            importance_color = "🟢"
            
        st.markdown(f"**{i}.** {importance_color} {point.text} *(Importance: {importance_text})*")

def display_platform_posts(posts):
    """Display generated posts for each platform."""
    if not posts:
        st.warning("No posts were generated.")
        return
        
    st.subheader("📱 Generated Posts")
    
    platform_icons = {
        "twitter": "🐦",
        "linkedin": "💼", 
        "instagram": "📸"
    }
    
    cols = st.columns(len(posts))
    
    for i, post in enumerate(posts):
        with cols[i]:
            platform = post.platform.lower()
            icon = platform_icons.get(platform, "📝")
            
            st.markdown(f"""
            <div class="post-container">
                <div class="platform-header">{icon} {post.platform.title()}</div>
                <div class="post-content">{post.primary_text}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Show thread if available (Twitter)
            if hasattr(post, 'thread') and post.thread:
                st.markdown("**Thread:**")
                for j, tweet in enumerate(post.thread, 1):
                    st.markdown(f"{j}. {tweet}")
            
            # Show hashtags
            if post.hashtags:
                st.markdown(f"**Hashtags:** {' '.join(post.hashtags)}")
            
            # Show mentions
            if post.mentions:
                st.markdown(f"**Mentions:** {', '.join(post.mentions)}")

def display_fact_checking(reviews):
    """Display fact-checking results."""
    if not reviews:
        st.warning("No fact-checking results available.")
        return
        
    st.subheader("🔍 Fact-Checking Results")
    
    for platform, review in reviews.items():
        with st.expander(f"📋 {platform.title()} - Compliance & Fact-Check"):
            
            # Compliance status
            status_color = "🟢" if review.status == "approved" else "🟡" if review.status == "review" else "🔴"
            st.markdown(f"**Status:** {status_color} {review.status.title()}")
            
            # Compliance issues
            if review.issues:
                st.markdown("**Compliance Issues:**")
                for issue in review.issues:
                    st.markdown(f"- {issue.rule_id}: {issue.message}")
            
            # Fact-check claims
            if hasattr(review, 'claims') and review.claims:
                st.markdown("**Fact-Check Results:**")
                for claim in review.claims:
                    confidence = getattr(claim, 'confidence', 0)
                    severity_class = f"fact-check-{claim.severity}"
                    
                    st.markdown(f"""
                    <div class="{severity_class}">
                        <strong>{claim.text}</strong><br>
                        <small>Confidence: {confidence:.1%} | Severity: {claim.severity}</small>
                    </div>
                    """, unsafe_allow_html=True)

def display_scheduling(timings):
    """Display optimal posting times."""
    if not timings:
        st.warning("No scheduling recommendations available.")
        return
        
    st.subheader("⏰ Optimal Posting Times")
    
    for timing in timings:
        # Parse the ISO datetime string to display it properly
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(timing.local_datetime_iso)
            formatted_time = dt.strftime('%Y-%m-%d %H:%M')
        except:
            formatted_time = timing.local_datetime_iso
            
        st.markdown(f"""
        <div class="timing-card">
            <strong>📱 {timing.platform.title()}</strong><br>
            <strong>🕐 {formatted_time}</strong><br>
            <em>{timing.rationale}</em>
        </div>
        """, unsafe_allow_html=True)

def generate_export_text(result):
    """Generate formatted text for export."""
    if not result:
        return "No content to export."
        
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    export_text = f"""Content Workflow Agent - Export Report
Generated: {timestamp}

{'='*60}
KEY POINTS EXTRACTED
{'='*60}

"""
    
    # Add key points
    for i, point in enumerate(result.get('key_points', []), 1):
        importance = getattr(point, 'importance', 0.5)
        export_text += f"{i}. {point.text} (Importance: {importance:.1f})\n"
    
    export_text += f"\n{'='*60}\nGENERATED POSTS\n{'='*60}\n\n"
    
    # Add posts
    for post in result.get('posts', []):
        export_text += f"{post.platform.upper()}:\n"
        export_text += f"{post.primary_text}\n"
        
        if hasattr(post, 'thread') and post.thread:
            export_text += "Thread:\n"
            for j, tweet in enumerate(post.thread, 1):
                export_text += f"  {j}. {tweet}\n"
        
        if post.hashtags:
            export_text += f"Hashtags: {' '.join(post.hashtags)}\n"
        
        if post.mentions:
            export_text += f"Mentions: {', '.join(post.mentions)}\n"
        
        export_text += "\n" + "-"*40 + "\n\n"
    
    export_text += f"{'='*60}\nSCHEDULING RECOMMENDATIONS\n{'='*60}\n\n"
    
    # Add scheduling
    for timing in result.get('timings', []):
        # Parse the ISO datetime string for export
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(timing.local_datetime_iso)
            formatted_time = dt.strftime('%Y-%m-%d %H:%M')
        except:
            formatted_time = timing.local_datetime_iso
        export_text += f"{timing.platform.upper()}: {formatted_time}\n"
        export_text += f"Rationale: {timing.rationale}\n\n"
    
    return export_text

def main():
    """Main Streamlit application."""
    st.title("🚀 Content Workflow Agent")
    st.markdown("Transform your blog content into engaging social media posts with AI-powered optimization.")
    
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        st.error("⚠️ OpenAI API key not found! Please set OPENAI_API_KEY in your .env file.")
        st.stop()
    
    # Input section
    st.header("📝 Input")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        blog_text = st.text_area(
            "Blog Content",
            placeholder="Paste your blog content here (minimum 100 characters)...",
            height=200,
            help="Enter the blog post or article content you want to convert into social media posts."
        )
    
    with col2:
        topic_hint = st.text_input(
            "Topic Hint (Optional)",
            placeholder="e.g., technology, travel, healthcare",
            help="Provide a topic hint to improve content targeting and hashtag generation."
        )
        
        # Processing controls
        st.markdown("### Processing Options")
        process_button = st.button("🚀 Generate Content Plan", type="primary", use_container_width=True)
    
    # Validation
    if blog_text and len(blog_text) < 100:
        st.warning("⚠️ Please enter at least 100 characters for meaningful content generation.")
    
    # Process content
    if process_button and blog_text and len(blog_text) >= 100:
        with st.spinner("🔄 Processing your content... This may take 30-60 seconds."):
            
            # Create progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Update progress
            status_text.text("Extracting key points...")
            progress_bar.progress(20)
            
            # Process content
            result = process_content_directly(blog_text, topic_hint)
            progress_bar.progress(100)
            status_text.text("Processing complete!")
            
            if result and not result.get('errors'):
                st.success("✅ Content processing completed successfully!")
                
                # Display results
                display_key_points(result.get('key_points', []))
                display_platform_posts(result.get('posts', []))
                display_fact_checking(result.get('reviews', {}))
                display_scheduling(result.get('timings', []))
                
                # Export functionality
                st.header("📥 Export Results")
                export_text = generate_export_text(result)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        label="📄 Download as Text File",
                        data=export_text,
                        file_name=f"content-plan-{datetime.now().strftime('%Y%m%d-%H%M%S')}.txt",
                        mime="text/plain"
                    )
                
                with col2:
                    if st.button("📋 Copy to Clipboard"):
                        st.code(export_text, language=None)
                        st.info("📋 Content displayed above - copy manually")
                
            else:
                st.error("❌ Content processing failed. Please check your input and try again.")
                if result and result.get('errors'):
                    st.error("Errors: " + ", ".join(result['errors']))

if __name__ == "__main__":
    main()
