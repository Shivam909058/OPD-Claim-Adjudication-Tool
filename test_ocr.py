"""
Test Document OCR Functionality
Tests the document processing and OCR capabilities.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.tools.document_ocr import DocumentProcessor, MedicalDocumentParser


def test_ocr_availability():
    """Check which OCR libraries are available."""
    print("\n" + "="*60)
    print("📋 OCR Library Availability Check")
    print("="*60)
    
    try:
        import pdfplumber
        print("✅ pdfplumber installed - PDF text extraction available")
    except ImportError:
        print("❌ pdfplumber not installed")
    
    try:
        import pytesseract
        print("✅ pytesseract installed - Tesseract OCR available")
        # Check if Tesseract is actually installed on system
        try:
            pytesseract.get_tesseract_version()
            print("   ✅ Tesseract OCR engine found on system")
        except Exception:
            print("   ⚠️ Tesseract not found. Install from: https://github.com/tesseract-ocr/tesseract")
    except ImportError:
        print("❌ pytesseract not installed")
    
    try:
        import easyocr
        print("✅ easyocr installed - Deep learning OCR available")
    except ImportError:
        print("⚠️ easyocr not installed (optional, for better accuracy)")
    
    try:
        from PIL import Image
        print("✅ Pillow installed - Image processing available")
    except ImportError:
        print("❌ Pillow not installed")
    
    try:
        from pdf2image import convert_from_path
        print("✅ pdf2image installed - PDF to image conversion available")
    except ImportError:
        print("⚠️ pdf2image not installed (needed for scanned PDFs)")


def test_sample_prescription_parsing():
    """Test prescription text parsing."""
    print("\n" + "="*60)
    print("📝 Testing Prescription Parsing")
    print("="*60)
    
    # Sample prescription text (simulating OCR output)
    sample_prescription = """
    Apollo Hospital
    Date: 15-Nov-2024
    
    Dr. Sharma MBBS, MD
    Reg. No: KA/45678/2015
    
    Patient: Rajesh Kumar
    Age: 35 years
    
    Diagnosis: Viral Fever with Upper Respiratory Infection
    
    Rx
    1. Tab. Paracetamol 650mg - 1 tablet thrice daily for 5 days
    2. Cap. Amoxicillin 500mg - 1 capsule twice daily for 5 days
    3. Syrup Benadryl 100ml - 2 tsp at night
    4. Tab. Vitamin C 500mg - once daily
    
    Investigations Advised:
    CBC, Dengue NS1
    
    Follow up after 5 days
    """
    
    parser = MedicalDocumentParser()
    result = parser.parse_prescription(sample_prescription)
    
    print(f"\nDoctor Name: {result.get('doctor_name', 'Not found')}")
    print(f"Registration: {result.get('doctor_reg', 'Not found')}")
    print(f"Diagnosis: {result.get('diagnosis', 'Not found')}")
    print(f"Medicines: {result.get('medicines_prescribed', [])}")
    print(f"Tests: {result.get('tests_prescribed', [])}")
    print(f"Date: {result.get('prescription_date', 'Not found')}")
    
    return result


def test_sample_bill_parsing():
    """Test bill text parsing."""
    print("\n" + "="*60)
    print("🧾 Testing Bill Parsing")
    print("="*60)
    
    # Sample bill text
    sample_bill = """
    APOLLO HOSPITAL
    Patient Bill / Invoice
    
    Bill No: APO-2024-123456
    Date: 15-Nov-2024
    
    Patient Name: Rajesh Kumar
    
    PARTICULARS                        AMOUNT
    -----------------------------------------
    Consultation Fee                   Rs. 1000
    Lab Tests (CBC, Dengue)            Rs. 800
    Medicines                          Rs. 450
    -----------------------------------------
    Sub Total                          Rs. 2250
    Discount (10%)                     Rs. 225
    -----------------------------------------
    Grand Total                        Rs. 2025/-
    
    Payment Mode: Cash
    Thank you for choosing Apollo Hospital
    """
    
    parser = MedicalDocumentParser()
    result = parser.parse_bill(sample_bill)
    
    print(f"\nHospital: {result.get('hospital_name', 'Not found')}")
    print(f"Bill Number: {result.get('bill_number', 'Not found')}")
    print(f"Consultation Fee: ₹{result.get('consultation_fee', 0)}")
    print(f"Diagnostic Tests: ₹{result.get('diagnostic_tests', 0)}")
    print(f"Medicines: ₹{result.get('medicines', 0)}")
    print(f"Total Amount: ₹{result.get('total_amount', 0)}")
    print(f"Line Items: {result.get('line_items', [])}")
    
    return result


def test_pdf_extraction(pdf_path: str = None):
    """Test PDF extraction if a file path is provided."""
    if not pdf_path:
        print("\n⚠️ No PDF path provided. Skipping PDF test.")
        print("   To test: python test_ocr.py path/to/document.pdf")
        return
    
    print("\n" + "="*60)
    print(f"📄 Testing PDF Extraction: {pdf_path}")
    print("="*60)
    
    processor = DocumentProcessor()
    result = processor.process_file(pdf_path)
    
    if result.get("success"):
        print(f"✅ Extraction successful!")
        print(f"Method: {result.get('method')}")
        print(f"Pages: {result.get('page_count', 'N/A')}")
        print(f"\nExtracted Text (first 500 chars):")
        print("-" * 40)
        text = result.get("text", "")
        print(text[:500] if len(text) > 500 else text)
        print("-" * 40)
    else:
        print(f"❌ Extraction failed: {result.get('error')}")


def run_all_tests():
    """Run all OCR tests."""
    print("\n" + "="*60)
    print("🔬 DOCUMENT OCR TEST SUITE")
    print("="*60)
    
    test_ocr_availability()
    test_sample_prescription_parsing()
    test_sample_bill_parsing()
    
    # Check if a file was provided as argument
    if len(sys.argv) > 1:
        test_pdf_extraction(sys.argv[1])
    else:
        print("\n💡 Tip: To test with a real document:")
        print("   python test_ocr.py path/to/prescription.pdf")
        print("   python test_ocr.py path/to/bill.jpg")


if __name__ == "__main__":
    run_all_tests()
