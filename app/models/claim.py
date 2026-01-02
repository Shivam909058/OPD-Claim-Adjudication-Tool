"""
Claim-related Pydantic models for OPD Claim Adjudication Tool.
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class ClaimStatus(str, Enum):
    """Status of a claim in the system."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PARTIAL = "PARTIAL"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class ClaimCategory(str, Enum):
    """Categories of OPD claims."""
    CONSULTATION = "consultation"
    DIAGNOSTIC = "diagnostic"
    PHARMACY = "pharmacy"
    DENTAL = "dental"
    VISION = "vision"
    ALTERNATIVE_MEDICINE = "alternative_medicine"


class PrescriptionData(BaseModel):
    """Extracted prescription data."""
    doctor_name: Optional[str] = None
    doctor_reg: Optional[str] = None
    diagnosis: Optional[str] = None
    medicines_prescribed: List[str] = Field(default_factory=list)
    tests_prescribed: List[str] = Field(default_factory=list)
    procedures: List[str] = Field(default_factory=list)
    treatment: Optional[str] = None
    prescription_date: Optional[str] = None


class BillData(BaseModel):
    """Extracted bill data."""
    consultation_fee: float = 0
    diagnostic_tests: float = 0
    medicines: float = 0
    procedures: float = 0
    test_names: List[str] = Field(default_factory=list)
    total_amount: float = 0
    hospital_name: Optional[str] = None
    bill_date: Optional[str] = None
    bill_number: Optional[str] = None
    
    # Specific category amounts
    root_canal: float = 0
    teeth_whitening: float = 0
    mri_scan: float = 0
    therapy_charges: float = 0
    diet_plan: float = 0


class ClaimDocument(BaseModel):
    """Document attached to a claim."""
    prescription: Optional[PrescriptionData] = None
    bill: Optional[BillData] = None
    diagnostic_reports: List[str] = Field(default_factory=list)


class ClaimSubmission(BaseModel):
    """Input model for claim submission."""
    member_id: str = Field(..., description="Employee/Member ID")
    member_name: str = Field(..., description="Name of the claimant")
    treatment_date: str = Field(..., description="Date of treatment (YYYY-MM-DD)")
    claim_amount: float = Field(..., gt=0, description="Total claim amount in INR")
    hospital: Optional[str] = Field(None, description="Hospital/Clinic name")
    cashless_request: bool = Field(False, description="Request for cashless facility")
    category: Optional[ClaimCategory] = Field(None, description="Claim category")
    documents: ClaimDocument = Field(..., description="Submitted documents")
    
    # Optional fields for eligibility checking
    member_join_date: Optional[str] = Field(None, description="Date member joined policy")
    previous_claims_same_day: int = Field(0, description="Number of previous claims on same day")
    previous_claims_ytd: float = Field(0, description="Total claims amount year-to-date")


class ExtractedData(BaseModel):
    """All data extracted from submitted documents."""
    claim_id: str
    member_id: str
    member_name: str
    treatment_date: str
    claim_amount: float
    
    # Extracted from prescription
    doctor_name: Optional[str] = None
    doctor_registration: Optional[str] = None
    diagnosis: Optional[str] = None
    medicines: List[str] = Field(default_factory=list)
    tests: List[str] = Field(default_factory=list)
    procedures: List[str] = Field(default_factory=list)
    
    # Extracted from bill
    consultation_fee: float = 0
    diagnostic_amount: float = 0
    pharmacy_amount: float = 0
    procedure_amount: float = 0
    
    # Hospital info
    hospital_name: Optional[str] = None
    is_network_hospital: bool = False
    
    # Validation flags
    has_prescription: bool = False
    has_bill: bool = False
    has_valid_doctor_reg: bool = False
    dates_match: bool = True
    
    # Raw data
    raw_documents: Optional[Dict[str, Any]] = None


class ClaimResponse(BaseModel):
    """Response model for claim operations."""
    claim_id: str
    status: ClaimStatus
    message: str
    created_at: datetime = Field(default_factory=datetime.now)
    extracted_data: Optional[ExtractedData] = None
    decision: Optional[Dict[str, Any]] = None


class ClaimListItem(BaseModel):
    """Summary item for claims list."""
    claim_id: str
    member_id: str
    member_name: str
    treatment_date: str
    claim_amount: float
    status: ClaimStatus
    approved_amount: Optional[float] = None
    created_at: datetime


class ClaimHistory(BaseModel):
    """Response for claims history."""
    total_claims: int
    claims: List[ClaimListItem]
