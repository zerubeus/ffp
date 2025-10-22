"""
Configuration settings for the fact-checking agent.
"""

from dataclasses import dataclass


@dataclass
class FactCheckConfig:
    """Configuration for fact-checking operations."""

    # Database settings
    cache_ttl_days: int = 30  # How long to cache verified claims
    cleanup_retention_days: int = 90  # How long to keep old data
    min_cache_access_count: int = 2  # Minimum access count to keep during cleanup

    # Claim verification settings
    max_sources_per_evidence: int = 10  # Maximum sources to include in evidence
    min_explanation_length: int = 100  # Minimum explanation length in words

    # Credibility thresholds
    high_credibility_threshold: float = 0.8  # 80%+
    medium_credibility_threshold: float = 0.6  # 60-79%
    low_credibility_threshold: float = 0.4  # 40-59%

    # Analysis settings
    false_verdict_threshold: float = 0.5  # Threshold for low credibility
    disputed_verdict_threshold: float = 0.3  # Threshold for medium credibility

    # Human review settings
    min_insufficient_confidence_for_review: int = 2  # Require review after N insufficient confidence verdicts

    # Performance settings
    trending_claims_limit: int = 5  # Number of trending claims to return
    analysis_history_days: int = 7  # Default days for analysis history

    # Model settings
    default_model: str = 'anthropic:claude-3-sonnet'  # Default AI model

    # Cache settings
    recent_access_days: int = 7  # Days to consider for recent access statistics


# Global configuration instance
config = FactCheckConfig()
