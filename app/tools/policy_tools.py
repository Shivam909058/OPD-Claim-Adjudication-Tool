"""
Policy-related tools for checking coverage, limits, and exclusions.
These tools can be used by Agno agents to access policy information.
"""

import json
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from app.config import settings


def load_policy_terms() -> Dict[str, Any]:
    """Load policy terms from JSON file."""
    policy_path = settings.policy_terms_path
    if policy_path.exists():
        with open(policy_path, 'r') as f:
            return json.load(f)
    return {}


# Cache policy terms
_policy_cache: Optional[Dict[str, Any]] = None


def get_policy_terms() -> Dict[str, Any]:
    """
    Get the complete policy terms document.
    
    Returns:
        Dict containing all policy terms, limits, exclusions, and coverage details.
    """
    global _policy_cache
    if _policy_cache is None:
        _policy_cache = load_policy_terms()
    return _policy_cache


def get_coverage_details() -> Dict[str, Any]:
    """Get coverage details from policy."""
    policy = get_policy_terms()
    return policy.get("coverage_details", {})


def get_annual_limit() -> float:
    """Get annual coverage limit."""
    coverage = get_coverage_details()
    return coverage.get("annual_limit", 50000)


def get_per_claim_limit() -> float:
    """Get per-claim limit."""
    coverage = get_coverage_details()
    return coverage.get("per_claim_limit", 5000)


def get_sub_limits(category: str = None) -> Dict[str, Any]:
    """
    Get sub-limits for different categories.
    
    Args:
        category: Optional category to get specific sub-limit for.
                 Options: consultation, diagnostic, pharmacy, dental, vision, alternative_medicine
    
    Returns:
        Dict with sub-limit information for the category or all categories.
    """
    coverage = get_coverage_details()
    
    sub_limits = {
        "consultation": {
            "limit": coverage.get("consultation_fees", {}).get("sub_limit", 2000),
            "copay_percentage": coverage.get("consultation_fees", {}).get("copay_percentage", 10),
            "network_discount": coverage.get("consultation_fees", {}).get("network_discount", 20),
        },
        "diagnostic": {
            "limit": coverage.get("diagnostic_tests", {}).get("sub_limit", 10000),
            "pre_auth_required": coverage.get("diagnostic_tests", {}).get("pre_authorization_required", False),
            "covered_tests": coverage.get("diagnostic_tests", {}).get("covered_tests", []),
        },
        "pharmacy": {
            "limit": coverage.get("pharmacy", {}).get("sub_limit", 15000),
            "generic_mandatory": coverage.get("pharmacy", {}).get("generic_drugs_mandatory", True),
            "branded_copay": coverage.get("pharmacy", {}).get("branded_drugs_copay", 30),
        },
        "dental": {
            "limit": coverage.get("dental", {}).get("sub_limit", 10000),
            "routine_limit": coverage.get("dental", {}).get("routine_checkup_limit", 2000),
            "procedures_covered": coverage.get("dental", {}).get("procedures_covered", []),
            "cosmetic_covered": coverage.get("dental", {}).get("cosmetic_procedures", False),
        },
        "vision": {
            "limit": coverage.get("vision", {}).get("sub_limit", 5000),
            "eye_test": coverage.get("vision", {}).get("eye_test_covered", True),
            "glasses_covered": coverage.get("vision", {}).get("glasses_contact_lenses", True),
            "lasik_covered": coverage.get("vision", {}).get("lasik_surgery", False),
        },
        "alternative_medicine": {
            "limit": coverage.get("alternative_medicine", {}).get("sub_limit", 8000),
            "covered_treatments": coverage.get("alternative_medicine", {}).get("covered_treatments", []),
            "sessions_limit": coverage.get("alternative_medicine", {}).get("therapy_sessions_limit", 20),
        },
    }
    
    if category and category in sub_limits:
        return sub_limits[category]
    return sub_limits


def get_waiting_periods() -> Dict[str, int]:
    """
    Get waiting periods for different conditions.
    
    Returns:
        Dict with condition names and their waiting period in days.
    """
    policy = get_policy_terms()
    waiting = policy.get("waiting_periods", {})
    
    periods = {
        "initial": waiting.get("initial_waiting", 30),
        "pre_existing": waiting.get("pre_existing_diseases", 365),
        "maternity": waiting.get("maternity", 270),
    }
    
    # Add specific ailments
    specific = waiting.get("specific_ailments", {})
    for ailment, days in specific.items():
        periods[ailment.lower()] = days
    
    return periods


def get_exclusions() -> List[str]:
    """
    Get list of excluded treatments/conditions.
    
    Returns:
        List of exclusion strings.
    """
    policy = get_policy_terms()
    return policy.get("exclusions", [])


def check_exclusions(treatment: str, diagnosis: str = None) -> Tuple[bool, str]:
    """
    Check if a treatment or diagnosis is excluded from coverage.
    
    Args:
        treatment: The treatment or procedure name.
        diagnosis: Optional diagnosis to check.
    
    Returns:
        Tuple of (is_excluded: bool, reason: str)
    """
    exclusions = get_exclusions()
    treatment_lower = treatment.lower() if treatment else ""
    diagnosis_lower = diagnosis.lower() if diagnosis else ""
    
    # Check if it's alternative medicine (covered per policy)
    alt_medicine_keywords = ["ayurveda", "ayurvedic", "homeopathy", "unani", "panchakarma", "yoga therapy"]
    if any(kw in treatment_lower or kw in diagnosis_lower for kw in alt_medicine_keywords):
        return False, ""  # Alternative medicine is COVERED
    
    # VITAMINS: Per policy, excluded UNLESS prescribed for deficiency
    # If on prescription (medical document), assume doctor prescribed for medical reason
    # Only flag vitamins if explicitly for supplements/wellness (not treatment)
    if "vitamin" in treatment_lower or "supplement" in treatment_lower:
        # Check if it's for a medical deficiency
        deficiency_keywords = ["deficiency", "anemia", "scurvy", "rickets", "malnutrition"]
        if any(kw in diagnosis_lower for kw in deficiency_keywords):
            return False, ""  # Vitamins for deficiency are covered
        # If prescribed by doctor (in prescription), be lenient - assume medical reason
        # Only exclude vitamins/supplements if diagnosis suggests wellness/prevention
        wellness_keywords = ["wellness", "prevention", "supplement", "general health", "boost"]
        if any(kw in diagnosis_lower for kw in wellness_keywords):
            return True, "Vitamins and supplements (unless prescribed for deficiency)"
        # Default: If on prescription, assume it's for medical treatment
        return False, ""
    
    exclusion_keywords = {
        "cosmetic": ["cosmetic", "whitening", "aesthetic", "beauty", "bleaching"],
        "weight_loss": ["weight loss", "obesity", "bariatric", "diet plan", "slimming"],
        "infertility": ["infertility", "ivf", "fertility"],
        "experimental": ["experimental", "unproven", "clinical trial"],
        "self_inflicted": ["self-inflicted", "self inflicted", "suicide"],
        "adventure_sports": ["adventure sports", "bungee", "skydiving", "paragliding"],
        "alcohol_drugs": ["alcoholism", "drug abuse", "addiction", "substance"],
    }
    
    for exclusion_type, keywords in exclusion_keywords.items():
        for keyword in keywords:
            if keyword in treatment_lower or keyword in diagnosis_lower:
                # Find matching exclusion from policy
                for excl in exclusions:
                    if keyword in excl.lower():
                        return True, excl
                return True, f"{exclusion_type.replace('_', ' ').title()} procedures/treatments"
    
    return False, ""


def check_coverage(category: str, treatment: str = None, diagnosis: str = None) -> Dict[str, Any]:
    """
    Check if a treatment is covered under the policy.
    
    Args:
        category: The claim category (consultation, dental, etc.)
        treatment: Optional specific treatment to check.
        diagnosis: Optional diagnosis to check.
    
    Returns:
        Dict with coverage status and details.
    """
    coverage = get_coverage_details()
    
    # First check exclusions
    if treatment:
        is_excluded, exclusion_reason = check_exclusions(treatment, diagnosis)
        if is_excluded:
            return {
                "is_covered": False,
                "reason": exclusion_reason,
                "category": category,
            }
    
    # Check category coverage
    category_map = {
        "consultation": "consultation_fees",
        "diagnostic": "diagnostic_tests",
        "pharmacy": "pharmacy",
        "dental": "dental",
        "vision": "vision",
        "alternative_medicine": "alternative_medicine",
    }
    
    policy_key = category_map.get(category, category)
    category_coverage = coverage.get(policy_key, {})
    
    if not category_coverage.get("covered", True):
        return {
            "is_covered": False,
            "reason": f"{category} is not covered under this policy",
            "category": category,
        }
    
    # Check specific treatments within category
    if category == "dental" and treatment:
        procedures_covered = category_coverage.get("procedures_covered", [])
        treatment_lower = treatment.lower()
        
        # Check cosmetic
        if any(word in treatment_lower for word in ["whitening", "cosmetic", "aesthetic"]):
            if not category_coverage.get("cosmetic_procedures", False):
                return {
                    "is_covered": False,
                    "reason": "Cosmetic dental procedures are not covered",
                    "category": category,
                }
        
        # Check if procedure is in covered list
        if procedures_covered:
            is_in_list = any(proc.lower() in treatment_lower for proc in procedures_covered)
            if not is_in_list and treatment_lower not in ["consultation", "checkup", "examination"]:
                return {
                    "is_covered": True,  # Default to covered if not explicitly excluded
                    "sub_limit": category_coverage.get("sub_limit", 10000),
                    "category": category,
                    "note": "Procedure may need verification",
                }
    
    # Check alternative medicine treatments
    if category == "alternative_medicine" and treatment:
        covered_treatments = category_coverage.get("covered_treatments", [])
        treatment_lower = treatment.lower()
        
        # Check if it's a covered alternative medicine type
        is_covered_type = any(t.lower() in treatment_lower for t in covered_treatments)
        if not is_covered_type:
            # Check common keywords
            alt_keywords = ["ayurveda", "ayurvedic", "homeopathy", "unani", "panchakarma", "yoga"]
            is_covered_type = any(k in treatment_lower for k in alt_keywords)
        
        if not is_covered_type:
            return {
                "is_covered": False,
                "reason": f"This alternative medicine treatment is not covered. Covered: {', '.join(covered_treatments)}",
                "category": category,
            }
    
    return {
        "is_covered": True,
        "sub_limit": category_coverage.get("sub_limit", get_per_claim_limit()),
        "copay_percentage": category_coverage.get("copay_percentage", 0),
        "category": category,
    }


def is_network_hospital(hospital_name: str) -> bool:
    """
    Check if a hospital is in the network.
    
    Args:
        hospital_name: Name of the hospital to check.
    
    Returns:
        True if hospital is in network, False otherwise.
    """
    if not hospital_name:
        return False
    
    policy = get_policy_terms()
    network_hospitals = policy.get("network_hospitals", [])
    
    hospital_lower = hospital_name.lower()
    for network_hospital in network_hospitals:
        if network_hospital.lower() in hospital_lower or hospital_lower in network_hospital.lower():
            return True
    
    return False


def get_network_hospitals() -> List[str]:
    """Get list of network hospitals."""
    policy = get_policy_terms()
    return policy.get("network_hospitals", [])


def get_claim_requirements() -> Dict[str, Any]:
    """Get claim submission requirements."""
    policy = get_policy_terms()
    return policy.get("claim_requirements", {})


def get_minimum_claim_amount() -> float:
    """Get minimum claim amount."""
    requirements = get_claim_requirements()
    return requirements.get("minimum_claim_amount", 500)


def get_submission_deadline_days() -> int:
    """Get claim submission deadline in days."""
    requirements = get_claim_requirements()
    return requirements.get("submission_timeline_days", 30)


def check_pre_authorization_required(test_name: str, amount: float = 0) -> bool:
    """
    Check if pre-authorization is required for a test.
    
    Args:
        test_name: Name of the diagnostic test.
        amount: Amount of the test (some tests need pre-auth above certain amounts).
    
    Returns:
        True if pre-authorization is required.
    """
    coverage = get_coverage_details()
    diagnostic = coverage.get("diagnostic_tests", {})
    
    # Tests that need pre-auth
    pre_auth_tests = ["mri", "ct scan", "pet scan"]
    test_lower = test_name.lower()
    
    for test in pre_auth_tests:
        if test in test_lower:
            # MRI/CT needs pre-auth for amounts above threshold
            if amount > 10000:
                return True
    
    return False


def calculate_copay(amount: float, category: str, is_network: bool = False) -> Dict[str, float]:
    """
    Calculate co-payment for a claim.
    
    Args:
        amount: Claim amount.
        category: Claim category.
        is_network: Whether it's a network hospital.
    
    Returns:
        Dict with copay amount and network discount.
    """
    sub_limits = get_sub_limits(category)
    copay_percentage = sub_limits.get("copay_percentage", 10)
    network_discount_percentage = sub_limits.get("network_discount", 20) if is_network else 0
    
    copay_amount = amount * (copay_percentage / 100)
    network_discount = amount * (network_discount_percentage / 100)
    
    return {
        "copay_amount": round(copay_amount, 2),
        "copay_percentage": copay_percentage,
        "network_discount": round(network_discount, 2),
        "network_discount_percentage": network_discount_percentage,
        "payable_amount": round(amount - copay_amount - network_discount, 2),
    }
