"""
Script to create sample test PDF documents for OPD Claim testing.
Run this to generate prescription and bill PDFs.

Requirements: pip install reportlab
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.pdfgen import canvas
from datetime import datetime
import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


def create_prescription_pdf(
    filename: str,
    doctor_name: str,
    doctor_reg: str,
    patient_name: str,
    diagnosis: str,
    medicines: list,
    tests: list = None,
    date: str = None
):
    """Create a medical prescription PDF."""
    filepath = os.path.join(OUTPUT_DIR, filename)
    c = canvas.Canvas(filepath, pagesize=A4)
    width, height = A4
    
    # Date
    if not date:
        date = datetime.now().strftime("%d/%m/%Y")
    
    # Header - Clinic info
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "City Medical Centre")
    
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 70, f"{doctor_name}, MBBS, MD")
    c.drawString(50, height - 85, f"Reg. No: {doctor_reg}")
    c.drawString(50, height - 100, "123 Medical Street, City - 560001")
    c.drawString(50, height - 115, "Phone: +91-9876543210")
    
    # Line separator
    c.setStrokeColor(colors.black)
    c.line(50, height - 130, width - 50, height - 130)
    
    # Date
    c.setFont("Helvetica", 11)
    c.drawString(width - 150, height - 150, f"Date: {date}")
    
    # Patient Details
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 170, "Patient Details:")
    c.setFont("Helvetica", 11)
    c.drawString(50, height - 190, f"Name: {patient_name}")
    c.drawString(50, height - 205, "Age: 35 years | Gender: Male")
    
    # Diagnosis
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 240, "Diagnosis:")
    c.setFont("Helvetica", 11)
    c.drawString(50, height - 260, diagnosis)
    
    # Prescription
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 300, "Rx")
    
    c.setFont("Helvetica", 11)
    y_pos = height - 325
    for i, med in enumerate(medicines, 1):
        c.drawString(70, y_pos, f"{i}. {med}")
        y_pos -= 20
    
    # Tests if any
    if tests:
        y_pos -= 20
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y_pos, "Investigations Advised:")
        c.setFont("Helvetica", 11)
        y_pos -= 20
        for test in tests:
            c.drawString(70, y_pos, f"• {test}")
            y_pos -= 18
    
    # Footer
    y_pos -= 40
    c.setFont("Helvetica", 10)
    c.drawString(50, y_pos, "Follow-up: After 7 days if symptoms persist")
    
    # Signature area
    c.drawString(width - 200, 100, "________________________")
    c.drawString(width - 200, 85, f"{doctor_name}")
    c.drawString(width - 200, 70, "Signature & Stamp")
    
    c.save()
    print(f"✓ Created: {filepath}")
    return filepath


def create_bill_pdf(
    filename: str,
    patient_name: str,
    items: dict,
    bill_number: str = None,
    date: str = None
):
    """Create a medical bill PDF."""
    filepath = os.path.join(OUTPUT_DIR, filename)
    c = canvas.Canvas(filepath, pagesize=A4)
    width, height = A4
    
    if not date:
        date = datetime.now().strftime("%d/%m/%Y")
    if not bill_number:
        bill_number = f"BILL-{datetime.now().strftime('%Y%m%d%H%M')}"
    
    # Header
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, height - 50, "City Medical Centre")
    
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 70, "123 Medical Street, City - 560001")
    c.drawString(50, height - 85, "GST No: 29ABCDE1234F1Z5")
    c.drawString(50, height - 100, "Phone: +91-9876543210")
    
    # Bill title
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width/2, height - 130, "MEDICAL BILL / RECEIPT")
    
    # Line separator
    c.line(50, height - 145, width - 50, height - 145)
    
    # Bill details
    c.setFont("Helvetica", 11)
    c.drawString(50, height - 165, f"Bill No: {bill_number}")
    c.drawString(width - 180, height - 165, f"Date: {date}")
    
    c.drawString(50, height - 185, f"Patient Name: {patient_name}")
    
    # Items table
    y_pos = height - 220
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y_pos, "PARTICULARS")
    c.drawString(width - 150, y_pos, "AMOUNT (₹)")
    
    c.line(50, y_pos - 5, width - 50, y_pos - 5)
    
    c.setFont("Helvetica", 11)
    y_pos -= 25
    total = 0
    
    for item, amount in items.items():
        c.drawString(50, y_pos, item)
        c.drawString(width - 150, y_pos, f"₹ {amount:,.2f}")
        total += amount
        y_pos -= 20
    
    # Total
    c.line(50, y_pos, width - 50, y_pos)
    y_pos -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y_pos, "TOTAL")
    c.drawString(width - 150, y_pos, f"₹ {total:,.2f}")
    
    # Payment info
    y_pos -= 40
    c.setFont("Helvetica", 10)
    c.drawString(50, y_pos, f"Amount in words: Rupees {int(total)} only")
    c.drawString(50, y_pos - 20, "Payment Mode: Cash / Card / UPI")
    
    # Footer
    c.drawString(width - 200, 100, "________________________")
    c.drawString(width - 200, 85, "Authorized Signatory")
    c.drawString(width - 200, 70, "Stamp")
    
    # Thank you note
    c.setFont("Helvetica-Oblique", 9)
    c.drawCentredString(width/2, 40, "Thank you for choosing City Medical Centre. Get well soon!")
    
    c.save()
    print(f"✓ Created: {filepath}")
    return filepath


def create_all_test_documents():
    """Create all sample test documents."""
    print("\n" + "="*60)
    print("Creating Sample Test Documents for OPD Claim Testing")
    print("="*60 + "\n")
    
    # Test Case 1: Simple Consultation (APPROVED)
    print("📄 Test Case 1: Simple Consultation")
    create_prescription_pdf(
        filename="tc1_prescription_fever.pdf",
        doctor_name="Dr. Sharma",
        doctor_reg="KA/45678/2015",
        patient_name="Rajesh Kumar",
        diagnosis="Viral fever with body ache",
        medicines=[
            "Tab. Paracetamol 650mg - 1 tab thrice daily x 5 days",
            "Tab. Vitamin C 500mg - 1 tab daily x 10 days",
            "Syp. Cough Suppressant - 10ml thrice daily x 5 days"
        ],
        tests=["CBC (Complete Blood Count)", "Dengue NS1 Antigen Test"]
    )
    create_bill_pdf(
        filename="tc1_bill_fever.pdf",
        patient_name="Rajesh Kumar",
        items={
            "Consultation Fee": 1000,
            "CBC Test": 300,
            "Dengue Test": 200,
        }
    )
    
    # Test Case 2: Dental Treatment (PARTIAL - cosmetic excluded)
    print("\n📄 Test Case 2: Dental Treatment")
    create_prescription_pdf(
        filename="tc2_prescription_dental.pdf",
        doctor_name="Dr. Patel",
        doctor_reg="MH/23456/2018",
        patient_name="Priya Singh",
        diagnosis="Tooth decay requiring root canal treatment",
        medicines=[
            "Cap. Amoxicillin 500mg - 1 cap thrice daily x 5 days",
            "Tab. Ibuprofen 400mg - 1 tab twice daily x 3 days (after food)"
        ],
        tests=[]
    )
    create_bill_pdf(
        filename="tc2_bill_dental.pdf",
        patient_name="Priya Singh",
        items={
            "Root Canal Treatment": 8000,
            "Teeth Whitening (Cosmetic)": 4000,  # This will be excluded
        }
    )
    
    # Test Case 3: High Amount (REJECTED - exceeds limit)
    print("\n📄 Test Case 3: Limit Exceeded")
    create_prescription_pdf(
        filename="tc3_prescription_gastro.pdf",
        doctor_name="Dr. Gupta",
        doctor_reg="DL/34567/2016",
        patient_name="Amit Verma",
        diagnosis="Acute Gastroenteritis",
        medicines=[
            "Tab. Ciprofloxacin 500mg - 1 tab twice daily x 5 days",
            "Cap. Probiotics - 1 cap twice daily x 10 days",
            "ORS Sachets - As needed",
            "Tab. Ondansetron 4mg - 1 tab as needed for vomiting"
        ]
    )
    create_bill_pdf(
        filename="tc3_bill_gastro.pdf",
        patient_name="Amit Verma",
        items={
            "Consultation Fee": 2000,
            "Medicines": 5500,  # Total 7500, exceeds 5000 limit
        }
    )
    
    # Test Case 6: Alternative Medicine (APPROVED - Ayurveda covered)
    print("\n📄 Test Case 6: Alternative Medicine (Ayurveda)")
    create_prescription_pdf(
        filename="tc6_prescription_ayurveda.pdf",
        doctor_name="Vaidya Krishnan",
        doctor_reg="AYUR/KL/2345/2019",
        patient_name="Kavita Nair",
        diagnosis="Chronic joint pain - Sandhivata",
        medicines=[
            "Panchakarma Therapy - Abhyanga (Oil Massage)",
            "Panchakarma - Swedana (Steam Therapy)",
            "Maharasnadi Kashayam - 15ml twice daily",
            "Yogaraja Guggulu - 2 tablets twice daily"
        ]
    )
    create_bill_pdf(
        filename="tc6_bill_ayurveda.pdf",
        patient_name="Kavita Nair",
        items={
            "Consultation Fee": 1000,
            "Panchakarma Therapy (5 sessions)": 3000,
        }
    )
    
    # Test Case 9: Weight Loss (REJECTED - excluded treatment)
    print("\n📄 Test Case 9: Weight Loss Treatment (Excluded)")
    create_prescription_pdf(
        filename="tc9_prescription_obesity.pdf",
        doctor_name="Dr. Banerjee",
        doctor_reg="WB/34567/2015",
        patient_name="Anita Desai",
        diagnosis="Obesity - BMI 35 - Morbid Obesity",
        medicines=[
            "Bariatric consultation",
            "Diet plan - 1200 calorie program",
            "Weight loss supplements"
        ]
    )
    create_bill_pdf(
        filename="tc9_bill_obesity.pdf",
        patient_name="Anita Desai",
        items={
            "Bariatric Consultation": 3000,
            "Diet Plan Package": 5000,
        }
    )
    
    # Test Case 7: MRI Scan (REJECTED - pre-auth required)
    print("\n📄 Test Case 7: MRI Scan (Pre-auth Required)")
    create_prescription_pdf(
        filename="tc7_prescription_mri.pdf",
        doctor_name="Dr. Rao",
        doctor_reg="AP/67890/2017",
        patient_name="Suresh Patil",
        diagnosis="Suspected lumbar disc herniation with radiculopathy",
        medicines=[
            "Tab. Pregabalin 75mg - 1 tab at night x 15 days",
            "Tab. Etoricoxib 90mg - 1 tab daily x 7 days"
        ],
        tests=["MRI Lumbar Spine with contrast"]
    )
    create_bill_pdf(
        filename="tc7_bill_mri.pdf",
        patient_name="Suresh Patil",
        items={
            "MRI Lumbar Spine": 15000,  # Exceeds pre-auth threshold
        }
    )
    
    print("\n" + "="*60)
    print("✅ All test documents created successfully!")
    print(f"📁 Location: {OUTPUT_DIR}")
    print("="*60)
    print("\nYou can now upload these PDFs to the frontend for testing.")
    print("\nDocument pairs for each test case:")
    print("  • TC1 (APPROVED): tc1_prescription_fever.pdf + tc1_bill_fever.pdf")
    print("  • TC2 (PARTIAL):  tc2_prescription_dental.pdf + tc2_bill_dental.pdf")
    print("  • TC3 (REJECTED): tc3_prescription_gastro.pdf + tc3_bill_gastro.pdf")
    print("  • TC6 (APPROVED): tc6_prescription_ayurveda.pdf + tc6_bill_ayurveda.pdf")
    print("  • TC7 (REJECTED): tc7_prescription_mri.pdf + tc7_bill_mri.pdf")
    print("  • TC9 (REJECTED): tc9_prescription_obesity.pdf + tc9_bill_obesity.pdf")


if __name__ == "__main__":
    create_all_test_documents()
