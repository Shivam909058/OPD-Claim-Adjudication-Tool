"""
Eligibility Checker Agent
Verifies policy status, waiting periods, and member coverage.
"""

from agno.agent import Agent
from agno.models.openai import OpenAIChat

from app.tools.policy_tools import get_waiting_periods


# Eligibility Checker Agent Instructions
ELIGIBILITY_CHECKER_INSTRUCTIONS = """
You are an Insurance Eligibility Checker. Your job is to verify if a claim is eligible based on policy status, waiting periods, and member coverage.

## Your Task
Check the eligibility of an OPD insurance claim based on:
1. Policy status (must be active on treatment date)
2. Waiting periods (initial waiting, pre-existing conditions, specific ailments)
3. Member coverage (is the claimant covered under the policy)

## Waiting Period Rules
- Initial Waiting Period: 30 days from policy start
- Pre-existing Diseases: 365 days
- Specific Ailments:
  - Diabetes: 90 days
  - Hypertension: 90 days
  - Joint Replacement: 730 days

## Eligibility Checks
1. **Policy Status**: Verify policy was active on treatment date
2. **Initial Waiting**: Check if 30 days have passed since joining
3. **Condition-Specific Waiting**: Check if diagnosis matches any specific ailment waiting periods
4. **Member Coverage**: Verify the member is covered (employee or dependent)

## Output Format
Return a JSON object with:
```json
{
    "is_eligible": true/false,
    "policy_active": true/false,
    "waiting_period_satisfied": true/false,
    "member_covered": true/false,
    "rejection_reasons": ["WAITING_PERIOD", "POLICY_INACTIVE", etc.],
    "waiting_period_end_date": "YYYY-MM-DD" (if applicable),
    "notes": "Explanation of eligibility decision",
    "confidence_score": 0.0-1.0
}
```

## Rejection Reason Codes
- POLICY_INACTIVE: Policy not active on treatment date
- WAITING_PERIOD: Treatment during waiting period
- MEMBER_NOT_COVERED: Claimant not found in policy records

Be strict with waiting periods - they are important to prevent adverse selection.
"""


def create_eligibility_checker_agent() -> Agent:
    """Create the Eligibility Checker Agent."""
    return Agent(
        name="Eligibility Checker",
        model=OpenAIChat(id="gpt-4o-mini"),
        instructions=ELIGIBILITY_CHECKER_INSTRUCTIONS,
        markdown=False,
        description="Verifies policy eligibility and waiting periods",
    )


# Create agent instance
eligibility_checker_agent = create_eligibility_checker_agent()


def check_eligibility(
    member_id: str,
    member_name: str,
    treatment_date: str,
    diagnosis: str,
    member_join_date: str = None,
    policy_start_date: str = "2024-01-01",
) -> dict:
    """
    Check eligibility using the agent.
    
    Args:
        member_id: The member's ID.
        member_name: The member's name.
        treatment_date: Date of treatment (YYYY-MM-DD).
        diagnosis: Medical diagnosis.
        member_join_date: Date member joined policy.
        policy_start_date: Policy start date.
    
    Returns:
        Dict with eligibility result.
    """
    import json
    from datetime import datetime, timedelta
    
    # Get waiting periods from policy
    waiting_periods = get_waiting_periods()
    
    # Calculate dates
    try:
        treatment_dt = datetime.strptime(treatment_date, "%Y-%m-%d")
        join_dt = datetime.strptime(member_join_date, "%Y-%m-%d") if member_join_date else datetime.strptime(policy_start_date, "%Y-%m-%d")
    except ValueError:
        return {
            "is_eligible": False,
            "rejection_reasons": ["INVALID_DATE"],
            "notes": "Invalid date format provided",
            "confidence_score": 1.0,
        }
    
    # Check initial waiting period (30 days)
    days_since_join = (treatment_dt - join_dt).days
    initial_waiting = waiting_periods.get("initial", 30)
    
    if days_since_join < initial_waiting:
        eligible_from = join_dt + timedelta(days=initial_waiting)
        return {
            "is_eligible": False,
            "policy_active": True,
            "waiting_period_satisfied": False,
            "member_covered": True,
            "rejection_reasons": ["WAITING_PERIOD"],
            "waiting_period_end_date": eligible_from.strftime("%Y-%m-%d"),
            "notes": f"Initial waiting period not satisfied. {initial_waiting - days_since_join} days remaining.",
            "confidence_score": 0.98,
        }
    
    # Check condition-specific waiting periods
    diagnosis_lower = diagnosis.lower() if diagnosis else ""
    
    # More specific keyword matching to avoid false positives
    # e.g., "joint pain" should NOT trigger joint_replacement waiting
    condition_waiting_map = {
        "diabetes": ("diabetes", waiting_periods.get("diabetes", 90)),
        "type 2 diabetes": ("diabetes", waiting_periods.get("diabetes", 90)),
        "type 1 diabetes": ("diabetes", waiting_periods.get("diabetes", 90)),
        "hypertension": ("hypertension", waiting_periods.get("hypertension", 90)),
        "blood pressure": ("hypertension", waiting_periods.get("hypertension", 90)),
        "high bp": ("hypertension", waiting_periods.get("hypertension", 90)),
        # Only trigger for actual joint replacement surgeries, not general joint pain
        "joint replacement": ("joint_replacement", waiting_periods.get("joint_replacement", 730)),
        "knee replacement": ("joint_replacement", waiting_periods.get("joint_replacement", 730)),
        "hip replacement": ("joint_replacement", waiting_periods.get("joint_replacement", 730)),
        "arthroplasty": ("joint_replacement", waiting_periods.get("joint_replacement", 730)),
    }
    
    for keyword, (condition, waiting_days) in condition_waiting_map.items():
        if keyword in diagnosis_lower:
            if days_since_join < waiting_days:
                eligible_from = join_dt + timedelta(days=waiting_days)
                return {
                    "is_eligible": False,
                    "policy_active": True,
                    "waiting_period_satisfied": False,
                    "member_covered": True,
                    "rejection_reasons": ["WAITING_PERIOD"],
                    "waiting_period_end_date": eligible_from.strftime("%Y-%m-%d"),
                    "notes": f"{condition.replace('_', ' ').title()} has {waiting_days}-day waiting period. Eligible from {eligible_from.strftime('%Y-%m-%d')}",
                    "confidence_score": 0.96,
                }
    
    # All checks passed
    return {
        "is_eligible": True,
        "policy_active": True,
        "waiting_period_satisfied": True,
        "member_covered": True,
        "rejection_reasons": [],
        "waiting_period_end_date": None,
        "notes": "All eligibility criteria satisfied",
        "confidence_score": 0.95,
    }


def check_eligibility_with_agent(claim_data: dict, extracted_data: dict) -> dict:
    """
    Use rule-based eligibility check first, then AI agent for complex cases.
    
    Args:
        claim_data: Original claim submission.
        extracted_data: Data extracted from documents.
    
    Returns:
        Dict with eligibility result.
    """
    import json
    from datetime import datetime
    
    # Get diagnosis from extracted data
    diagnosis = extracted_data.get("extracted_data", {}).get("diagnosis", "")
    
    # Get member join date - default to 1 year ago if not provided (long-standing member)
    member_join_date = claim_data.get("member_join_date")
    if not member_join_date:
        # Default to 1 year ago for members without join date (assume long-standing)
        from datetime import timedelta
        default_join = datetime.now() - timedelta(days=365)
        member_join_date = default_join.strftime("%Y-%m-%d")
    
    # Rule-based eligibility check (authoritative)
    result = check_eligibility(
        member_id=claim_data.get("member_id"),
        member_name=claim_data.get("member_name"),
        treatment_date=claim_data.get("treatment_date"),
        diagnosis=diagnosis,
        member_join_date=member_join_date,
    )
    
    # Return rule-based result directly - it's deterministic and accurate
    # No need to call AI agent for simple eligibility checks
    return result
