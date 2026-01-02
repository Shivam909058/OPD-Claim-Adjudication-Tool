"""
Main FastAPI Application with AgentOS
OPD Claim Adjudication Tool Backend
"""

import json
from datetime import datetime
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Query, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import settings
from app.database.db import (
    init_db,
    get_db,
    close_db,
    create_claim,
    get_claim,
    get_all_claims,
    get_claims_by_member,
    update_claim_decision,
    get_claims_ytd,
    get_claims_same_day,
    ClaimRecord,
)
from app.models.claim import ClaimSubmission, ClaimResponse, ClaimStatus, ClaimListItem, ClaimHistory
from app.models.decision import AdjudicationResult, DecisionType, AppealRequest, AppealResponse
from app.workflows.claim_adjudication import process_claim, generate_claim_id, format_result_for_api


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    print("🚀 Starting OPD Claim Adjudication Tool...")
    init_db()
    print("✅ Database initialized")
    yield
    print("👋 Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="OPD Claim Adjudication API",
    description="""
    AI-powered OPD Insurance Claim Adjudication System
    
    This API processes Outpatient Department (OPD) insurance claims using AI agents to:
    - Extract data from medical documents
    - Validate eligibility and coverage
    - Calculate approved amounts
    - Make intelligent adjudication decisions
    
    Built with Agno AI Framework and FastAPI.
    """,
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== API Models ====================

class ClaimSubmissionRequest(BaseModel):
    """Request model for claim submission."""
    member_id: str
    member_name: str
    treatment_date: str
    claim_amount: float
    hospital: Optional[str] = None
    cashless_request: bool = False
    category: Optional[str] = None
    member_join_date: Optional[str] = None
    documents: dict  # Contains prescription and bill data
    previous_claims_same_day: Optional[int] = None  # For testing fraud detection
    
    class Config:
        json_schema_extra = {
            "example": {
                "member_id": "EMP001",
                "member_name": "Rajesh Kumar",
                "treatment_date": "2024-11-01",
                "claim_amount": 1500,
                "hospital": "Apollo Hospitals",
                "cashless_request": False,
                "documents": {
                    "prescription": {
                        "doctor_name": "Dr. Sharma",
                        "doctor_reg": "KA/45678/2015",
                        "diagnosis": "Viral fever",
                        "medicines_prescribed": ["Paracetamol 650mg", "Vitamin C"]
                    },
                    "bill": {
                        "consultation_fee": 1000,
                        "diagnostic_tests": 500,
                        "test_names": ["CBC", "Dengue test"]
                    }
                }
            }
        }


class ClaimDecisionResponse(BaseModel):
    """Response model for claim decision."""
    claim_id: str
    decision: str
    approved_amount: float
    deductions: dict
    rejected_items: List[str]
    rejection_reasons: List[str]
    confidence_score: float
    fraud_flags: List[str]
    cashless_approved: bool
    network_discount: float
    notes: str
    next_steps: str
    created_at: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    timestamp: str


# ==================== API Endpoints ====================

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API info."""
    return {
        "name": "OPD Claim Adjudication API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "submit_claim": "POST /api/claims/submit",
            "get_claim": "GET /api/claims/{claim_id}",
            "list_claims": "GET /api/claims",
            "health": "GET /health",
        }
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.now().isoformat()
    )


@app.post("/api/claims/submit", response_model=ClaimDecisionResponse, tags=["Claims"])
async def submit_claim(request: ClaimSubmissionRequest):
    """
    Submit a new OPD claim for adjudication.
    
    The claim will be processed through the AI-powered adjudication workflow:
    1. Document data extraction
    2. Eligibility verification
    3. Coverage validation
    4. Limit calculation
    5. Final decision
    
    Returns the adjudication decision with approved amount and details.
    """
    try:
        # Get database session
        db = get_db()
        
        # Generate claim ID
        claim_id = generate_claim_id()
        
        # Check for previous claims (for fraud detection)
        # Use provided value for testing, or query DB for actual count
        if request.previous_claims_same_day is not None:
            previous_same_day = request.previous_claims_same_day
        else:
            previous_same_day = get_claims_same_day(db, request.member_id, request.treatment_date)
        previous_ytd = get_claims_ytd(db, request.member_id, datetime.now().year)
        
        # Prepare claim data
        claim_data = {
            "claim_id": claim_id,
            "member_id": request.member_id,
            "member_name": request.member_name,
            "treatment_date": request.treatment_date,
            "claim_amount": request.claim_amount,
            "hospital": request.hospital,
            "cashless_request": request.cashless_request,
            "category": request.category,
            "member_join_date": request.member_join_date,
            "documents": request.documents,
            "previous_claims_same_day": previous_same_day,
            "previous_claims_ytd": previous_ytd,
        }
        
        # Create initial claim record
        create_claim(db, claim_data)
        
        # Process claim through workflow
        result = process_claim(claim_data)
        
        # Update claim with decision
        update_claim_decision(
            db=db,
            claim_id=claim_id,
            decision=result.decision.value,
            approved_amount=result.approved_amount,
            rejection_reasons=result.rejection_reasons,
            rejected_items=result.rejected_items,
            confidence_score=result.confidence_score,
            notes=result.notes,
            next_steps=result.next_steps,
            fraud_flags=result.fraud_flags,
            copay_amount=result.deductions.get("copay", 0),
            network_discount=result.network_discount,
            excluded_amount=result.deductions.get("excluded_items", 0),
        )
        
        close_db(db)
        
        # Return response
        return ClaimDecisionResponse(
            claim_id=claim_id,
            decision=result.decision.value,
            approved_amount=result.approved_amount,
            deductions=result.deductions,
            rejected_items=result.rejected_items,
            rejection_reasons=result.rejection_reasons,
            confidence_score=result.confidence_score,
            fraud_flags=result.fraud_flags,
            cashless_approved=result.cashless_approved,
            network_discount=result.network_discount,
            notes=result.notes,
            next_steps=result.next_steps,
            created_at=datetime.now().isoformat(),
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing claim: {str(e)}")


@app.get("/api/claims/{claim_id}", tags=["Claims"])
async def get_claim_by_id(claim_id: str):
    """
    Get details of a specific claim by ID.
    
    Returns the claim details including decision, approved amount, and all metadata.
    """
    db = get_db()
    claim = get_claim(db, claim_id)
    close_db(db)
    
    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
    
    return claim.to_dict()


@app.get("/api/claims", tags=["Claims"])
async def list_claims(
    member_id: Optional[str] = Query(None, description="Filter by member ID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
):
    """
    List all claims with optional filtering.
    
    Can filter by member_id to get claims for a specific member.
    Supports pagination with skip and limit parameters.
    """
    db = get_db()
    
    if member_id:
        claims = get_claims_by_member(db, member_id)
    else:
        claims = get_all_claims(db, skip=skip, limit=limit)
    
    close_db(db)
    
    return {
        "total_claims": len(claims),
        "claims": [claim.to_dict() for claim in claims]
    }


@app.post("/api/claims/{claim_id}/appeal", tags=["Claims"])
async def submit_appeal(claim_id: str, appeal: AppealRequest):
    """
    Submit an appeal for a rejected claim.
    
    Appeals will be queued for manual review by the claims team.
    """
    db = get_db()
    claim = get_claim(db, claim_id)
    
    if not claim:
        close_db(db)
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
    
    if claim.decision not in ["REJECTED", "PARTIAL"]:
        close_db(db)
        raise HTTPException(status_code=400, detail="Appeals can only be submitted for rejected or partially approved claims")
    
    # Generate appeal ID
    appeal_id = f"APL_{datetime.now().strftime('%Y%m%d%H%M%S')}_{claim_id[-8:]}"
    
    # In a real system, you'd save the appeal to database
    # For now, just update the claim status
    claim.status = "UNDER_APPEAL"
    claim.notes = f"{claim.notes} | Appeal submitted: {appeal.reason}"
    db.commit()
    
    close_db(db)
    
    return AppealResponse(
        claim_id=claim_id,
        appeal_id=appeal_id,
        status="UNDER_REVIEW",
        message="Your appeal has been submitted and will be reviewed within 3-5 business days."
    )


@app.get("/api/policy/terms", tags=["Policy"])
async def get_policy_terms():
    """
    Get the policy terms and coverage details.
    
    Returns the complete policy configuration including limits, sub-limits, and exclusions.
    """
    from app.tools.policy_tools import get_policy_terms as load_policy
    return load_policy()


@app.get("/api/policy/exclusions", tags=["Policy"])
async def get_policy_exclusions():
    """Get the list of excluded treatments and conditions."""
    from app.tools.policy_tools import get_exclusions
    return {"exclusions": get_exclusions()}


@app.get("/api/policy/network-hospitals", tags=["Policy"])
async def get_network_hospitals():
    """Get the list of network hospitals."""
    from app.tools.policy_tools import get_network_hospitals
    return {"network_hospitals": get_network_hospitals()}


# ==================== Document OCR Endpoints ====================

@app.post("/api/documents/extract", tags=["Documents"])
async def extract_document_data(
    file: UploadFile = File(...),
    doc_type: str = Form(default="auto", description="Document type: prescription, bill, or auto")
):
    """
    Extract data from uploaded document using OCR.
    
    Supports PDF and image files (JPG, PNG, etc.).
    Returns structured data extracted from prescription or bill.
    """
    try:
        from app.tools.document_ocr import extract_from_bytes
        
        # Validate file type
        allowed_types = ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg', 'image/webp']
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type: {file.content_type}. Allowed: PDF, JPG, PNG"
            )
        
        # Read file content
        file_bytes = await file.read()
        
        # Determine file type for processing
        if file.content_type == 'application/pdf':
            file_type = 'pdf'
        else:
            file_type = file.filename.split('.')[-1] if file.filename else 'jpg'
        
        # Extract data using OCR
        result = extract_from_bytes(file_bytes, file_type, doc_type)
        
        return {
            "success": result.get("success", True),
            "filename": file.filename,
            "doc_type": doc_type,
            "extracted_data": result
        }
        
    except HTTPException:
        raise
    except ImportError as e:
        raise HTTPException(
            status_code=500, 
            detail="OCR libraries not installed. Run: pip install pdfplumber pytesseract easyocr"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document extraction error: {str(e)}")


@app.post("/api/claims/submit-with-docs", tags=["Claims"])
async def submit_claim_with_documents(
    member_id: str = Form(...),
    member_name: str = Form(...),
    treatment_date: str = Form(...),
    claim_amount: float = Form(...),
    hospital: Optional[str] = Form(None),
    cashless_request: bool = Form(False),
    category: Optional[str] = Form(None),
    prescription_file: Optional[UploadFile] = File(None),
    bill_file: Optional[UploadFile] = File(None),
):
    """
    Submit a claim with document uploads.
    
    Documents are processed with OCR to extract prescription and bill data.
    The extracted data is then used for claim adjudication.
    """
    try:
        from app.tools.document_ocr import extract_from_bytes
        
        documents = {"prescription": {}, "bill": {}}
        
        # Process prescription file
        if prescription_file:
            file_bytes = await prescription_file.read()
            file_type = 'pdf' if prescription_file.content_type == 'application/pdf' else 'jpg'
            result = extract_from_bytes(file_bytes, file_type, "prescription")
            
            if result.get("doctor_name"):
                documents["prescription"]["doctor_name"] = result["doctor_name"]
            if result.get("doctor_reg"):
                documents["prescription"]["doctor_reg"] = result["doctor_reg"]
            if result.get("diagnosis"):
                documents["prescription"]["diagnosis"] = result["diagnosis"]
            if result.get("medicines_prescribed"):
                documents["prescription"]["medicines_prescribed"] = result["medicines_prescribed"]
            if result.get("tests_prescribed"):
                documents["prescription"]["tests_prescribed"] = result["tests_prescribed"]
        
        # Process bill file
        if bill_file:
            file_bytes = await bill_file.read()
            file_type = 'pdf' if bill_file.content_type == 'application/pdf' else 'jpg'
            result = extract_from_bytes(file_bytes, file_type, "bill")
            
            if result.get("consultation_fee"):
                documents["bill"]["consultation_fee"] = result["consultation_fee"]
            if result.get("diagnostic_tests"):
                documents["bill"]["diagnostic_tests"] = result["diagnostic_tests"]
            if result.get("medicines"):
                documents["bill"]["medicines"] = result["medicines"]
            if result.get("total_amount"):
                documents["bill"]["total_amount"] = result["total_amount"]
            if result.get("hospital_name"):
                documents["bill"]["hospital_name"] = result["hospital_name"]
        
        # If no documents provided, use empty placeholders
        if not documents["prescription"]:
            documents["prescription"] = {
                "doctor_name": "Not provided",
                "diagnosis": "Not provided"
            }
        if not documents["bill"]:
            documents["bill"] = {
                "total_amount": claim_amount
            }
        
        # Get database session
        db = get_db()
        
        # Generate claim ID
        claim_id = generate_claim_id()
        
        # Check for previous claims
        previous_same_day = get_claims_same_day(db, member_id, treatment_date)
        previous_ytd = get_claims_ytd(db, member_id, datetime.now().year)
        
        # Prepare claim data
        claim_data = {
            "claim_id": claim_id,
            "member_id": member_id,
            "member_name": member_name,
            "treatment_date": treatment_date,
            "claim_amount": claim_amount,
            "hospital": hospital,
            "cashless_request": cashless_request,
            "category": category,
            "documents": documents,
            "previous_claims_same_day": previous_same_day,
            "previous_claims_ytd": previous_ytd,
        }
        
        # Create initial claim record
        create_claim(db, claim_data)
        
        # Process claim through workflow
        result = process_claim(claim_data)
        
        # Update claim with decision
        update_claim_decision(
            db=db,
            claim_id=claim_id,
            decision=result.decision.value,
            approved_amount=result.approved_amount,
            rejection_reasons=result.rejection_reasons,
            rejected_items=result.rejected_items,
            confidence_score=result.confidence_score,
            notes=result.notes,
            next_steps=result.next_steps,
            fraud_flags=result.fraud_flags,
            copay_amount=result.deductions.get("copay", 0),
            network_discount=result.network_discount,
            excluded_amount=result.deductions.get("excluded_items", 0),
        )
        
        close_db(db)
        
        return ClaimDecisionResponse(
            claim_id=claim_id,
            decision=result.decision.value,
            approved_amount=result.approved_amount,
            deductions=result.deductions,
            rejected_items=result.rejected_items,
            rejection_reasons=result.rejection_reasons,
            confidence_score=result.confidence_score,
            fraud_flags=result.fraud_flags,
            cashless_approved=result.cashless_approved,
            network_discount=result.network_discount,
            notes=result.notes,
            next_steps=result.next_steps,
            created_at=datetime.now().isoformat(),
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing claim: {str(e)}")


# ==================== Test Endpoint ====================

@app.post("/api/test/process", tags=["Testing"])
async def test_process_claim(test_case: dict):
    """
    Test endpoint to process a claim without saving to database.
    
    Useful for testing and development.
    """
    try:
        result = process_claim(test_case)
        return format_result_for_api(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.delete("/api/test/reset-database", tags=["Testing"])
async def reset_database():
    """
    Reset the database by deleting all claims.
    
    WARNING: This will delete all claim data. Use only for testing.
    """
    try:
        from app.database.db import engine, Base
        from sqlalchemy import text
        
        db = get_db()
        # Delete all claims
        db.execute(text("DELETE FROM claims"))
        db.commit()
        close_db(db)
        
        return {
            "status": "success",
            "message": "Database reset successfully. All claims deleted."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resetting database: {str(e)}")


# ==================== Run Server ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
