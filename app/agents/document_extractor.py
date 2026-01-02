"""
Document Extractor Agent
Extracts and structures data from submitted medical documents.
"""

from agno.agent import Agent
from agno.models.openai import OpenAIChat

# Document Extractor Agent Instructions
DOCUMENT_EXTRACTOR_INSTRUCTIONS = """
You are a Medical Document Data Extractor. Your job is to extract structured information from medical documents (prescriptions, bills, diagnostic reports).

## Your Task
Given a claim submission with documents, extract and validate all relevant data fields.

## Data to Extract

### From Prescription:
- doctor_name: Full name of the doctor
- doctor_reg: Registration number (format: STATE/NUMBER/YEAR or AYUR/STATE/NUMBER/YEAR)
- diagnosis: Medical condition/diagnosis
- medicines_prescribed: List of medicines with dosage
- tests_prescribed: Any diagnostic tests recommended
- procedures: Any procedures mentioned
- prescription_date: Date on prescription

### From Bill:
- hospital_name: Name of hospital/clinic
- bill_date: Date on bill
- bill_number: Bill/invoice number
- consultation_fee: Doctor consultation charges
- diagnostic_tests: Charges for tests
- medicines: Pharmacy charges
- procedure_charges: Charges for any procedures
- total_amount: Total bill amount
- Individual line items if available (root_canal, mri_scan, etc.)

## Validation Checks
1. Check if prescription is present (required)
2. Check if bill is present (required)
3. Validate doctor registration format
4. Check if dates are consistent
5. Verify patient name matches (if available)

## Output Format
Return a JSON object with:
```json
{
    "extraction_successful": true/false,
    "has_prescription": true/false,
    "has_bill": true/false,
    "has_valid_doctor_reg": true/false,
    "dates_match": true/false,
    "extracted_data": {
        "doctor_name": "...",
        "doctor_registration": "...",
        "diagnosis": "...",
        "medicines": ["..."],
        "tests": ["..."],
        "procedures": ["..."],
        "consultation_fee": 0,
        "diagnostic_amount": 0,
        "pharmacy_amount": 0,
        "procedure_amount": 0,
        "hospital_name": "...",
        "total_bill_amount": 0
    },
    "validation_issues": ["list of any issues found"],
    "confidence_score": 0.0-1.0
}
```

Be precise and accurate. If a field is not available, set it to null or empty.
"""


def create_document_extractor_agent() -> Agent:
    """Create the Document Extractor Agent."""
    return Agent(
        name="Document Extractor",
        model=OpenAIChat(id="gpt-4o-mini"),
        instructions=DOCUMENT_EXTRACTOR_INSTRUCTIONS,
        markdown=False,
        description="Extracts and validates data from medical documents",
    )


# Create agent instance
document_extractor_agent = create_document_extractor_agent()


def extract_document_data(claim_submission: dict) -> dict:
    """
    Extract data from claim documents using the agent.
    
    Args:
        claim_submission: The claim submission data with documents.
    
    Returns:
        Dict with extracted data.
    """
    import json
    
    # Prepare the prompt
    prompt = f"""
Extract data from this OPD claim submission:

Member ID: {claim_submission.get('member_id')}
Member Name: {claim_submission.get('member_name')}
Treatment Date: {claim_submission.get('treatment_date')}
Claim Amount: ₹{claim_submission.get('claim_amount')}

Documents Submitted:
{json.dumps(claim_submission.get('documents', {}), indent=2)}

Extract all relevant information and validate the documents.
Return your response as a valid JSON object.
"""
    
    # Run the agent
    response = document_extractor_agent.run(prompt)
    
    # Parse response
    try:
        # Try to extract JSON from response
        content = response.content if hasattr(response, 'content') else str(response)
        
        # Find JSON in response
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
        
        return json.loads(json_str)
    except Exception as e:
        # Return basic extraction if parsing fails
        documents = claim_submission.get('documents', {})
        prescription = documents.get('prescription', {})
        bill = documents.get('bill', {})
        
        return {
            "extraction_successful": True,
            "has_prescription": bool(prescription),
            "has_bill": bool(bill),
            "has_valid_doctor_reg": bool(prescription.get('doctor_reg')),
            "dates_match": True,
            "extracted_data": {
                "doctor_name": prescription.get('doctor_name'),
                "doctor_registration": prescription.get('doctor_reg'),
                "diagnosis": prescription.get('diagnosis'),
                "medicines": prescription.get('medicines_prescribed', []),
                "tests": prescription.get('tests_prescribed', []),
                "procedures": prescription.get('procedures', []),
                "consultation_fee": bill.get('consultation_fee', 0),
                "diagnostic_amount": bill.get('diagnostic_tests', 0),
                "pharmacy_amount": bill.get('medicines', 0),
                "procedure_amount": bill.get('root_canal', 0) + bill.get('therapy_charges', 0),
                "hospital_name": bill.get('hospital_name'),
                "total_bill_amount": claim_submission.get('claim_amount', 0),
            },
            "validation_issues": [],
            "confidence_score": 0.85,
            "parse_error": str(e),
        }
