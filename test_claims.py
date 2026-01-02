"""
Test script to verify the OPD Claim Adjudication system.
Run this after setting up your environment.

Usage:
    python test_claims.py              # Run all tests
    python test_claims.py TC001        # Run specific test case
    python test_claims.py --list       # List all test cases
"""

import json
import sys
from pathlib import Path
from app.workflows.claim_adjudication import process_claim, format_result_for_api


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


def convert_test_case_to_claim_format(test_case):
    """Convert test_cases.json format to process_claim input format"""
    input_data = test_case["input_data"]
    
    claim_input = {
        "member_id": input_data.get("member_id"),
        "member_name": input_data.get("member_name"),
        "treatment_date": input_data.get("treatment_date"),
        "claim_amount": input_data.get("claim_amount"),
        "documents": input_data.get("documents", {}),
        # Default join date if not provided (long-standing member)
        "member_join_date": input_data.get("member_join_date", "2024-01-01")
    }
    
    # Add optional fields
    if "hospital" in input_data:
        claim_input["hospital"] = input_data["hospital"]
    
    if "cashless_request" in input_data:
        claim_input["cashless_request"] = input_data["cashless_request"]
    
    if "previous_claims_same_day" in input_data:
        claim_input["previous_claims_same_day"] = input_data["previous_claims_same_day"]
    
    return claim_input


def list_test_cases():
    """List all available test cases"""
    test_cases = load_test_cases()
    
    print("\n" + "="*80)
    print("📋 AVAILABLE TEST CASES (from docs/test_cases.json)")
    print("="*80)
    
    for tc in test_cases:
        expected = tc["expected_output"]["decision"]
        emoji = "✅" if expected == "APPROVED" else "⚠️" if expected in ["PARTIAL", "MANUAL_REVIEW"] else "❌"
        print(f"\n{emoji} {tc['case_id']}: {tc['case_name']}")
        print(f"   {tc['description']}")
        print(f"   Expected Decision: {expected}")
        if "approved_amount" in tc["expected_output"]:
            print(f"   Expected Amount: ₹{tc['expected_output']['approved_amount']}")


def run_single_test(case_id: str):
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
        return None
    
    print(f"\n📋 Running: {test_case['case_id']} - {test_case['case_name']}")
    print(f"📝 {test_case['description']}")
    print("-"*60)
    
    claim_input = convert_test_case_to_claim_format(test_case)
    expected = test_case["expected_output"]
    
    try:
        result = process_claim(claim_input)
        api_result = format_result_for_api(result)
        
        print(f"\n📊 RESULT:")
        print(json.dumps(api_result, indent=2))
        
        print(f"\n🎯 EXPECTED vs ACTUAL:")
        expected_decision = expected["decision"]
        actual_decision = api_result["decision"]
        
        decision_match = actual_decision == expected_decision
        print(f"   Decision: {expected_decision} → {actual_decision} {'✅' if decision_match else '❌'}")
        
        if "approved_amount" in expected:
            expected_amount = expected["approved_amount"]
            actual_amount = api_result["approved_amount"]
            amount_match = abs(actual_amount - expected_amount) < 100
            print(f"   Amount: ₹{expected_amount} → ₹{actual_amount} {'✅' if amount_match else '⚠️'}")
        
        return api_result
        
    except Exception as e:
        print(f"❌ ERROR - {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def run_tests():
    """Run all test cases from test_cases.json"""
    print("\n" + "="*80)
    print("🧪 OPD CLAIM ADJUDICATION - TEST SUITE")
    print("   Loading test cases from: docs/test_cases.json")
    print("="*80)
    
    test_cases = load_test_cases()
    if not test_cases:
        return 0, 0
    
    print(f"\n📋 Running {len(test_cases)} test cases...\n")
    
    passed = 0
    failed = 0
    results = []
    
    for test_case in test_cases:
        case_id = test_case["case_id"]
        case_name = test_case["case_name"]
        expected = test_case["expected_output"]
        expected_decision = expected["decision"]
        
        print(f"\n{'='*60}")
        print(f"📋 {case_id}: {case_name}")
        print(f"📝 {test_case['description']}")
        print("-"*60)
        
        claim_input = convert_test_case_to_claim_format(test_case)
        
        try:
            result = process_claim(claim_input)
            api_result = format_result_for_api(result)
            
            actual_decision = api_result["decision"]
            
            # Check decision match
            decision_match = actual_decision == expected_decision
            
            if decision_match:
                print(f"✅ PASSED - Decision: {actual_decision}")
                passed += 1
            else:
                print(f"❌ FAILED - Expected: {expected_decision}, Got: {actual_decision}")
                failed += 1
            
            # Show details
            print(f"   Approved Amount: ₹{api_result['approved_amount']:,.2f}")
            print(f"   Confidence: {api_result['confidence_score']}%")
            
            if api_result['rejection_reasons']:
                print(f"   Rejection Reasons: {api_result['rejection_reasons']}")
            if api_result['rejected_items']:
                print(f"   Rejected Items: {api_result['rejected_items'][:3]}")
            if api_result.get('fraud_flags'):
                print(f"   Fraud Flags: {api_result['fraud_flags']}")
            
            # Compare amounts if expected
            if "approved_amount" in expected:
                expected_amount = expected["approved_amount"]
                actual_amount = api_result["approved_amount"]
                if abs(actual_amount - expected_amount) > 100:
                    print(f"   ⚠️ Amount mismatch: Expected ₹{expected_amount}, Got ₹{actual_amount}")
            
            results.append({
                "case_id": case_id,
                "case_name": case_name,
                "expected": expected_decision,
                "actual": actual_decision,
                "passed": decision_match
            })
                
        except Exception as e:
            print(f"❌ ERROR - {str(e)}")
            failed += 1
            results.append({
                "case_id": case_id,
                "case_name": case_name,
                "expected": expected_decision,
                "actual": "ERROR",
                "passed": False
            })
    
    # Summary
    print("\n" + "="*80)
    print("📊 TEST RESULTS SUMMARY")
    print("="*80)
    
    for r in results:
        emoji = "✅" if r["passed"] else "❌"
        print(f"{emoji} {r['case_id']}: {r['case_name']}")
        if not r["passed"]:
            print(f"      Expected: {r['expected']} → Got: {r['actual']}")
    
    print("\n" + "-"*80)
    total = len(test_cases)
    percentage = (passed / total * 100) if total > 0 else 0
    print(f"📈 Results: {passed}/{total} passed ({percentage:.1f}%)")
    print("="*80 + "\n")
    
    return passed, failed


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
            print("  python test_claims.py           # Run all tests")
            print("  python test_claims.py TC001     # Run specific test")
            print("  python test_claims.py --list    # List all tests")
    else:
        run_tests()
