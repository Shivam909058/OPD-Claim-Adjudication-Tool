"""
Claim Adjudication Workflow
Orchestrates all agents to process and adjudicate OPD claims.
"""

import uuid
import json
from datetime import datetime
from typing import Dict, Any, Optional

from agno.workflow import Workflow
from agno.agent import Agent

from app.agents.document_extractor import extract_document_data
from app.agents.eligibility_checker import check_eligibility_with_agent
from app.agents.coverage_validator import validate_coverage_with_agent
from app.agents.limit_calculator import calculate_limits_with_agent
from app.agents.decision_maker import make_decision_with_agent

from app.models.claim import ClaimSubmission, ClaimResponse, ClaimStatus
from app.models.decision import AdjudicationResult, DecisionType


def generate_claim_id() -> str:
    """Generate a unique claim ID."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_id = str(uuid.uuid4())[:8].upper()
    return f"CLM_{timestamp}_{unique_id}"


class ClaimAdjudicationWorkflow:
    """
    Workflow that orchestrates the claim adjudication process.
    
    Steps:
    1. Document Extraction - Extract data from submitted documents
    2. Eligibility Check - Verify policy status and waiting periods
    3. Coverage Validation - Check if treatment is covered
    4. Limit Calculation - Calculate approved amount
    5. Final Decision - Make adjudication decision
    """
    
    def __init__(self):
        self.workflow_id = "claim-adjudication"
        self.name = "Claim Adjudication Workflow"
    
    def process(self, claim_data: Dict[str, Any]) -> AdjudicationResult:
        """
        Process a claim through the adjudication workflow.
        
        Args:
            claim_data: The claim submission data.
        
        Returns:
            AdjudicationResult with the final decision.
        """
        # Generate claim ID if not provided
        claim_id = claim_data.get("claim_id") or generate_claim_id()
        
        print(f"\n{'='*60}")
        print(f"Processing Claim: {claim_id}")
        print(f"{'='*60}")
        
        # Step 1: Document Extraction
        print("\n📄 Step 1: Extracting document data...")
        extraction_result = extract_document_data(claim_data)
        print(f"   ✓ Extraction complete. Has prescription: {extraction_result.get('has_prescription')}, Has bill: {extraction_result.get('has_bill')}")
        
        # Check for missing documents
        if not extraction_result.get("has_prescription"):
            return AdjudicationResult(
                claim_id=claim_id,
                decision=DecisionType.REJECTED,
                approved_amount=0,
                rejection_reasons=["MISSING_DOCUMENTS"],
                confidence_score=1.0,
                notes="Prescription from registered doctor is required",
                next_steps="Please submit a valid prescription from a registered medical practitioner.",
            )
        
        if not extraction_result.get("has_bill"):
            return AdjudicationResult(
                claim_id=claim_id,
                decision=DecisionType.REJECTED,
                approved_amount=0,
                rejection_reasons=["MISSING_DOCUMENTS"],
                confidence_score=1.0,
                notes="Medical bill/invoice is required",
                next_steps="Please submit the original bill or invoice for the treatment.",
            )
        
        # Step 2: Eligibility Check
        print("\n✅ Step 2: Checking eligibility...")
        eligibility_result = check_eligibility_with_agent(claim_data, extraction_result)
        print(f"   ✓ Eligibility: {'Passed' if eligibility_result.get('is_eligible') else 'Failed'}")
        
        # If not eligible, reject immediately
        if not eligibility_result.get("is_eligible"):
            return AdjudicationResult(
                claim_id=claim_id,
                decision=DecisionType.REJECTED,
                approved_amount=0,
                rejection_reasons=eligibility_result.get("rejection_reasons", []),
                confidence_score=eligibility_result.get("confidence_score", 0.95),
                notes=eligibility_result.get("notes", "Eligibility check failed"),
                next_steps=f"Eligible from: {eligibility_result.get('waiting_period_end_date', 'N/A')}" if eligibility_result.get("waiting_period_end_date") else "Please contact support.",
                eligibility_result=eligibility_result,
            )
        
        # Step 3: Coverage Validation
        print("\n🔍 Step 3: Validating coverage...")
        coverage_result = validate_coverage_with_agent(claim_data, extraction_result)
        print(f"   ✓ Coverage: {'Covered' if coverage_result.get('is_covered') else 'Issues found'}")
        if coverage_result.get("excluded_items"):
            print(f"   ⚠ Excluded items: {coverage_result.get('excluded_items')}")
        
        # Step 4: Limit Calculation
        print("\n💰 Step 4: Calculating limits...")
        limit_result = calculate_limits_with_agent(claim_data, extraction_result, coverage_result)
        print(f"   ✓ Within limits: {limit_result.get('within_limits')}")
        print(f"   ✓ Approved amount: ₹{limit_result.get('approved_amount', 0)}")
        
        # Step 5: Final Decision
        print("\n⚖️ Step 5: Making final decision...")
        decision_result = make_decision_with_agent(
            claim_id=claim_id,
            claim_data=claim_data,
            extraction_result=extraction_result,
            eligibility_result=eligibility_result,
            coverage_result=coverage_result,
            limit_result=limit_result,
        )
        
        print(f"\n{'='*60}")
        print(f"Decision: {decision_result.decision.value}")
        print(f"Approved Amount: ₹{decision_result.approved_amount}")
        print(f"Confidence: {decision_result.confidence_score}")
        print(f"{'='*60}\n")
        
        return decision_result


# Create workflow instance
claim_workflow = ClaimAdjudicationWorkflow()


def process_claim(claim_submission: Dict[str, Any]) -> AdjudicationResult:
    """
    Process a claim submission through the adjudication workflow.
    
    This is the main entry point for claim processing.
    
    Args:
        claim_submission: Dict containing:
            - member_id: str
            - member_name: str
            - treatment_date: str (YYYY-MM-DD)
            - claim_amount: float
            - documents: Dict with prescription and bill data
            - hospital: Optional[str]
            - cashless_request: bool
            - member_join_date: Optional[str]
            - previous_claims_same_day: int
            - previous_claims_ytd: float
    
    Returns:
        AdjudicationResult with decision, approved amount, and details.
    
    Example:
        result = process_claim({
            "member_id": "EMP001",
            "member_name": "Rajesh Kumar",
            "treatment_date": "2024-11-01",
            "claim_amount": 1500,
            "documents": {
                "prescription": {
                    "doctor_name": "Dr. Sharma",
                    "doctor_reg": "KA/45678/2015",
                    "diagnosis": "Viral fever",
                    "medicines_prescribed": ["Paracetamol 650mg"]
                },
                "bill": {
                    "consultation_fee": 1000,
                    "diagnostic_tests": 500
                }
            }
        })
    """
    return claim_workflow.process(claim_submission)


async def process_claim_async(claim_submission: Dict[str, Any]) -> AdjudicationResult:
    """
    Async version of process_claim for use with FastAPI.
    
    Args:
        claim_submission: The claim submission data.
    
    Returns:
        AdjudicationResult with the final decision.
    """
    # For now, just call the sync version
    # In production, you'd want to make the agent calls async
    return process_claim(claim_submission)


def format_result_for_api(result: AdjudicationResult) -> Dict[str, Any]:
    """
    Format the adjudication result for API response.
    
    Args:
        result: The AdjudicationResult object.
    
    Returns:
        Dict suitable for JSON serialization.
    """
    return {
        "claim_id": result.claim_id,
        "decision": result.decision.value,
        "approved_amount": result.approved_amount,
        "deductions": result.deductions,
        "rejected_items": result.rejected_items,
        "rejection_reasons": result.rejection_reasons,
        "confidence_score": result.confidence_score,
        "fraud_flags": result.fraud_flags,
        "cashless_approved": result.cashless_approved,
        "network_discount": result.network_discount,
        "notes": result.notes,
        "next_steps": result.next_steps,
    }
