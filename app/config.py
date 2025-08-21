"""
Configuration management for the Content Workflow Agent.

This module handles all environment-based configuration settings for the application.
It provides a centralized way to manage API keys, service providers, and operational settings
while ensuring proper validation and secure defaults.
"""

import os
from typing import Literal, cast

# Optional dependency handling for python-dotenv
# This allows the app to work even if dotenv package is not installed
try:
    from dotenv import load_dotenv
    # Load environment variables from .env file if it exists
    # This is useful for local development but not required in production
    load_dotenv()
except ImportError:
    # dotenv is optional - continue without it
    # Production environments typically set environment variables directly
    pass


class Config:
    """
    Application configuration loaded from environment variables.
    
    This class uses class attributes to store configuration values, making them
    accessible throughout the application. All settings are loaded from environment
    variables with sensible defaults where appropriate.
    
    Why class attributes instead of instance attributes:
    - Allows for easy global access without dependency injection
    - Configuration is immutable after startup
    - Simpler to test and mock during development
    """

    # Required settings - these must be provided by the user
    # OpenAI API key is essential for all LLM operations (content generation, embeddings)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Optional settings with sensible defaults
    # Default timezone affects scheduling recommendations and timestamp formatting
    # Asia/Kolkata chosen as default to avoid US/Europe bias in global applications
    DEFAULT_TZ: str = os.getenv("DEFAULT_TZ", "Asia/Kolkata")
    
    # Fact-checking provider selection - allows switching between search backends
    # DuckDuckGo chosen as default because it requires no API keys and has good rate limits
    FACTCHECK_PROVIDER: Literal["duckduckgo", "wikipedia", "serpapi"] = cast(
        Literal["duckduckgo", "wikipedia", "serpapi"],
        os.getenv("FACTCHECK_PROVIDER", "duckduckgo")
    )
    
    # SerpAPI key - only needed if using premium search provider
    # Empty default allows graceful fallback to free providers
    SERPAPI_API_KEY: str = os.getenv("SERPAPI_API_KEY", "")
    
    # Wikipedia language code for international content support
    # English chosen as default for broadest content coverage
    WIKIPEDIA_LANG: str = os.getenv("WIKIPEDIA_LANG", "en")
    
    # Organization name used in generated content mentions and branding
    # Generic "Acme" used as safe default that won't appear in real content
    ORG_NAME: str = os.getenv("ORG_NAME", "Acme")
    
    # Compliance mode affects how strictly content rules are enforced
    # "standard" mode issues warnings, "strict" mode blocks problematic content
    COMPLIANCE_MODE: Literal["standard", "strict"] = cast(
        Literal["standard", "strict"],
        os.getenv("COMPLIANCE_MODE", "standard")
    )

    @classmethod
    def validate(cls) -> None:
        """
        Validate required configuration settings on application startup.
        
        This method checks that all essential configuration is present and valid.
        It's called during module import to fail fast if configuration is missing.
        
        Why validate on startup instead of runtime:
        - Fails fast with clear error messages
        - Prevents runtime failures after partial processing
        - Makes configuration issues obvious during deployment
        
        Raises:
            ValueError: If required configuration is missing or invalid
        """
        # OpenAI API key is absolutely required - all core functionality depends on it
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        # If user chooses SerpAPI, they must provide a valid API key
        # This prevents runtime failures during fact-checking operations
        if cls.FACTCHECK_PROVIDER == "serpapi" and not cls.SERPAPI_API_KEY:
            raise ValueError("SERPAPI_API_KEY is required when FACTCHECK_PROVIDER=serpapi")


# Initialize and validate configuration on module import
# This ensures the application fails fast if configuration is invalid
# rather than failing later during request processing
config = Config()
config.validate()
