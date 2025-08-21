"""
Intelligent scheduling functionality with timezone-aware posting time suggestions.

This module implements research-based scheduling recommendations that consider platform
engagement patterns, content type, audience geography, and timing best practices.
The system provides context-aware suggestions with clear rationales.

Key features:
- Research-driven platform timing heuristics
- Content-type sensitive scheduling (breaking news, professional, visual)
- Audience geography detection and timezone adjustment
- Intelligent conflict resolution and post spacing
- Regulated industry content flagging
- Comprehensive rationale generation for transparency

Why intelligent scheduling matters:
- Different platforms have different peak engagement times
- Content type affects optimal timing (urgent vs evergreen)
- Audience geography determines relevant timezones
- Proper spacing prevents algorithm penalties
- Compliance timing for regulated content
"""

from datetime import datetime, timedelta
from typing import List, Optional
from zoneinfo import ZoneInfo

from ..config import config
from ..models import Platform, PostingTime

# Research-based optimal time slots by platform and context
# These times are derived from industry research and engagement studies
# Each platform has different usage patterns that affect optimal posting times
PLATFORM_OPTIMAL_TIMES = {
    "twitter": {
        # Peak engagement during lunch break - high social media usage
        "weekday_primary": ["12:00", "13:00", "14:00", "15:00"],  # 12pm-3pm peak engagement
        # Morning commute/pre-work browsing
        "weekday_secondary": ["09:00"],  # 9am bump
        # Breaking news should be posted immediately for maximum impact
        "breaking_news": ["immediate"],  # Post ASAP for breaking news
        # Weekend leisure browsing patterns
        "weekend": ["10:00", "14:00", "16:00"]
    },
    "linkedin": {
        # Professional network - Tuesday/Thursday optimal for business content
        "tuesday_thursday": ["07:00", "08:00", "09:00", "12:00", "13:00", "14:00", "17:00", "18:00"],
        # Other weekdays have reduced but still meaningful engagement
        "other_weekdays": ["08:00", "13:00", "17:00"],
        # Pre-work professional browsing window
        "professional_morning": ["07:00", "08:00", "09:00"],  # Before work
        # LinkedIn engagement drops significantly on weekends
        "weekend": []  # LinkedIn performs poorly on weekends
    },
    "instagram": {
        # Evening leisure browsing - prime time for visual content
        "weekday_evening": ["18:00", "19:00", "20:00", "21:00"],  # 6-9pm
        # Weekend morning casual browsing
        "weekend_morning": ["10:00", "11:00"],  # Sunday mornings
        # Weekend evening engagement
        "weekend_evening": ["18:00", "19:00", "20:00", "21:00"],
        # Optimal for high-quality visual content
        "visual_content": ["19:00", "20:00"]  # Prime visual browsing
    }
}

# Content type timing preferences
CONTENT_TYPE_PREFERENCES = {
    "professional": {
        "platforms": {"linkedin": "professional_morning", "twitter": "weekday_secondary"},
        "description": "Professional insights work best in morning business hours"
    },
    "breaking_news": {
        "platforms": {"twitter": "breaking_news"},
        "description": "Breaking news should be posted immediately"
    },
    "visual_lifestyle": {
        "platforms": {"instagram": "weekday_evening"},
        "description": "Visual content performs best during leisure browsing"
    },
    "analytical": {
        "platforms": {"linkedin": "tuesday_thursday", "twitter": "weekday_primary"},
        "description": "Data-driven content works best during professional hours"
    },
    "travel": {
        "platforms": {"instagram": "weekend_morning", "twitter": "weekday_primary"},
        "description": "Travel content engages well on weekends and lunch breaks"
    }
}

# Geographic audience detection patterns
AUDIENCE_PATTERNS = {
    "us": ["america", "united states", "us ", "usa", "american", "newark", "miami", "california"],
    "europe": ["europe", "european", "eu ", "uk", "britain", "germany", "france", "london"],
    "asia": ["asia", "asian", "china", "japan", "india", "singapore", "tokyo"],
    "nordics": ["greenland", "iceland", "denmark", "norway", "sweden", "finland"],
    "global": ["global", "worldwide", "international", "multinational"]
}

# Timezone mappings for audience localization  
AUDIENCE_TIMEZONES = {
    "us": "US/Eastern",
    "europe": "Europe/London",
    "asia": "Asia/Singapore", 
    "nordics": "Europe/Copenhagen",
    "global": "US/Eastern"  # Default to US Eastern
}

# Regulated industry patterns for compliance flagging
REGULATED_INDUSTRIES = {
    "healthcare": ["health", "medical", "drug", "medicine", "clinical", "treatment", "therapy"],
    "finance": ["investment", "trading", "stock", "crypto", "financial", "finance", "banking"],
    "aviation": ["aviation", "aircraft", "flight", "airline", "airport", "faa", "boeing", "airbus"]
}
REGULATED_INDUSTRIES = {
    "healthcare": ["hospital", "medical", "health", "patient", "doctor", "medicine", "clinical"],
    "finance": ["bank", "financial", "investment", "trading", "crypto", "payment", "fintech"],
    "aviation": ["airline", "airport", "flight", "aircraft", "aviation", "faa"],
    "pharma": ["drug", "pharmaceutical", "medication", "treatment", "therapy"]
}


def suggest_times(platforms: List[Platform], content_text: str = "", topic_hint: str = "") -> List[PostingTime]:
    """
    Suggest context-aware optimal posting times with content-type sensitivity.

    Args:
        platforms: List of platforms to schedule
        content_text: Blog content for context analysis
        topic_hint: Topic hint for content categorization

    Returns:
        List of PostingTime suggestions with context-aware timing
    """
    # Detect content type and audience geography
    content_type = _detect_content_type(content_text, topic_hint)
    audience_region = _detect_audience_geography(content_text, topic_hint)
    regulated_industry = _detect_regulated_industry(content_text, topic_hint)
    
    # Get timezone for audience localization
    target_timezone = ZoneInfo(AUDIENCE_TIMEZONES.get(audience_region, config.DEFAULT_TZ))
    now = datetime.now(target_timezone)
    
    suggestions = []
    used_time_slots = set()
    
    # Process platforms based on content type preferences
    for platform in platforms:
        platform_suggestions = _get_context_aware_suggestions(
            platform, content_type, now, target_timezone, used_time_slots, regulated_industry
        )
        suggestions.extend(platform_suggestions)

    # Sort by datetime and apply intelligent limits
    suggestions.sort(key=lambda x: x.local_datetime_iso)
    
    # Limit based on content urgency
    max_posts = 3 if content_type == "breaking_news" else 6
    return suggestions[:max_posts]


def _get_staggered_platform_suggestions(
    platform: Platform, now: datetime, timezone: ZoneInfo, used_slots: set
) -> List[PostingTime]:
    """
    Get staggered posting time suggestions for a specific platform.

    Args:
        platform: Target platform
        now: Current datetime in target timezone
        timezone: Target timezone
        used_slots: Set of already used time slots

    Returns:
        List of PostingTime suggestions for the platform
    """
    suggestions = []
    slots = _get_platform_time_slots(platform)

    for slot in slots[:2]:  # Limit to top 2 slots per platform
        suggested_time = _calculate_next_slot_time(slot, now, timezone)
        
        # Create time slot key for staggering (30-min blocks)
        time_slot_key = (suggested_time.date(), suggested_time.hour, suggested_time.minute // 30)
        
        # Stagger if slot is already used
        if time_slot_key in used_slots:
            stagger_hours = 2 if platform == "twitter" else 3
            suggested_time += timedelta(hours=stagger_hours)
            time_slot_key = (suggested_time.date(), suggested_time.hour, suggested_time.minute // 30)
        
        used_slots.add(time_slot_key)
        rationale = f"{'Primary' if len(suggestions) == 0 else 'Secondary'} slot - {_get_slot_rationale(platform, slot)}"

        suggestions.append(
            PostingTime(
                platform=platform,
                local_datetime_iso=suggested_time.isoformat(),
                rationale=rationale,
            )
        )

    return suggestions

def _detect_content_type(content_text: str, topic_hint: str) -> str:
    """Detect content type for timing optimization."""
    combined_text = f"{content_text} {topic_hint}".lower()
    
    # Breaking news indicators
    if any(term in combined_text for term in ["breaking", "alert", "urgent", "just announced", "developing"]):
        return "breaking_news"
    
    # Travel/lifestyle content
    if any(term in combined_text for term in ["travel", "vacation", "destination", "tourism", "flight", "hotel"]):
        return "travel"
    
    # Professional/analytical content
    if any(term in combined_text for term in ["study", "research", "analysis", "data", "report", "survey"]):
        return "analytical" 
    
    # Visual/lifestyle content
    if any(term in combined_text for term in ["photos", "images", "beautiful", "stunning", "lifestyle", "culture"]):
        return "visual_lifestyle"
    
    # Default to professional for business content
    return "professional"


def _detect_audience_geography(content_text: str, topic_hint: str) -> str:
    """Detect target audience geography for timezone localization."""
    combined_text = f"{content_text} {topic_hint}".lower()
    
    # Check for geographic patterns
    for region, patterns in AUDIENCE_PATTERNS.items():
        if any(pattern in combined_text for pattern in patterns):
            return region
    
    return "global"  # Default


def _detect_regulated_industry(content_text: str, topic_hint: str) -> Optional[str]:
    """Detect if content relates to regulated industries requiring compliance review."""
    combined_text = f"{content_text} {topic_hint}".lower()
    
    for industry, patterns in REGULATED_INDUSTRIES.items():
        if any(pattern in combined_text for pattern in patterns):
            return industry
    
    return None


def _get_context_aware_suggestions(
    platform: Platform, 
    content_type: str, 
    now: datetime, 
    timezone: ZoneInfo, 
    used_slots: set,
    regulated_industry: Optional[str]
) -> List[PostingTime]:
    """Generate context-aware posting suggestions."""
    suggestions = []
    
    # Get timing preference for this content type and platform
    type_prefs = CONTENT_TYPE_PREFERENCES.get(content_type, {})
    platform_timing_key = type_prefs.get("platforms", {}).get(platform)
    
    if not platform_timing_key:
        # Fallback to general platform timing
        platform_timing_key = _get_default_timing_key(platform, now)
    
    # Get optimal times for this platform and timing context
    optimal_times = PLATFORM_OPTIMAL_TIMES.get(platform, {}).get(platform_timing_key, ["12:00"])
    
    # Handle immediate posting for breaking news
    if platform_timing_key == "immediate":
        immediate_time = now + timedelta(minutes=5)  # 5 minute buffer
        rationale = "Breaking news - post immediately for maximum engagement"
        
        if regulated_industry:
            rationale += f" [COMPLIANCE REQUIRED: {regulated_industry.upper()} content needs review]"
        
        suggestions.append(PostingTime(
            platform=platform,
            local_datetime_iso=immediate_time.isoformat(),
            rationale=rationale
        ))
        return suggestions
    
    # Generate suggestions for regular content
    for i, time_slot in enumerate(optimal_times[:2]):  # Limit to 2 per platform
        suggested_time = _calculate_optimal_slot_time(time_slot, now, timezone, platform_timing_key)
        
        # Apply staggering if slot already used
        time_slot_key = (suggested_time.date(), suggested_time.hour, suggested_time.minute // 30)
        if time_slot_key in used_slots:
            stagger_hours = 1 if platform == "twitter" else 2
            suggested_time += timedelta(hours=stagger_hours)
            time_slot_key = (suggested_time.date(), suggested_time.hour, suggested_time.minute // 30)
        
        used_slots.add(time_slot_key)
        
        # Generate context-aware rationale
        rationale = _generate_context_rationale(platform, content_type, time_slot, regulated_industry)
        
        suggestions.append(PostingTime(
            platform=platform,
            local_datetime_iso=suggested_time.isoformat(),
            rationale=rationale
        ))
    
    return suggestions


def _get_default_timing_key(platform: Platform, now: datetime) -> str:
    """Get default timing key based on platform and current day."""
    current_day = now.weekday()  # 0=Monday, 6=Sunday
    
    if platform == "linkedin":
        # Tuesday-Thursday get premium slots
        return "tuesday_thursday" if 1 <= current_day <= 3 else "other_weekdays"
    elif platform == "instagram":
        # Weekends get special treatment
        return "weekend_morning" if current_day >= 5 else "weekday_evening"
    else:  # twitter
        return "weekday_primary" if current_day < 5 else "weekend"


def _calculate_optimal_slot_time(time_slot: str, now: datetime, timezone: ZoneInfo, timing_context: str) -> datetime:
    """Calculate next optimal posting time for a slot."""
    hour, minute = map(int, time_slot.split(":"))
    suggested_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    # For weekend-specific content, ensure it's scheduled for weekend
    if "weekend" in timing_context and now.weekday() < 5:
        days_until_weekend = 5 - now.weekday()  # Days until Saturday
        suggested_time += timedelta(days=days_until_weekend)
    
    # If time has passed today, schedule for tomorrow (or appropriate day)
    elif suggested_time <= now:
        suggested_time += timedelta(days=1)
    
    return suggested_time


def _generate_context_rationale(platform: Platform, content_type: str, time_slot: str, regulated_industry: Optional[str]) -> str:
    """Generate context-aware rationale for posting time."""
    # Base rationale from content type
    type_description = CONTENT_TYPE_PREFERENCES.get(content_type, {}).get("description", "Optimal engagement time")
    
    # Platform-specific timing reason
    platform_reasons = {
        "07:00": "Early morning professional browsing",
        "08:00": "Pre-work engagement peak", 
        "09:00": "Morning commute and coffee break",
        "12:00": "Lunch break browsing peak",
        "13:00": "Post-lunch professional activity",
        "14:00": "Afternoon engagement window",
        "15:00": "Late afternoon peak",
        "17:00": "End-of-workday browsing",
        "18:00": "Evening leisure browsing",
        "19:00": "Prime evening engagement",
        "20:00": "Peak evening social time",
        "21:00": "Late evening browsing"
    }
    
    timing_reason = platform_reasons.get(time_slot, "Optimal engagement window")
    base_rationale = f"{timing_reason} - {type_description}"
    
    # Add compliance flag for regulated industries
    if regulated_industry:
        compliance_flag = f" [COMPLIANCE REVIEW REQUIRED: {regulated_industry.upper()} content]"
        base_rationale += compliance_flag
    
    return base_rationale


def _calculate_next_slot_time(slot: str, now: datetime, timezone: ZoneInfo) -> datetime:
    """
    Calculate the next occurrence of a time slot.

    Args:
        slot: Time slot in HH:MM format
        now: Current datetime
        timezone: Target timezone

    Returns:
        Next datetime for the slot
    """
    hour, minute = map(int, slot.split(":"))
    today_slot = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    # If the slot time has passed today, schedule for tomorrow
    if today_slot <= now:
        return today_slot + timedelta(days=1)

    return today_slot


def _get_rationale(platform: Platform, slot: str) -> str:
    """
    Get rationale for a specific platform and time slot.

    Args:
        platform: Target platform
        slot: Time slot in HH:MM format

    Returns:
        Human-readable rationale string
    """
    rationales = {
        "twitter": {
            "09:00": "Morning commute - high engagement for quick reads",
            "12:00": "Lunch break - peak social media browsing",
            "18:00": "Evening wind-down - high retweet activity",
        },
        "linkedin": {
            "08:45": "Pre-work professional browsing",
            "13:00": "Lunch break professional networking",
            "09:30": "Mid-morning business activity peak",
        },
        "instagram": {
            "11:00": "Late morning leisure browsing",
            "19:00": "Evening social media prime time",
            "15:30": "Afternoon break - visual content peak",
        },
    }

    return rationales.get(platform, {}).get(slot, f"Optimal {platform} posting time")
