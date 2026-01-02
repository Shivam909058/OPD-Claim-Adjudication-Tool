"""
Limit Calculator Agent
Calculates approved amounts, co-pays, and validates against policy limits.
"""

from agno.agent import Agent
from agno.models.openai import OpenAIChat

from app.tools.policy_tools import (
    get_annual_limit,
    get_per_claim_limit,
    get_sub_limits,
    calculate_copay,
    is_network_hospital,
    get_minimum_claim_amount,
)


# Limit Calculator Agent Instructions
LIMIT_CALCULATOR_INSTRUCTIONS = """
You are an Insurance Limit Calculator. Your job is to calculate the approved amount for a claim based on policy limits, co-payments, and deductions.

## Your Task
Calculate the final approved amount considering:
1. Per-claim limit (₹5,000)
2. Annual limit (₹50,000)
3. Category sub-limits
4. Co-payment percentages
5. Network discounts
6. Excluded amounts

## Policy Limits
- Annual Limit: ₹50,000
- Per-Claim Limit: ₹5,000
- Family Floater Limit: ₹1,50,000

## Sub-Limits by Category
- Consultation: ₹2,000 (10% co-pay, 20% network discount)
- Diagnostic Tests: ₹10,000
- Pharmacy: ₹15,000 (30% co-pay for branded drugs)
- Dental: ₹10,000 (routine checkup: ₹2,000)
- Vision: ₹5,000
- Alternative Medicine: ₹8,000

## Calculation Rules
1. First check if claim amount exceeds per-claim limit
2. Check if YTD claims + current claim exceeds annual limit
3. Check category sub-limits
4. Apply co-payment deduction
5. Apply network discount (if network hospital)
6. Deduct excluded items

## Output Format
Return a JSON object with:
```json
{
    "within_limits": true/false,
    "claim_amount": 0,
    "approved_amount": 0,
    "copay_amount": 0,
    "copay_percentage": 0,
    "network_discount": 0,
    "excluded_amount": 0,
    "per_claim_limit": 5000,
    "annual_limit": 50000,
    "applicable_sub_limit": 0,
    "remaining_annual_limit": 0,
    "per_claim_exceeded": true/false,
    "annual_limit_exceeded": true/false,
    "sub_limit_exceeded": true/false,
    "rejection_reasons": ["PER_CLAIM_EXCEEDED", "ANNUAL_LIMIT_EXCEEDED", "SUB_LIMIT_EXCEEDED"],
    "deductions_breakdown": {
        "copay": 0,
        "network_discount": 0,
        "excluded_items": 0
    },
    "notes": "Calculation explanation",
    "confidence_score": 0.0-1.0
}
```

Be precise with calculations - amounts matter!
"""


def create_limit_calculator_agent() -> Agent:
    """Create the Limit Calculator Agent."""
    return Agent(
        name="Limit Calculator",
        model=OpenAIChat(id="gpt-4o-mini"),
        instructions=LIMIT_CALCULATOR_INSTRUCTIONS,
        markdown=False,
        description="Calculates approved amounts and validates limits",
    )


# Create agent instance
limit_calculator_agent = create_limit_calculator_agent()


def calculate_limits(
    claim_amount: float,
    category: str = None,
    hospital_name: str = None,
    excluded_amount: float = 0,
    previous_claims_ytd: float = 0,
    sub_limit: float = None,
) -> dict:
    """
    Calculate approved amount based on limits.
    
    Args:
        claim_amount: Total claim amount.
        category: Claim category.
        hospital_name: Hospital name (for network check).
        excluded_amount: Amount to be excluded.
        previous_claims_ytd: Previous claims total for the year.
        sub_limit: Override sub-limit if known.
    
    Returns:
        Dict with limit calculation result.
    """
    # Get policy limits
    per_claim_limit = get_per_claim_limit()  # ₹5,000
    annual_limit = get_annual_limit()  # ₹50,000
    min_claim_amount = get_minimum_claim_amount()  # ₹500
    
    # Check minimum claim amount
    if claim_amount < min_claim_amount:
        return {
            "within_limits": False,
            "claim_amount": claim_amount,
            "approved_amount": 0,
            "rejection_reasons": ["BELOW_MIN_AMOUNT"],
            "notes": f"Claim amount ₹{claim_amount} is below minimum threshold of ₹{min_claim_amount}",
            "confidence_score": 1.0,
        }
    
    # Initialize
    rejection_reasons = []
    per_claim_exceeded = False
    annual_limit_exceeded = False
    sub_limit_exceeded = False
    
    # Calculate eligible amount (after exclusions)
    eligible_amount = claim_amount - excluded_amount
    
    # Get sub-limit for category
    if sub_limit is None:
        if category:
            sub_limit_info = get_sub_limits(category)
            sub_limit = sub_limit_info.get("limit", per_claim_limit)
        else:
            sub_limit = per_claim_limit
    
    # Check per-claim limit
    if eligible_amount > per_claim_limit:
        per_claim_exceeded = True
        rejection_reasons.append("PER_CLAIM_EXCEEDED")
    
    # Check annual limit
    remaining_annual = annual_limit - previous_claims_ytd
    if eligible_amount > remaining_annual:
        annual_limit_exceeded = True
        rejection_reasons.append("ANNUAL_LIMIT_EXCEEDED")
    
    # Check sub-limit
    if eligible_amount > sub_limit:
        sub_limit_exceeded = True
        # Don't add rejection for sub-limit, just cap the amount
    
    # Calculate approved amount (cap at all applicable limits)
    approved_amount = min(eligible_amount, per_claim_limit, remaining_annual, sub_limit)
    approved_amount = max(approved_amount, 0)  # Can't be negative
    
    # Check if network hospital for discount
    is_network = is_network_hospital(hospital_name) if hospital_name else False
    
    # Calculate co-pay and discounts
    copay_info = calculate_copay(approved_amount, category or "consultation", is_network)
    
    copay_amount = copay_info["copay_amount"]
    network_discount = copay_info["network_discount"]
    
    # Final approved amount after co-pay
    final_approved = approved_amount - copay_amount
    
    # If network hospital, the discount is a benefit, not a deduction from approved amount
    # The approved amount stays the same, but effective cost to insurance is less
    
    # Determine if within limits
    within_limits = len(rejection_reasons) == 0
    
    # Generate notes
    notes_parts = []
    if per_claim_exceeded:
        notes_parts.append(f"Claim amount ₹{claim_amount} exceeds per-claim limit of ₹{per_claim_limit}")
    if annual_limit_exceeded:
        notes_parts.append(f"Annual limit exceeded. Remaining: ₹{remaining_annual}")
    if sub_limit_exceeded:
        notes_parts.append(f"Sub-limit for {category} is ₹{sub_limit}")
    if excluded_amount > 0:
        notes_parts.append(f"Excluded amount: ₹{excluded_amount}")
    if copay_amount > 0:
        notes_parts.append(f"Co-pay ({copay_info['copay_percentage']}%): ₹{copay_amount}")
    if is_network:
        notes_parts.append(f"Network hospital discount: ₹{network_discount}")
    
    notes = ". ".join(notes_parts) if notes_parts else "All amounts within limits"
    
    return {
        "within_limits": within_limits,
        "claim_amount": claim_amount,
        "eligible_amount": eligible_amount,
        "approved_amount": round(final_approved, 2),
        "copay_amount": round(copay_amount, 2),
        "copay_percentage": copay_info["copay_percentage"],
        "network_discount": round(network_discount, 2),
        "excluded_amount": excluded_amount,
        "per_claim_limit": per_claim_limit,
        "annual_limit": annual_limit,
        "applicable_sub_limit": sub_limit,
        "remaining_annual_limit": round(remaining_annual, 2),
        "per_claim_exceeded": per_claim_exceeded,
        "annual_limit_exceeded": annual_limit_exceeded,
        "sub_limit_exceeded": sub_limit_exceeded,
        "is_network_hospital": is_network,
        "rejection_reasons": rejection_reasons,
        "deductions_breakdown": {
            "copay": round(copay_amount, 2),
            "network_discount": round(network_discount, 2),
            "excluded_items": excluded_amount,
        },
        "notes": notes,
        "confidence_score": 0.98,
    }


def calculate_limits_with_agent(
    claim_data: dict,
    extracted_data: dict,
    coverage_result: dict,
) -> dict:
    """
    Use the agent for complex limit calculations.
    
    Args:
        claim_data: Original claim submission.
        extracted_data: Data extracted from documents.
        coverage_result: Result from coverage validation.
    
    Returns:
        Dict with limit calculation result.
    """
    import json
    
    # Get relevant data
    claim_amount = claim_data.get("claim_amount", 0)
    hospital_name = claim_data.get("hospital")
    previous_claims_ytd = claim_data.get("previous_claims_ytd", 0)
    
    # Calculate excluded amount from coverage result (safely handle None)
    excluded_items = coverage_result.get("excluded_items") or []
    excluded_amount = 0
    
    # Get bill details to calculate excluded amounts
    documents = claim_data.get("documents", {})
    bill = documents.get("bill", {})
    
    # Map excluded items to amounts
    for item in excluded_items:
        if not item:
            continue
        item_lower = str(item).lower()
        if "whitening" in item_lower or "teeth whitening" in item_lower:
            excluded_amount += bill.get("teeth_whitening", 0)
        elif "diet" in item_lower:
            excluded_amount += bill.get("diet_plan", 0)
        elif "cosmetic" in item_lower:
            # Generic cosmetic exclusion
            excluded_amount += bill.get("teeth_whitening", 0) + bill.get("cosmetic", 0)
    
    # Get category from coverage result
    category = coverage_result.get("category")
    sub_limit = coverage_result.get("applicable_sub_limit")
    
    # Do rule-based calculation
    result = calculate_limits(
        claim_amount=claim_amount,
        category=category,
        hospital_name=hospital_name,
        excluded_amount=excluded_amount,
        previous_claims_ytd=previous_claims_ytd,
        sub_limit=sub_limit,
    )
    
    # If clear rejection, return immediately
    if not result["within_limits"] and result["per_claim_exceeded"]:
        return result
    
    # For complex cases with partial approvals, use agent
    if excluded_amount > 0 or result["sub_limit_exceeded"]:
        prompt = f"""
Calculate the approved amount for this claim:

Claim Amount: ₹{claim_amount}
Category: {category}
Hospital: {hospital_name}
Is Network Hospital: {result['is_network_hospital']}

Excluded Items: {excluded_items}
Excluded Amount: ₹{excluded_amount}

Previous Claims YTD: ₹{previous_claims_ytd}
Remaining Annual Limit: ₹{result['remaining_annual_limit']}

Sub-Limits:
{json.dumps(get_sub_limits(), indent=2)}

Calculate:
1. Eligible amount after exclusions
2. Apply per-claim limit (₹5,000)
3. Apply category sub-limit (₹{sub_limit})
4. Calculate co-pay deduction
5. Apply network discount if applicable
6. Final approved amount

Return your calculation as a valid JSON object with approved_amount and breakdown.
"""
        
        try:
            response = limit_calculator_agent.run(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Parse JSON response
            if '```json' in content:
                json_str = content.split('```json')[1].split('```')[0]
            elif '```' in content:
                json_str = content.split('```')[1].split('```')[0]
            elif '{' in content:
                start = content.find('{')
                end = content.rfind('}') + 1
                json_str = content[start:end]
            else:
                json_str = content
            
            agent_result = json.loads(json_str)
            
            # Use agent's calculation if it differs significantly
            if "approved_amount" in agent_result:
                result["approved_amount"] = agent_result["approved_amount"]
                result["notes"] = agent_result.get("notes", result["notes"])
                result["confidence_score"] = agent_result.get("confidence_score", 0.92)
            
            return result
            
        except Exception as e:
            # Return rule-based result if agent fails
            result["notes"] = result.get("notes", "") + f" (Agent calculation skipped: {str(e)})"
            return result
    
    return result
