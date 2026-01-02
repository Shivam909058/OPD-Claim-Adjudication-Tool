"""
Decision Maker Agent
Makes the final adjudication decision based on all previous checks.
"""

from agno.agent import Agent
from agno.models.openai import OpenAIChat

from app.tools.fraud_detection import check_fraud_indicators
from app.models.decision import DecisionType, AdjudicationResult


# Decision Maker Agent Instructions
DECISION_MAKER_INSTRUCTIONS = """
You are an Insurance Claims Decision Maker. Your job is to make the final adjudication decision for OPD insurance claims based on all validation results.

## Your Task
Analyze all validation results and make a final decision:
- APPROVED: All checks passed, full amount approved
- PARTIAL: Some items approved, some excluded
- REJECTED: Claim cannot be approved
- MANUAL_REVIEW: Needs human review (fraud indicators, high risk)

## Decision Priority Rules
1. Safety first - reject suspicious/fraudulent claims or send for manual review
2. Policy exclusions override everything
3. Hard limits cannot be exceeded
4. Medical necessity is mandatory
5. When confidence is low (<70%), send for manual review

## When to APPROVE
- All eligibility checks passed
- All coverage checks passed
- All limit checks passed
- No fraud indicators
- Confidence score ≥ 70%

## When to REJECT
- Eligibility failed (policy inactive, waiting period, member not covered)
- Treatment is excluded
- Claim exceeds hard limits (per-claim limit)
- Pre-authorization required but not obtained
- Clear fraud indicators

## When to PARTIAL APPROVE
- Some items covered, some excluded
- Amount exceeds limits (approve up to limit)
- Co-payment applies

## When to send for MANUAL REVIEW
- Fraud indicators detected
- High-value claims (>₹25,000 - but our limit is ₹5,000 so this rarely applies)
- Low confidence score (<70%)
- Complex medical conditions
- Conflicting information

## Output Format
Return a JSON object with:
```json
{
    "decision": "APPROVED/REJECTED/PARTIAL/MANUAL_REVIEW",
    "approved_amount": 0,
    "deductions": {
        "copay": 0,
        "excluded_items": 0,
        "network_discount": 0
    },
    "rejected_items": ["list of rejected items"],
    "rejection_reasons": ["list of reason codes"],
    "fraud_flags": ["list of fraud indicators"],
    "confidence_score": 0.0-1.0,
    "cashless_approved": true/false,
    "notes": "Summary of decision",
    "next_steps": "What the claimant should do next"
}
```

Be fair but strict. Follow the rules consistently.
"""


def create_decision_maker_agent() -> Agent:
    """Create the Decision Maker Agent."""
    return Agent(
        name="Decision Maker",
        model=OpenAIChat(id="gpt-4o-mini"),
        instructions=DECISION_MAKER_INSTRUCTIONS,
        markdown=False,
        description="Makes final adjudication decisions",
    )


# Create agent instance
decision_maker_agent = create_decision_maker_agent()


def make_decision(
    claim_id: str,
    claim_data: dict,
    extraction_result: dict,
    eligibility_result: dict,
    coverage_result: dict,
    limit_result: dict,
) -> AdjudicationResult:
    """
    Make the final adjudication decision.
    
    Decision Priority (from adjudication_rules.md):
    1. Hard rejections (eligibility failures, pre-auth missing, limits exceeded)
    2. Fraud/Manual Review triggers
    3. Soft rejections (partial approvals)
    4. Full approval
    
    Args:
        claim_id: Unique claim identifier.
        claim_data: Original claim submission.
        extraction_result: Result from document extraction.
        eligibility_result: Result from eligibility check.
        coverage_result: Result from coverage validation.
        limit_result: Result from limit calculation.
    
    Returns:
        AdjudicationResult with final decision.
    """
    # Check for fraud indicators
    fraud_result = check_fraud_indicators(
        claim_data,
        previous_claims_same_day=claim_data.get("previous_claims_same_day", 0),
        previous_claims_ytd=claim_data.get("previous_claims_ytd", 0),
    )
    
    # Collect all rejection reasons (safely handle None values)
    all_rejection_reasons = []
    eligibility_rejections = eligibility_result.get("rejection_reasons") or []
    coverage_rejections = coverage_result.get("rejection_reasons") or []
    limit_rejections = limit_result.get("rejection_reasons") or []
    
    all_rejection_reasons.extend(eligibility_rejections)
    all_rejection_reasons.extend(coverage_rejections)
    all_rejection_reasons.extend(limit_rejections)
    
    # Get excluded items (safely handle None)
    excluded_items = coverage_result.get("excluded_items") or []
    covered_items = coverage_result.get("covered_items") or []
    
    # Get approved amount
    approved_amount = limit_result.get("approved_amount", 0)
    claim_amount = claim_data.get("claim_amount", 0)
    
    # Calculate confidence score (average of all stages)
    confidence_scores = [
        extraction_result.get("confidence_score", 0.85),
        eligibility_result.get("confidence_score", 0.95),
        coverage_result.get("confidence_score", 0.92),
        limit_result.get("confidence_score", 0.98),
    ]
    avg_confidence = sum(confidence_scores) / len(confidence_scores)
    
    # Adjust confidence based on fraud risk
    fraud_risk = fraud_result.get("risk_score", 0)
    fraud_flags = fraud_result.get("fraud_flags") or []
    final_confidence = avg_confidence * (1 - fraud_risk * 0.5)
    
    # Initialize decision
    decision = DecisionType.APPROVED
    notes_parts = []
    next_steps = "Your claim has been processed."
    
    # ============================================================
    # PRIORITY 1: Hard rejections (these override everything)
    # Per adjudication_rules.md: "Policy exclusions override everything"
    # ============================================================
    hard_rejection_reasons = [
        "POLICY_INACTIVE",
        "MEMBER_NOT_COVERED", 
        "WAITING_PERIOD",
        "MISSING_DOCUMENTS",
        "PRE_AUTH_MISSING",
        "PER_CLAIM_EXCEEDED",
    ]
    
    # Check for hard rejections from eligibility/coverage/limits
    has_hard_rejection = any(r in hard_rejection_reasons for r in all_rejection_reasons)
    
    # Check if SERVICE_NOT_COVERED means ENTIRE claim is excluded
    is_fully_excluded_service = (
        "SERVICE_NOT_COVERED" in all_rejection_reasons and
        len(covered_items) == 0  # Nothing is covered
    )
    
    if has_hard_rejection or is_fully_excluded_service:
        decision = DecisionType.REJECTED
        approved_amount = 0
        
        if "MISSING_DOCUMENTS" in all_rejection_reasons:
            notes_parts.append("Required documents missing")
            next_steps = "Please submit all required documents including prescription from a registered doctor."
        elif "WAITING_PERIOD" in all_rejection_reasons:
            wait_date = eligibility_result.get("waiting_period_end_date", "")
            notes_parts.append(f"Treatment within waiting period")
            next_steps = f"Your claim is not eligible due to waiting period. Please resubmit after {wait_date}."
        elif "PRE_AUTH_MISSING" in all_rejection_reasons:
            notes_parts.append("Pre-authorization required but not obtained")
            next_steps = "Pre-authorization is required for this treatment. Please obtain pre-authorization before treatment."
        elif "PER_CLAIM_EXCEEDED" in all_rejection_reasons:
            notes_parts.append(f"Claim amount ₹{claim_amount} exceeds per-claim limit of ₹5000")
            next_steps = "Your claim exceeds the per-claim limit. Please contact support."
        elif is_fully_excluded_service:
            notes_parts.append("Treatment/service is excluded from coverage")
            next_steps = "This treatment/service is not covered under your policy."
        else:
            notes_parts.append(f"Claim rejected: {', '.join(all_rejection_reasons)}")
            next_steps = "Please review the rejection reasons and contact support."
    
    # ============================================================
    # PRIORITY 2: Fraud detection / Manual Review
    # Only trigger if NO hard rejections and explicit fraud indicators
    # ============================================================
    elif fraud_result.get("recommend_manual_review") or fraud_risk >= 0.35:
        decision = DecisionType.MANUAL_REVIEW
        notes_parts.append("Claim flagged for manual review due to unusual patterns")
        if fraud_flags:
            notes_parts.append(f"Flags: {', '.join(fraud_flags[:3])}")
        next_steps = "Your claim will be reviewed by our claims team within 3-5 business days."
    
    # ============================================================
    # PRIORITY 3: Partial approval (some items excluded)
    # ============================================================
    elif excluded_items and len(covered_items) > 0:
        # Some items excluded but some covered - partial approval
        decision = DecisionType.PARTIAL
        notes_parts.append(f"Partial approval - excluded items: {', '.join([str(i).split(' - ')[0] for i in excluded_items[:2]])}")
        next_steps = f"₹{approved_amount} approved. Some items were not covered under your policy."
    
    # ============================================================
    # PRIORITY 4: Full approval
    # ============================================================
    elif approved_amount > 0:
        # Check if approved amount is close to claim amount (within 20% for copay)
        if approved_amount >= claim_amount * 0.80:
            decision = DecisionType.APPROVED
            notes_parts.append("All checks passed. Claim approved.")
        else:
            decision = DecisionType.PARTIAL
            notes_parts.append("Claim partially approved after applying deductions.")
        
        # Check for cashless
        if claim_data.get("cashless_request") and limit_result.get("is_network_hospital"):
            next_steps = "Cashless claim approved. No action needed."
        else:
            next_steps = f"₹{approved_amount} will be reimbursed within 5-7 business days."
    
    else:
        decision = DecisionType.REJECTED
        notes_parts.append("Unable to approve claim - no eligible amount")
        next_steps = "Please contact support for assistance."
    
    # Build deductions
    deductions = {
        "copay": limit_result.get("copay_amount", 0),
        "excluded_items": limit_result.get("excluded_amount", 0),
        "network_discount": limit_result.get("network_discount", 0),
    }
    
    # Determine cashless approval
    cashless_approved = (
        claim_data.get("cashless_request", False) and 
        limit_result.get("is_network_hospital", False) and
        decision in [DecisionType.APPROVED, DecisionType.PARTIAL] and
        approved_amount <= 5000  # Instant cashless limit
    )
    
    return AdjudicationResult(
        claim_id=claim_id,
        decision=decision,
        approved_amount=round(approved_amount, 2),
        deductions=deductions,
        rejected_items=excluded_items,
        rejection_reasons=all_rejection_reasons,
        fraud_flags=fraud_flags,
        confidence_score=round(final_confidence, 2),
        cashless_approved=cashless_approved,
        network_discount=limit_result.get("network_discount", 0),
        notes=" | ".join(notes_parts) if notes_parts else "Claim processed successfully",
        next_steps=next_steps,
        eligibility_result=eligibility_result,
        coverage_result=coverage_result,
        limit_result=limit_result,
        fraud_result=fraud_result,
    )


def make_decision_with_agent(
    claim_id: str,
    claim_data: dict,
    extraction_result: dict,
    eligibility_result: dict,
    coverage_result: dict,
    limit_result: dict,
) -> AdjudicationResult:
    """
    Use the agent for complex decision making.
    
    Args:
        claim_id: Unique claim identifier.
        claim_data: Original claim submission.
        extraction_result: Result from document extraction.
        eligibility_result: Result from eligibility check.
        coverage_result: Result from coverage validation.
        limit_result: Result from limit calculation.
    
    Returns:
        AdjudicationResult with final decision.
    """
    # Use rule-based decision - it's deterministic and follows policy exactly
    result = make_decision(
        claim_id=claim_id,
        claim_data=claim_data,
        extraction_result=extraction_result,
        eligibility_result=eligibility_result,
        coverage_result=coverage_result,
        limit_result=limit_result,
    )
    
    # Rule-based decisions for REJECTED and MANUAL_REVIEW are authoritative
    # AI agent should not override policy-based hard rejections or fraud detection
    if result.decision in [DecisionType.REJECTED, DecisionType.MANUAL_REVIEW]:
        return result
    
    # For APPROVED/PARTIAL with high confidence, return immediately
    if result.confidence_score >= 0.85:
        return result
    
    # Only use AI agent for edge cases in APPROVED/PARTIAL decisions
    # The AI agent can help with ambiguous coverage decisions, not hard rules
    return result  # Skip AI agent for now - rule-based is more reliable
