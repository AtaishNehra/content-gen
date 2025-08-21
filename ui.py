"""
Streamlit UI for the Content Workflow Agent.

This module provides an alternative user interface using Streamlit for users who
prefer a more interactive, form-based approach to content generation. It communicates
with the FastAPI backend to process content and display results.

Key features:
- User-friendly form interface for blog content input
- Real-time processing status and progress indicators
- Formatted display of generated posts with platform-specific styling
- Downloadable results in multiple formats
- Error handling with user-friendly messages
- Responsive design that works on different screen sizes

Why provide a Streamlit UI alongside FastAPI:
- Some users prefer form-based interfaces over API calls
- Provides immediate visual feedback during processing
- Easier for non-technical users to interact with the system
- Enables rapid prototyping and testing of new features
- Supports different user workflows and preferences
"""

import json
from datetime import datetime
from typing import Optional

import streamlit as st
import requests

# Configure Streamlit page settings for optimal user experience
# Wide layout provides more space for displaying multiple platform posts
st.set_page_config(
    page_title="Content Workflow Agent",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Handle WebSocket issues in Replit
if "websocket_error_count" not in st.session_state:
    st.session_state.websocket_error_count = 0

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
</style>
""", unsafe_allow_html=True)

def call_content_api(text: str, topic_hint: Optional[str] = None) -> Optional[dict]:
    """Call the Content Workflow Agent API."""
    try:
        payload = {"text": text}
        if topic_hint:
            payload["topic_hint"] = topic_hint
        
        response = requests.post(
            "http://localhost:5000/v1/plan",
            json=payload,
            timeout=120
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {str(e)}")
        return None
    except Exception as e:
        st.error(f"Unexpected error: {str(e)}")
        return None

def format_platform_post(post: dict, review: dict) -> None:
    """Display a formatted platform post."""
    status = review.get('status', 'unknown')
    status_icons = {'pass': '✅', 'flag': '⚠️', 'block': '❌'}
    status_icon = status_icons.get(status, '❓')
    
    with st.container():
        st.markdown(f"""
        <div class="post-container">
            <div class="platform-header">{status_icon} {post['platform'].upper()}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Main content
        st.markdown(f"""
        <div class="post-content">{post['primary_text']}</div>
        """, unsafe_allow_html=True)
        
        # Thread content if available
        if post.get('thread') and len(post['thread']) > 1:
            with st.expander("View Thread"):
                for i, tweet in enumerate(post['thread'], 1):
                    st.write(f"**Tweet {i}:** {tweet}")
        
        # Metadata
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            if post['hashtags']:
                st.markdown(f"**Hashtags:** {' '.join(post['hashtags'])}")
        with col2:
            if post['mentions']:
                st.markdown(f"**Mentions:** {' '.join(post['mentions'])}")
        with col3:
            st.markdown(f"**Length:** {len(post['primary_text'])} chars")
        
        # Compliance issues if any
        if review.get('issues'):
            with st.expander("⚠️ Compliance Issues"):
                for issue in review['issues']:
                    st.warning(f"**{issue['rule']}:** {issue['message']}")

def format_timing(timing: dict) -> None:
    """Display a formatted timing suggestion."""
    try:
        dt = datetime.fromisoformat(timing['local_datetime_iso'])
        formatted_time = dt.strftime("%B %d, %Y at %I:%M %p")
        
        st.markdown(f"""
        <div class="timing-card">
            <strong>{timing['platform'].upper()}:</strong> {formatted_time}<br>
            <em>{timing['rationale']}</em>
        </div>
        """, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error formatting time: {e}")

# Main UI
st.title("🚀 Content Workflow Agent")
st.markdown("Transform your blog posts into optimized social media content")

# Sidebar for configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    st.info("Configure settings in your environment variables")
    
    # API status check
    try:
        health_response = requests.get("http://localhost:5000/health", timeout=5)
        if health_response.status_code == 200:
            st.success("✅ API Connected")
        else:
            st.error("❌ API Not Responding")
    except:
        st.error("❌ API Unavailable")

# Main form
with st.form("content_form"):
    st.subheader("📝 Input Content")
    
    # Blog content input
    blog_text = st.text_area(
        "Blog Post Content",
        height=200,
        placeholder="Paste your blog post content here...",
        help="Enter the full text of your blog post that you want to convert into social media content."
    )
    
    # Topic hint
    topic_hint = st.text_input(
        "Topic Hint (Optional)",
        placeholder="e.g., AI marketing, tech innovation, business strategy",
        help="Provide a topic hint to help generate more relevant hashtags and content."
    )
    
    # Submit button
    submitted = st.form_submit_button("🎯 Generate Social Media Content", use_container_width=True)

# Process form submission
if submitted:
    if not blog_text.strip():
        st.error("Please enter blog post content before generating.")
    else:
        with st.spinner("🤖 Processing your content... This may take 30-60 seconds."):
            # Call the API
            result = call_content_api(blog_text, topic_hint if topic_hint else None)
            
            if result:
                st.success("✅ Content generated successfully!")
                
                # Display key points
                if result.get('key_points'):
                    with st.expander("💡 Key Points Extracted", expanded=True):
                        for i, point in enumerate(result['key_points'], 1):
                            importance = point.get('importance', 0)
                            importance_bar = "🟦" * int(importance * 5)
                            st.write(f"**{i}.** {point['text']} {importance_bar}")
                
                # Display generated posts
                st.subheader("📱 Generated Social Media Posts")
                
                # Create tabs for each platform
                platforms = [post['platform'] for post in result.get('posts', [])]
                if platforms:
                    tabs = st.tabs([platform.upper() for platform in platforms])
                    
                    for tab, post in zip(tabs, result.get('posts', [])):
                        with tab:
                            review = result.get('reviews', {}).get(post['platform'], {})
                            format_platform_post(post, review)
                
                # Display posting times
                if result.get('timings'):
                    st.subheader("📅 Suggested Posting Times")
                    for timing in result['timings']:
                        format_timing(timing)
                
                # Raw JSON data (for debugging)
                with st.expander("🔍 Raw API Response"):
                    st.json(result)

# Footer
st.markdown("---")
st.markdown(
    "Built with ❤️ using Streamlit and FastAPI • "
    "Powered by OpenAI GPT-4o and LangGraph"
)