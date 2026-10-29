from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field, HttpUrl, field_validator

def get_utc_now():
    return datetime.now(timezone.utc)

class CostStatus(str, Enum):
    VERIFIED_FREE = "verified_free"
    PAID = "paid"
    PENDING = "pending_verification"

class ProspectInput(BaseModel):
    domain: str = Field(min_length=3, max_length=253)
    page_url: str | None = None
    title: str = ""
    description: str = ""
    category: str = ""
    authority_score: float | None = Field(default=None, ge=0, le=100)
    backlink_quality: float | None = Field(default=None, ge=0, le=100)
    spam_risk: float | None = Field(default=None, ge=0, le=100)
    relevance: float | None = Field(default=None, ge=0, le=100)
    placement_fee: float | None = Field(default=None, ge=0)
    submission_fee: float | None = Field(default=None, ge=0)
    mandatory_purchase: bool | None = None
    paid_plan_required: bool | None = None
    free_submission_available: bool = False
    terms_verified: bool = False
    evidence_url: str | None = None
    link_type: str | None = None

    # Optional tabular ML features for spam-risk model inference
    referring_domains: float | None = None
    outbound_link_ratio: float | None = None
    content_relevance: float | None = None
    domain_age_years: float | None = None
    anchor_diversity: float | None = None
    thin_content_ratio: float | None = None

    @field_validator("domain")
    @classmethod
    def clean_domain(cls, value: str) -> str:
        from app.security import normalize_domain
        return normalize_domain(value)

class AnalyzeRequest(BaseModel):
    website_url: HttpUrl
    category: str = Field(min_length=1, max_length=100)
    country: str = Field(default="GLOBAL", min_length=2, max_length=10)
    keywords: list[str] = Field(default_factory=list, max_length=50)
    provider: str = "demo"
    use_deep_learning: bool = False
    target_count: int = Field(default=100, ge=10, le=200)
    include_types: list[str] = Field(default_factory=lambda: ["directory", "image", "pdf", "editorial"])
    sync: bool | None = None
    prospects: list[ProspectInput] | None = None

class ScoreRequest(BaseModel):
    prospects: list[ProspectInput] = Field(min_length=1, max_length=500)

class ScoreBreakdown(BaseModel):
    relevance: float | None
    authority: float | None
    backlink_quality: float | None
    spam_risk: float | None
    editorial_potential: float
    opportunity_score: float | None
    confidence: str
    missing_fields: list[str] = Field(default_factory=list)
    semantic_similarity: float | None = None

class ProspectResult(BaseModel):
    domain: str
    page_url: str | None = None
    title: str = ""
    description: str = ""
    cost_status: CostStatus
    score: ScoreBreakdown
    evidence_url: str | None = None
    link_type: str | None = None
    reasons: list[str] = Field(default_factory=list)
    last_checked: datetime = Field(default_factory=get_utc_now)

class BacklinkCheckRequest(BaseModel):
    urls: list[HttpUrl] = Field(min_length=1, max_length=50)
    target_domain: str | None = None
    target_url: str | None = None

class ExplainProspectRequest(BaseModel):
    domain: str
    category: str
    evidence: dict = Field(default_factory=dict)

class AsyncScanJobResponse(BaseModel):
    scan_id: str
    status: str = "queued"
    progress: int = 0
    stage: str = "Scan queued for execution"
    message: str = "Scan job initiated asynchronously."
    stream_url: str
    status_url: str

class ScanStatusResponse(BaseModel):
    scan_id: str
    status: str
    progress: int
    stage: str
    error_message: str | None = None
    created_at: datetime
    website_domain: str
    category: str
    prospects_found: int = 0
    payload: dict | None = None
