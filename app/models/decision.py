"""
Decision-related Pydantic models for OPD Claim Adjudication Tool.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class DecisionType(str, Enum):
    """Types of adjudication decisions."""
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PARTIAL = "PARTIAL"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class RejectionReason(str, Enum):
    """Standard rejection reason codes."""
    # Category 1: Eligibility Issues
    POLICY_INACTIVE = "POLICY_INACTIVE"
    WAITING_PERIOD = "WAITING_PERIOD"
    MEMBER_NOT_COVERED = "MEMBER_NOT_COVERED"
    
    # Category 2: Documentation Issues
    MISSING_DOCUMENTS = "MISSING_DOCUMENTS"
    ILLEGIBLE_DOCUMENTS = "ILLEGIBLE_DOCUMENTS"
    INVALID_PRESCRIPTION = "INVALID_PRESCRIPTION"
    DOCTOR_REG_INVALID = "DOCTOR_REG_INVALID"
    DATE_MISMATCH = "DATE_MISMATCH"
    PATIENT_MISMATCH = "PATIENT_MISMATCH"
    
    # Category 3: Coverage Issues
    SERVICE_NOT_COVERED = "SERVICE_NOT_COVERED"
    EXCLUDED_CONDITION = "EXCLUDED_CONDITION"
    PRE_AUTH_MISSING = "PRE_AUTH_MISSING"
    
    # Category 4: Limit Issues
    ANNUAL_LIMIT_EXCEEDED = "ANNUAL_LIMIT_EXCEEDED"
    SUB_LIMIT_EXCEEDED = "SUB_LIMIT_EXCEEDED"
    PER_CLAIM_EXCEEDED = "PER_CLAIM_EXCEEDED"
    
    # Category 5: Medical Issues
    NOT_MEDICALLY_NECESSARY = "NOT_MEDICALLY_NECESSARY"
    EXPERIMENTAL_TREATMENT = "EXPERIMENTAL_TREATMENT"
    COSMETIC_PROCEDURE = "COSMETIC_PROCEDURE"
    
    # Category 6: Process Issues
    LATE_SUBMISSION = "LATE_SUBMISSION"
    DUPLICATE_CLAIM = "DUPLICATE_CLAIM"
    BELOW_MIN_AMOUNT = "BELOW_MIN_AMOUNT"


class EligibilityResult(BaseModel):
    """Result from eligibility check."""
    is_eligible: bool = True
    policy_active: bool = True
    waiting_period_satisfied: bool = True
    member_covered: bool = True
    rejection_reasons: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
    waiting_period_end_date: Optional[str] = None


class CoverageResult(BaseModel):
    """Result from coverage validation."""
    is_covered: bool = True
    covered_items: List[str] = Field(default_factory=list)
    excluded_items: List[str] = Field(default_factory=list)
    pre_auth_required: bool = False
    pre_auth_obtained: bool = False
    rejection_reasons: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class LimitResult(BaseModel):
    """Result from limit calculations."""
    within_limits: bool = True
    claim_amount: float = 0
    approved_amount: float = 0
    
    # Deductions breakdown
    copay_amount: float = 0
    copay_percentage: float = 0
    network_discount: float = 0
    excluded_amount: float = 0
    
    # Limit checks
    per_claim_limit: float = 5000
    annual_limit: float = 50000
    applicable_sub_limit: float = 0
    remaining_annual_limit: float = 50000
    
    # Violations
    per_claim_exceeded: bool = False
    annual_limit_exceeded: bool = False
    sub_limit_exceeded: bool = False
    
    rejection_reasons: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class FraudCheckResult(BaseModel):
    """Result from fraud detection."""
    is_suspicious: bool = False
    fraud_flags: List[str] = Field(default_factory=list)
    risk_score: float = 0.0  # 0-1, higher means more risky
    recommend_manual_review: bool = False
    notes: Optional[str] = None


class AdjudicationResult(BaseModel):
    """Final adjudication decision."""
    claim_id: str
    decision: DecisionType
    approved_amount: float = 0
    
    # Breakdown
    deductions: Dict[str, float] = Field(default_factory=dict)
    rejected_items: List[str] = Field(default_factory=list)
    rejection_reasons: List[str] = Field(default_factory=list)
    
    # Confidence and flags
    confidence_score: float = Field(ge=0, le=1, default=0.95)
    fraud_flags: List[str] = Field(default_factory=list)
    
    # Additional info
    cashless_approved: bool = False
    network_discount: float = 0
    notes: Optional[str] = None
    next_steps: Optional[str] = None
    
    # Sub-results for transparency
    eligibility_result: Optional[EligibilityResult] = None
    coverage_result: Optional[CoverageResult] = None
    limit_result: Optional[LimitResult] = None
    fraud_result: Optional[FraudCheckResult] = None


class AppealRequest(BaseModel):
    """Request to appeal a claim decision."""
    reason: str = Field(..., min_length=10, description="Reason for appeal")
    additional_documents: List[str] = Field(default_factory=list)


class AppealResponse(BaseModel):
    """Response for appeal submission."""
    claim_id: str
    appeal_id: str
    status: str = "UNDER_REVIEW"
    message: str
