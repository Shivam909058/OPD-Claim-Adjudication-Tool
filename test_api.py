"""
API Test Script for OPD Claim Adjudication System
Run this to test the backend API endpoints directly via HTTP.

Usage:
    python test_api.py              # Run all tests
    python test_api.py TC001        # Run specific test case
    python test_api.py --list       # List all test cases

Make sure the backend is running on http://localhost:7777
"""

import requests  
import json
import sys
from pathlib import Path

BASE_URL = "http://localhost:7777"
TEST_CASES_FILE = Path(__file__).parent / "docs" / "test_cases.json"


def load_test_cases():
    """Load test cases from JSON file"""
    try:
        with open(TEST_CASES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data["test_cases"]
    except FileNotFoundError:
        print(f"❌ Test cases file not found: {TEST_CASES_FILE}")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in test cases file: {e}")
        return []


def convert_test_case_to_api_format(test_case):
    """Convert test_cases.json format to API request format"""
    input_data = test_case["input_data"]
    
    # Build API request payload
    api_payload = {
        "member_id": input_data.get("member_id"),
        "member_name": input_data.get("member_name"),
        "treatment_date": input_data.get("treatment_date"),
        "claim_amount": input_data.get("claim_amount"),
        "hospital": input_data.get("hospital", "General Hospital"),
        "cashless_request": input_data.get("cashless_request", False),
        "documents": input_data.get("documents", {})
    }
    
    # Add optional fields if present
    if "member_join_date" in input_data:
        api_payload["member_join_date"] = input_data["member_join_date"]
    
    if "previous_claims_same_day" in input_data:
        api_payload["previous_claims_same_day"] = input_data["previous_claims_same_day"]
    
    # Determine category from documents
    docs = input_data.get("documents", {})
    prescription = docs.get("prescription", {})
    bill = docs.get("bill", {})
    
    if "root_canal" in bill or "dental" in prescription.get("diagnosis", "").lower():
        api_payload["category"] = "dental"
    elif "mri_scan" in bill or "therapy_charges" in bill:
        api_payload["category"] = "diagnostic"
    elif bill.get("medicines", 0) > bill.get("consultation_fee", 0):
        api_payload["category"] = "pharmacy"
    else:
        api_payload["category"] = "consultation"
    
    return api_payload


def test_health():
    """Test health endpoint"""
    print("\n" + "="*60)
    print("🏥 Testing Health Endpoint")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend. Is it running on port 7777?")
        return False


def test_submit_claim(claim_data, test_case):
    """Submit a claim and compare with expected output"""
    case_id = test_case["case_id"]
    case_name = test_case["case_name"]
    expected = test_case["expected_output"]
    
    print("\n" + "="*60)
    print(f"📋 {case_id}: {case_name}")
    print(f"📝 {test_case['description']}")
    print("="*60)
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/claims/submit",
            json=claim_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # Display results
            print(f"\n📊 RESULT:")
            print(f"   Claim ID: {result['claim_id']}")
            print(f"   Decision: {result['decision']}")
            print(f"   Approved Amount: ₹{result['approved_amount']:,.2f}")
            print(f"   Confidence Score: {result['confidence_score']}%")
            
            if result.get('rejection_reasons'):
                print(f"   Rejection Reasons: {result['rejection_reasons']}")
            if result.get('rejected_items'):
                print(f"   Rejected Items: {result['rejected_items']}")
            if result.get('fraud_flags'):
                print(f"   Fraud Flags: {result['fraud_flags']}")
            if result.get('deductions'):
                print(f"   Deductions: {result['deductions']}")
            
            # Compare with expected
            print(f"\n🎯 EXPECTED vs ACTUAL:")
            expected_decision = expected["decision"]
            actual_decision = result["decision"]
            
            decision_match = actual_decision == expected_decision
            print(f"   Decision: {expected_decision} → {actual_decision} {'✅' if decision_match else '❌'}")
            
            if "approved_amount" in expected:
                expected_amount = expected["approved_amount"]
                actual_amount = result["approved_amount"]
                amount_match = abs(actual_amount - expected_amount) < 100  # Allow small variance
                print(f"   Amount: ₹{expected_amount} → ₹{actual_amount} {'✅' if amount_match else '⚠️'}")
            
            return {
                "case_id": case_id,
                "case_name": case_name,
                "expected_decision": expected_decision,
                "actual_decision": actual_decision,
                "passed": decision_match,
                "result": result
            }
        else:
            print(f"❌ Error: {response.json()}")
            return {
                "case_id": case_id,
                "case_name": case_name,
                "expected_decision": expected["decision"],
                "actual_decision": "ERROR",
                "passed": False,
                "error": response.json()
            }
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend. Is it running on port 7777?")
        return None


def test_get_claims():
    """Get list of all claims"""
    print("\n" + "="*60)
    print("📋 All Claims in Database")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/api/claims")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Total Claims: {result['total_claims']}")
            
            for claim in result['claims'][:10]:  # Show first 10
                emoji = "✅" if claim.get('decision') == "APPROVED" else "⚠️" if claim.get('decision') == "PARTIAL" else "❌"
                print(f"\n  {emoji} {claim['claim_id']}: {claim['member_name']}")
                print(f"     Amount: ₹{claim['claim_amount']:,.2f} | Decision: {claim.get('decision', claim['status'])}")
            
            return result
        else:
            print(f"❌ Error: {response.json()}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend")
        return None


def list_test_cases():
    """List all available test cases"""
    test_cases = load_test_cases()
    
    print("\n" + "="*60)
    print("📋 AVAILABLE TEST CASES")
    print("="*60)
    
    for tc in test_cases:
        expected = tc["expected_output"]["decision"]
        emoji = "✅" if expected == "APPROVED" else "⚠️" if expected in ["PARTIAL", "MANUAL_REVIEW"] else "❌"
        print(f"\n{emoji} {tc['case_id']}: {tc['case_name']}")
        print(f"   {tc['description']}")
        print(f"   Expected: {expected}")


def run_single_test(case_id):
    """Run a single test case by ID"""
    test_cases = load_test_cases()
    
    test_case = None
    for tc in test_cases:
        if tc["case_id"].upper() == case_id.upper():
            test_case = tc
            break
    
    if not test_case:
        print(f"❌ Test case '{case_id}' not found")
        list_test_cases()
        return
    
    if not test_health():
        print("\n❌ Backend is not running. Start it with: python -m app.main")
        return
    
    api_payload = convert_test_case_to_api_format(test_case)
    result = test_submit_claim(api_payload, test_case)
    
    return result


def run_all_tests():
    """Run all test cases from test_cases.json"""
    print("\n" + "="*60)
    print("🏥 OPD CLAIM ADJUDICATION SYSTEM - API TESTS")
    print("   Loading test cases from: docs/test_cases.json")
    print("="*60)
    
    # First check health
    if not test_health():
        print("\n❌ Backend is not running. Start it with: python -m app.main")
        return
    
    # Reset database before running tests
    print("\n🗑️ Resetting database for clean test run...")
    try:
        response = requests.delete(f"{BASE_URL}/api/test/reset-database")
        if response.status_code == 200:
            print("   ✓ Database reset successful")
        else:
            print(f"   ⚠ Could not reset database: {response.text}")
    except Exception as e:
        print(f"   ⚠ Could not reset database: {e}")
    
    # Load test cases
    test_cases = load_test_cases()
    if not test_cases:
        return
    
    print(f"\n📋 Running {len(test_cases)} test cases...")
    
    results = []
    for test_case in test_cases:
        api_payload = convert_test_case_to_api_format(test_case)
        result = test_submit_claim(api_payload, test_case)
        if result:
            results.append(result)
    
    # Summary
    print("\n\n" + "="*60)
    print("📊 TEST RESULTS SUMMARY")
    print("="*60)
    
    passed = 0
    failed = 0
    
    for r in results:
        if r["passed"]:
            print(f"✅ {r['case_id']}: {r['case_name']} - {r['actual_decision']}")
            passed += 1
        else:
            print(f"❌ {r['case_id']}: {r['case_name']} - Expected {r['expected_decision']}, Got {r['actual_decision']}")
            failed += 1
    
    print("\n" + "-"*60)
    print(f"📈 Results: {passed}/{len(results)} passed ({100*passed//len(results) if results else 0}%)")
    
    # Get all claims
    test_get_claims()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--list":
            list_test_cases()
        elif arg.upper().startswith("TC"):
            run_single_test(arg)
        else:
            print(f"Unknown argument: {arg}")
            print("Usage:")
            print("  python test_api.py           # Run all tests")
            print("  python test_api.py TC001     # Run specific test")
            print("  python test_api.py --list    # List all tests")
    else:
        run_all_tests()
