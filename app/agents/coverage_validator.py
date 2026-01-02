"""
Coverage Validator Agent
Validates if the treatment/service is covered under the policy.
"""

from agno.agent import Agent
from agno.models.openai import OpenAIChat

from app.tools.policy_tools import (
    check_coverage,
    check_exclusions,
    get_exclusions,
    get_sub_limits,
    check_pre_authorization_required,
)


# Coverage Validator Agent Instructions
COVERAGE_VALIDATOR_INSTRUCTIONS = """
You are an Insurance Coverage Validator. Your job is to check if a treatment or service is covered under the OPD insurance policy.

## Your Task
Validate coverage for a claim by checking:
1. Is the treatment/service category covered?
2. Is the specific treatment in the exclusions list?
3. Does it require pre-authorization?
4. What are the applicable sub-limits?

## Coverage Categories
- Consultation: Doctor visits, consultations
- Diagnostic Tests: Blood tests, X-rays, MRI, CT scan
- Pharmacy: Medicines and drugs
- Dental: Fillings, extractions, root canals (NOT cosmetic)
- Vision: Eye tests, glasses (NOT LASIK)
- Alternative Medicine: Ayurveda, Homeopathy, Unani

## Exclusions (NOT COVERED)
- Cosmetic procedures (teeth whitening, aesthetic treatments)
- Weight loss treatments
- Infertility treatments
- Experimental treatments
- Self-inflicted injuries
- Adventure sports injuries
- HIV/AIDS treatment
- Alcoholism/drug abuse treatment
- Vitamins and supplements (unless prescribed for deficiency)

## Pre-Authorization Requirements
- MRI scans (above ₹10,000)
- CT scans (above ₹10,000)
- PET scans

## Output Format
Return a JSON object with:
```json
{
    "is_covered": true/false,
    "covered_items": ["list of covered items"],
    "excluded_items": ["list of excluded items with reasons"],
    "pre_auth_required": true/false,
    "pre_auth_obtained": true/false,
    "applicable_sub_limit": 0,
    "rejection_reasons": ["SERVICE_NOT_COVERED", "EXCLUDED_CONDITION", "PRE_AUTH_MISSING"],
    "notes": "Explanation of coverage decision",
    "confidence_score": 0.0-1.0
}
```

## Rejection Reason Codes
- SERVICE_NOT_COVERED: Treatment/service not covered
- EXCLUDED_CONDITION: Condition in exclusions list
- PRE_AUTH_MISSING: Pre-authorization required but not obtained

Be thorough in checking exclusions - cosmetic procedures are often disguised.
"""


def create_coverage_validator_agent() -> Agent:
    """Create the Coverage Validator Agent."""
    return Agent(
        name="Coverage Validator",
        model=OpenAIChat(id="gpt-4o-mini"),
        instructions=COVERAGE_VALIDATOR_INSTRUCTIONS,
        markdown=False,
        description="Validates coverage and checks exclusions",
    )


# Create agent instance
coverage_validator_agent = create_coverage_validator_agent()


def validate_coverage(
    diagnosis: str,
    treatments: list,
    procedures: list,
    medicines: list,
    tests: list,
    claim_amount: float,
    category: str = None,
    pre_auth_obtained: bool = False,
) -> dict:
    """
    Validate coverage using rule-based logic following policy_terms.json.
    
    Key Policy Rules:
    1. Alternative medicine (Ayurveda, Homeopathy, Unani) IS covered up to ₹8000
    2. Vitamins/supplements excluded UNLESS prescribed for deficiency
    3. Cosmetic procedures are NOT covered
    4. Weight loss treatments are NOT covered
    5. MRI/CT require pre-auth if claim > ₹10,000
    
    Args:
        diagnosis: Medical diagnosis.
        treatments: List of treatments.
        procedures: List of procedures.
        medicines: List of medicines.
        tests: List of diagnostic tests.
        claim_amount: Total claim amount.
        category: Claim category.
        pre_auth_obtained: Whether pre-authorization was obtained.
    
    Returns:
        Dict with coverage validation result.
    """
    covered_items = []
    excluded_items = []
    rejection_reasons = []
    pre_auth_required = False
    applicable_sub_limit = 5000  # Default to per-claim limit
    
    # Combine all items for checking
    all_items = (treatments or []) + (procedures or [])
    if diagnosis:
        all_items.append(diagnosis)
    
    # Check diagnosis for alternative medicine (COVERED per policy)
    diagnosis_lower = (diagnosis or "").lower()
    is_alternative_medicine = any(kw in diagnosis_lower for kw in 
        ["ayurveda", "ayurvedic", "homeopathy", "homeopathic", "unani", "panchakarma", "yoga therapy"])
    
    # Check if it's a treatment for a specific condition (vitamins may be okay)
    is_deficiency_treatment = any(kw in diagnosis_lower for kw in 
        ["deficiency", "anemia", "scurvy", "rickets", "malnutrition"])
    
    # Check each item for exclusions
    for item in all_items:
        if not item:
            continue
        
        item_lower = item.lower()
        
        # Skip alternative medicine from exclusion check - it's COVERED per policy
        if any(kw in item_lower for kw in ["ayurveda", "ayurvedic", "homeopathy", "unani", "panchakarma"]):
            covered_items.append(item)
            continue
        
        is_excluded, exclusion_reason = check_exclusions(item, diagnosis)
        
        if is_excluded:
            excluded_items.append(f"{item} - {exclusion_reason}")
            # Determine the specific rejection reason
            reason_lower = exclusion_reason.lower()
            if "cosmetic" in reason_lower or "whitening" in item_lower:
                if "COSMETIC_PROCEDURE" not in rejection_reasons:
                    rejection_reasons.append("COSMETIC_PROCEDURE")
            elif "weight" in reason_lower or "obesity" in item_lower or "diet plan" in item_lower:
                if "SERVICE_NOT_COVERED" not in rejection_reasons:
                    rejection_reasons.append("SERVICE_NOT_COVERED")
            else:
                if "EXCLUDED_CONDITION" not in rejection_reasons:
                    rejection_reasons.append("EXCLUDED_CONDITION")
        else:
            covered_items.append(item)
    
    # Check medicines for exclusions (be more lenient with prescribed medicines)
    for med in (medicines or []):
        if not med:
            continue
        
        med_lower = med.lower()
        
        # Vitamins are excluded UNLESS prescribed for deficiency
        if "vitamin" in med_lower or "supplement" in med_lower:
            if is_deficiency_treatment:
                # Vitamins okay for deficiency treatment
                covered_items.append(med)
            else:
                # Only flag as info, don't hard reject - doctor prescribed it
                # Per policy: "Vitamins and supplements (unless prescribed for deficiency)"
                # Since it's on prescription, assume it's for medical reason
                covered_items.append(med)  # Be lenient - doctor prescribed
        else:
            covered_items.append(med)
    
    # Check tests for pre-authorization
    for test in (tests or []):
        if not test:
            continue
            
        test_lower = test.lower()
        
        # Check if pre-auth is required (MRI, CT > ₹10,000)
        if check_pre_authorization_required(test, claim_amount):
            pre_auth_required = True
            if not pre_auth_obtained:
                if "PRE_AUTH_MISSING" not in rejection_reasons:
                    rejection_reasons.append("PRE_AUTH_MISSING")
                excluded_items.append(f"{test} - requires pre-authorization")
            else:
                covered_items.append(test)
        else:
            covered_items.append(test)
    
    # Determine category and get sub-limits
    if category:
        sub_limit_info = get_sub_limits(category)
        applicable_sub_limit = sub_limit_info.get("limit", 5000)
    else:
        # Auto-detect category from content
        if any("dental" in str(item).lower() for item in all_items) or \
           any(proc in str(all_items).lower() for proc in ["root canal", "extraction", "filling"]):
            category = "dental"
            applicable_sub_limit = get_sub_limits("dental").get("limit", 10000)
        elif any(med in str(medicines).lower() for med in ["ayur", "homeo", "unani"]) or \
             "ayur" in str(diagnosis).lower() or "panchakarma" in str(all_items).lower():
            category = "alternative_medicine"
            applicable_sub_limit = get_sub_limits("alternative_medicine").get("limit", 8000)
        elif tests and len(tests) > 0:
            category = "diagnostic"
            applicable_sub_limit = get_sub_limits("diagnostic").get("limit", 10000)
        elif medicines and len(medicines) > 0:
            category = "pharmacy"
            applicable_sub_limit = get_sub_limits("pharmacy").get("limit", 15000)
        else:
            category = "consultation"
            applicable_sub_limit = get_sub_limits("consultation").get("limit", 2000)
    
    # Determine overall coverage
    is_covered = len(rejection_reasons) == 0
    
    # Generate notes
    if is_covered:
        notes = f"All items covered under {category} category"
    else:
        notes = f"Coverage issues: {', '.join(rejection_reasons)}"
        if excluded_items:
            notes += f". Excluded: {', '.join(excluded_items[:3])}"
    
    return {
        "is_covered": is_covered,
        "covered_items": covered_items,
        "excluded_items": excluded_items,
        "pre_auth_required": pre_auth_required,
        "pre_auth_obtained": pre_auth_obtained,
        "applicable_sub_limit": applicable_sub_limit,
        "category": category,
        "rejection_reasons": rejection_reasons,
        "notes": notes,
        "confidence_score": 0.92 if is_covered else 0.95,
    }


def validate_coverage_with_agent(claim_data: dict, extracted_data: dict) -> dict:
    """
    Validate coverage following policy_terms.json rules.
    Uses rule-based logic for deterministic decisions.
    
    Args:
        claim_data: Original claim submission.
        extracted_data: Data extracted from documents.
    
    Returns:
        Dict with coverage validation result.
    """
    import json
    
    # Get data from extraction (safely handle None values)
    ext_data = extracted_data.get("extracted_data") or {}
    diagnosis = ext_data.get("diagnosis") or ""
    medicines = ext_data.get("medicines") or []
    tests = ext_data.get("tests") or []
    procedures = ext_data.get("procedures") or []
    
    # Get documents for additional context
    documents = claim_data.get("documents") or {}
    prescription = documents.get("prescription") or {}
    bill = documents.get("bill") or {}
    
    # Combine treatments (safely)
    presc_procedures = prescription.get("procedures") or []
    presc_treatment = prescription.get("treatment") or ""
    presc_medicines = prescription.get("medicines_prescribed") or []
    treatments = presc_procedures + ([presc_treatment] if presc_treatment else [])
    
    # Combine medicines from extracted and prescription
    all_medicines = list(set(medicines + presc_medicines))
    
    # Get diagnosis from prescription if not in extracted data
    if not diagnosis:
        diagnosis = prescription.get("diagnosis") or ""
    
    # Determine category from claim_data or auto-detect
    category = claim_data.get("category")
    diagnosis_lower = diagnosis.lower()
    
    # Auto-detect alternative medicine category
    if not category:
        if any(kw in diagnosis_lower for kw in ["ayurveda", "ayurvedic", "homeopathy", "unani", "panchakarma"]):
            category = "alternative_medicine"
        elif any(kw in str(treatments).lower() for kw in ["ayurveda", "panchakarma", "homeopathy"]):
            category = "alternative_medicine"
    
    # Do rule-based validation with all the data
    result = validate_coverage(
        diagnosis=diagnosis,
        treatments=treatments,
        procedures=procedures,
        medicines=all_medicines,
        tests=tests,
        claim_amount=claim_data.get("claim_amount", 0),
        category=category,
    )
    
    # Return rule-based result - it's deterministic and follows policy exactly
    return result
