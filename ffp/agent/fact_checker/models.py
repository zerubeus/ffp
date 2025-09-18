"""
Data models for the fact-checking agent.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ClaimType(str, Enum):
    """Types of factual claims that can be identified."""

    STATISTICAL = 'statistical'
    HISTORICAL = 'historical'
    SCIENTIFIC = 'scientific'
    QUOTE = 'quote'
    EVENT = 'event'
    POLICY = 'policy'
    CASUALTY = 'casualty'  # Specific to conflict reporting
    GEOGRAPHICAL = 'geographical'
    LEGAL = 'legal'
    MILITARY = 'military'


class ConfidenceLevel(str, Enum):
    """Confidence levels for fact-checking verdicts."""

    HIGH = 'high'  # 80-100%
    MEDIUM = 'medium'  # 60-79%
    LOW = 'low'  # 40-59%
    INSUFFICIENT = 'insufficient'  # <40%


class Claim(BaseModel):
    """Represents a factual claim extracted from social media content."""

    id: str = Field(..., description='Unique identifier')
    text: str = Field(..., min_length=10, description='The actual claim text')
    claim_type: ClaimType
    confidence: float = Field(..., ge=0.0, le=1.0, description='Extraction confidence')
    context: str = Field(..., description='Surrounding context from the post')
    extracted_entities: List[str] = Field(default_factory=list, description='Named entities found')
    keywords: List[str] = Field(default_factory=list, description='Key terms')
    location_context: Optional[str] = Field(None, description='Geographic context if relevant')
    temporal_context: Optional[str] = Field(None, description='Time context if relevant')


class EvidenceSource(BaseModel):
    """Represents a source of evidence for claim verification."""

    url: str
    title: str
    domain: str
    credibility_score: float = Field(..., ge=0.0, le=1.0)
    bias_rating: Optional[str] = None  # left, center, right, unknown
    publication_date: Optional[datetime] = None
    relevant_excerpt: str
    source_type: str  # "fact_checker", "news", "academic", "government", "ngo", "un"
    author: Optional[str] = None
    methodology: Optional[str] = None  # How the source gathered information


class Evidence(BaseModel):
    """Evidence collected for a specific claim."""

    claim_id: str
    sources: List[EvidenceSource]
    supporting_count: int = 0
    contradicting_count: int = 0
    neutral_count: int = 0
    overall_confidence: ConfidenceLevel
    conflicting_sources: bool = Field(default=False, description='Whether sources contradict each other')
    source_diversity_score: float = Field(default=0.0, ge=0.0, le=1.0, description='How diverse the sources are')


class FactCheckVerdict(BaseModel):
    """Final verdict on a claim's truthfulness."""

    claim_id: str
    verdict: str  # "TRUE", "FALSE", "PARTIALLY_TRUE", "UNVERIFIABLE", "MISLEADING", "DISPUTED"
    confidence: ConfidenceLevel
    explanation: str = Field(..., min_length=50, description='Detailed explanation of the verdict')
    evidence_summary: str = Field(..., description='Summary of evidence found')
    sources_consulted: List[str] = Field(..., description='URLs of sources checked')
    limitations: Optional[str] = Field(None, description='Limitations in verification')
    context_needed: Optional[str] = Field(None, description='Additional context needed')
    verification_timestamp: datetime = Field(default_factory=datetime.utcnow)
    sensitive_topic: bool = Field(default=False, description='Whether claim involves sensitive topic')


class PostAnalysis(BaseModel):
    """Complete analysis of a social media post."""

    post_id: str
    post_url: Optional[str] = None
    post_text: str
    claims: List[Claim]
    verdicts: List[FactCheckVerdict]
    overall_credibility: ConfidenceLevel
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow)
    potential_misinformation: bool = Field(default=False)
    requires_human_review: bool = Field(default=False)
    topic_sensitivity: str = Field(default='normal')  # "normal", "sensitive", "highly_sensitive"
    warning_flags: List[str] = Field(default_factory=list)


class PalestineFactCheckContext(BaseModel):
    """Specialized context for Palestine/Israel conflict fact-checking."""

    involves_casualties: bool = False
    involves_settlements: bool = False
    involves_international_law: bool = False
    involves_historical_events: bool = False
    involves_territory_claims: bool = False
    involves_human_rights: bool = False
    time_period: Optional[str] = None  # "current", "historical", "ongoing"
    geographical_scope: Optional[str] = None  # "gaza", "west_bank", "jerusalem", "israel_proper"
    source_perspective: Optional[str] = None  # "israeli", "palestinian", "international", "neutral"
