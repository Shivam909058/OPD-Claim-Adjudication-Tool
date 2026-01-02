"""
Fraud detection tools for identifying suspicious claims.
"""

import re
from typing import Dict, Any, List, Tuple
from datetime import datetime, timedelta


def validate_doctor_registration(reg_number: str) -> Tuple[bool, str]:
    """
    Validate doctor registration number format.
    
    Expected formats:
    - Allopathic: [STATE_CODE]/[NUMBER]/[YEAR] e.g., KA/45678/2015
    - Ayurvedic: AYUR/[STATE]/[NUMBER]/[YEAR] e.g., AYUR/KL/2345/2019
    - Homeopathic: HOM/[STATE]/[NUMBER]/[YEAR]
    - Dental: [STATE]/D/[NUMBER]/[YEAR]
    
    Args:
        reg_number: Doctor's registration number to validate.
    
    Returns:
        Tuple of (is_valid: bool, message: str)
    """
    if not reg_number:
        return False, "Doctor registration number is missing"
    
    reg_number = reg_number.strip().upper()
    
    # Valid state codes
    state_codes = [
        "AP", "AR", "AS", "BR", "CG", "GA", "GJ", "HR", "HP", "JH", "JK",
        "KA", "KL", "MP", "MH", "MN", "ML", "MZ", "NL", "OD", "PB", "RJ",
        "SK", "TN", "TS", "TR", "UP", "UK", "WB", "AN", "CH", "DN", "DD",
        "DL", "LD", "PY"
    ]
    
    # Pattern for standard medical registration: STATE/NUMBER/YEAR
    standard_pattern = r'^([A-Z]{2})/(\d{4,6})/(\d{4})$'
    
    # Pattern for Ayurvedic: AYUR/STATE/NUMBER/YEAR
    ayur_pattern = r'^AYUR/([A-Z]{2})/(\d{3,5})/(\d{4})$'
    
    # Pattern for Homeopathic: HOM/STATE/NUMBER/YEAR
    hom_pattern = r'^HOM/([A-Z]{2})/(\d{3,5})/(\d{4})$'
    
    # Pattern for Dental: STATE/D/NUMBER/YEAR
    dental_pattern = r'^([A-Z]{2})/D/(\d{3,5})/(\d{4})$'
    
    patterns = [
        (standard_pattern, "Allopathic"),
        (ayur_pattern, "Ayurvedic"),
        (hom_pattern, "Homeopathic"),
        (dental_pattern, "Dental"),
    ]
    
    for pattern, med_type in patterns:
        match = re.match(pattern, reg_number)
        if match:
            groups = match.groups()
            state = groups[0]
            year = int(groups[-1])
            
            # Validate state code
            if state not in state_codes and med_type == "Allopathic":
                return False, f"Invalid state code: {state}"
            
            # Validate year (should be between 1950 and current year)
            current_year = datetime.now().year
            if year < 1950 or year > current_year:
                return False, f"Invalid registration year: {year}"
            
            return True, f"Valid {med_type} registration"
    
    return False, "Registration number format not recognized"


def check_fraud_indicators(
    claim_data: Dict[str, Any],
    previous_claims_same_day: int = 0,
    previous_claims_ytd: float = 0,
    annual_limit: float = 50000,
) -> Dict[str, Any]:
    """
    Check for fraud indicators in a claim.
    
    Args:
        claim_data: The claim submission data.
        previous_claims_same_day: Number of other claims on the same day.
        previous_claims_ytd: Total claims amount year-to-date.
        annual_limit: Annual coverage limit.
    
    Returns:
        Dict with fraud analysis results.
    """
    flags: List[str] = []
    risk_score: float = 0.0
    
    claim_amount = claim_data.get("claim_amount", 0)
    member_id = claim_data.get("member_id", "")
    treatment_date = claim_data.get("treatment_date", "")
    documents = claim_data.get("documents", {})
    
    # Check 1: Multiple claims on same day
    if previous_claims_same_day >= 3:
        flags.append("Multiple claims on same day (3+)")
        risk_score += 0.3
    elif previous_claims_same_day >= 2:
        flags.append("Multiple claims on same day")
        risk_score += 0.15
    
    # Check 2: High utilization rate
    utilization_rate = (previous_claims_ytd + claim_amount) / annual_limit if annual_limit > 0 else 0
    if utilization_rate > 0.9:
        flags.append("Near annual limit exhaustion")
        risk_score += 0.1
    
    # Check 3: High single claim amount (close to per-claim limit)
    per_claim_limit = 5000
    if claim_amount > per_claim_limit * 0.95:
        flags.append("Claim amount very close to per-claim limit")
        risk_score += 0.1
    
    # Check 4: Check prescription data
    prescription = documents.get("prescription", {})
    if prescription:
        doctor_reg = prescription.get("doctor_reg", "")
        is_valid, _ = validate_doctor_registration(doctor_reg)
        if not is_valid:
            flags.append("Invalid or suspicious doctor registration")
            risk_score += 0.25
        
        # Check for unusually many medicines
        medicines = prescription.get("medicines_prescribed", [])
        if len(medicines) > 10:
            flags.append("Unusually high number of medicines prescribed")
            risk_score += 0.1
    
    # Check 5: Bill anomalies
    bill = documents.get("bill", {})
    if bill:
        # Check for round numbers (potential fabrication)
        amounts = [
            bill.get("consultation_fee", 0),
            bill.get("medicines", 0),
            bill.get("diagnostic_tests", 0),
        ]
        round_amounts = sum(1 for a in amounts if a > 0 and a % 500 == 0)
        if round_amounts >= 2:
            flags.append("Multiple round number amounts in bill")
            risk_score += 0.05
    
    # Check 6: Weekend/Holiday treatment for non-emergency
    try:
        treatment_dt = datetime.strptime(treatment_date, "%Y-%m-%d")
        if treatment_dt.weekday() >= 5:  # Saturday or Sunday
            diagnosis = prescription.get("diagnosis", "").lower() if prescription else ""
            emergency_keywords = ["emergency", "accident", "acute", "severe", "critical"]
            if not any(kw in diagnosis for kw in emergency_keywords):
                flags.append("Non-emergency treatment on weekend")
                risk_score += 0.05
    except (ValueError, TypeError):
        pass
    
    # Determine if manual review is needed
    recommend_manual_review = risk_score >= 0.35 or len(flags) >= 3
    
    # Cap risk score at 1.0
    risk_score = min(risk_score, 1.0)
    
    return {
        "is_suspicious": risk_score >= 0.35,
        "fraud_flags": flags,
        "risk_score": round(risk_score, 2),
        "recommend_manual_review": recommend_manual_review,
        "notes": f"Risk score: {risk_score:.2f}. {len(flags)} fraud indicator(s) detected." if flags else "No fraud indicators detected.",
    }


def check_document_consistency(
    prescription_date: str,
    bill_date: str,
    treatment_date: str,
) -> Tuple[bool, str]:
    """
    Check if document dates are consistent.
    
    Args:
        prescription_date: Date on prescription.
        bill_date: Date on bill.
        treatment_date: Claimed treatment date.
    
    Returns:
        Tuple of (is_consistent: bool, message: str)
    """
    try:
        dates = []
        date_names = []
        
        if prescription_date:
            dates.append(datetime.strptime(prescription_date, "%Y-%m-%d"))
            date_names.append("prescription")
        
        if bill_date:
            dates.append(datetime.strptime(bill_date, "%Y-%m-%d"))
            date_names.append("bill")
        
        if treatment_date:
            dates.append(datetime.strptime(treatment_date, "%Y-%m-%d"))
            date_names.append("treatment")
        
        if len(dates) < 2:
            return True, "Insufficient dates for comparison"
        
        # Check if all dates are within 7 days of each other
        min_date = min(dates)
        max_date = max(dates)
        
        if (max_date - min_date).days > 7:
            return False, f"Date mismatch: {(max_date - min_date).days} days between documents"
        
        return True, "Document dates are consistent"
        
    except (ValueError, TypeError) as e:
        return False, f"Error parsing dates: {str(e)}"


def check_diagnosis_treatment_match(
    diagnosis: str,
    treatments: List[str],
    medicines: List[str],
) -> Tuple[bool, str]:
    """
    Basic check if treatment/medicines align with diagnosis.
    
    Args:
        diagnosis: The medical diagnosis.
        treatments: List of treatments/procedures.
        medicines: List of prescribed medicines.
    
    Returns:
        Tuple of (is_matched: bool, message: str)
    """
    if not diagnosis:
        return False, "No diagnosis provided"
    
    diagnosis_lower = diagnosis.lower()
    
    # Define expected treatments/medicines for common conditions
    condition_map = {
        "fever": {
            "medicines": ["paracetamol", "crocin", "dolo", "acetaminophen"],
            "treatments": ["consultation", "blood test", "cbc"],
        },
        "diabetes": {
            "medicines": ["metformin", "glimepiride", "insulin", "glipizide"],
            "treatments": ["blood sugar", "hba1c", "consultation"],
        },
        "hypertension": {
            "medicines": ["amlodipine", "losartan", "metoprolol", "atenolol"],
            "treatments": ["bp check", "ecg", "consultation"],
        },
        "infection": {
            "medicines": ["antibiotic", "amoxicillin", "azithromycin", "ciprofloxacin"],
            "treatments": ["culture", "sensitivity", "consultation"],
        },
        "dental": {
            "medicines": ["analgesic", "antibiotic", "painkiller"],
            "treatments": ["root canal", "extraction", "filling", "cleaning"],
        },
    }
    
    # Find matching condition
    matched_condition = None
    for condition in condition_map:
        if condition in diagnosis_lower:
            matched_condition = condition
            break
    
    if not matched_condition:
        # Can't verify - allow it through
        return True, "Diagnosis-treatment match could not be verified (allow through)"
    
    expected = condition_map[matched_condition]
    
    # Check if at least one expected medicine/treatment is present
    all_items = [m.lower() for m in medicines] + [t.lower() for t in treatments]
    all_expected = expected["medicines"] + expected["treatments"]
    
    has_match = any(
        any(exp in item for item in all_items)
        for exp in all_expected
    )
    
    if has_match:
        return True, f"Treatment/medicines align with {matched_condition} diagnosis"
    else:
        return False, f"Treatment/medicines may not align with {matched_condition} diagnosis"
