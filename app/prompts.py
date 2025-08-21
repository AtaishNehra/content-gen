"""
Prompt templates for content generation and analysis.

This module contains all the LLM prompt templates used throughout the Content Workflow Agent.
Each prompt is carefully crafted to produce consistent, high-quality results while minimizing
hallucination and ensuring proper JSON formatting.

Key design principles:
1. Clear, specific instructions to reduce ambiguity
2. JSON-only responses for reliable parsing
3. Anti-hallucination guards to prevent content fabrication
4. Platform-specific constraints and requirements
5. Conditional language enforcement for factual accuracy
"""

# Key points extraction prompt - the foundation of all content generation
# This prompt is critical because all downstream content is based on these extracted insights
KEYPOINTS_PROMPT = """Extract 5–8 key bullet points from the blog text below. Preserve numbers, dates, entities. No marketing fluff. 

Return JSON array of objects with this exact format:
[
    {"text": "specific key point", "importance": 0.8},
    {"text": "another key point", "importance": 0.6}
]

Importance should be a float between 0 and 1, where 1 is most important.

Do not include any prose or explanation outside the JSON array.

Blog text:
{text}"""

# Platform-specific content generation prompt
# This prompt adapts key points into platform-optimized social media posts
# Critical features: character limits, platform tone, conditional language for accuracy
PLATFORM_PROMPT = """Create a {platform} post using the key points below. Follow these constraints:

PLATFORM RULES:
- twitter: ≤ 280 chars; also propose optional thread of 3–5 tweets (≤ 280 each)
- linkedin: 500–1200 chars; professional tone; line breaks ok
- instagram: 125–2200 chars; warm tone; single CTA

CONTENT STANDARDS:
- Use conditional language for statistics without verified sources ("studies suggest", "reports indicate")
- Include clear attribution for specific figures (e.g., "according to WTTC data")
- Avoid absolute statements - frame as trends or emerging patterns
- For recent data (2023-2024), state the year explicitly
- Distinguish between verified facts and industry projections

MENTIONS: Only use verified handles for major organizations (@deloitte, @who, @fda). Use plain text for others.

Include 5–12 relevant hashtags. Do not invent facts beyond the provided key points.

Return JSON with this exact format:
{{
    "primary_text": "main post content here",
    "thread": ["tweet 1", "tweet 2"] or null,
    "hashtags": ["#tag1", "#tag2"],
    "mentions": ["@handle1", "@handle2"]
}}

Key points:
{key_points}

Topic hint: {topic_hint}"""

# Factual claim extraction prompt - identifies statements that need verification
# This prompt is essential for fact-checking pipeline and preventing misinformation
# Focus on verifiable, specific claims rather than general statements
CLAIM_EXTRACT_PROMPT = """From both the original blog content and social media post below, extract up to 10 factual claims that should be verified, focusing on:
- Numeric statistics (percentages, dollar amounts, survey results)
- Named studies or reports (Gartner, Buffer, specific companies)
- Time-bound claims (specific years, dates)
- Quantifiable business metrics

Prioritize claims that reference specific sources or bold statistics. Ignore generic marketing language and tool mentions.

Return JSON array with this exact format:
[
    {{"text": "48% of knowledge workers are working remotely according to 2025 Gartner report", "severity": "high"}},
    {{"text": "80% of remote workers prefer to stay remote permanently per 2024 Buffer survey", "severity": "high"}}
]

Severity levels:
- low: general industry facts
- medium: specific statistics without named sources  
- high: claims with specific sources, percentages, or dollar amounts

Original blog content:
{original_text}

Social media post:
{post_text}"""

# Compliance remediation prompt - fixes content issues while preserving intent
# This prompt is used when compliance review finds violations that can be auto-corrected
# Goal is minimal changes that resolve issues without changing the core message
EDIT_SUGGESTIONS_PROMPT = """The following social media post has compliance issues. Please provide a minimally invasive rewrite that resolves all issues while maintaining the original message and tone.

Issues to fix:
{issues}

Original post:
{post_text}

Return only the revised post text, no extra commentary."""
