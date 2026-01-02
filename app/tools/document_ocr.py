"""
Document Processing Module for OCR and Text Extraction
Uses open-source libraries: pytesseract, pdfplumber, easyocr
"""

import os
import io
import re
import base64
import tempfile
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

# PDF text extraction
try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False
    print("Warning: pdfplumber not installed. PDF text extraction limited.")

# Image OCR with Tesseract
try:
    import pytesseract
    from PIL import Image
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False
    print("Warning: pytesseract not installed. Image OCR limited.")

# Deep learning OCR (optional, better accuracy)
try:
    import easyocr
    HAS_EASYOCR = True
    # Initialize reader (downloads models on first use)
    _easyocr_reader = None
except ImportError:
    HAS_EASYOCR = False
    _easyocr_reader = None


def get_easyocr_reader():
    """Lazy load EasyOCR reader to avoid slow startup."""
    global _easyocr_reader
    if HAS_EASYOCR and _easyocr_reader is None:
        _easyocr_reader = easyocr.Reader(['en'], gpu=False)
    return _easyocr_reader


class DocumentProcessor:
    """
    Processes medical documents (PDFs and images) to extract text.
    Uses multiple OCR backends for best results.
    """
    
    def __init__(self, use_easyocr: bool = False):
        """
        Initialize document processor.
        
        Args:
            use_easyocr: Use EasyOCR (better accuracy but slower). 
                         Falls back to Tesseract if False.
        """
        self.use_easyocr = use_easyocr and HAS_EASYOCR
        
    def process_file(self, file_path: str) -> Dict[str, Any]:
        """
        Process a file and extract text.
        
        Args:
            file_path: Path to the file (PDF or image)
            
        Returns:
            Dict with extracted text and metadata
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}
        
        extension = file_path.suffix.lower()
        
        if extension == '.pdf':
            return self._process_pdf(file_path)
        elif extension in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']:
            return self._process_image(file_path)
        else:
            return {"success": False, "error": f"Unsupported file type: {extension}"}
    
    def process_bytes(self, file_bytes: bytes, file_type: str) -> Dict[str, Any]:
        """
        Process file from bytes.
        
        Args:
            file_bytes: File content as bytes
            file_type: 'pdf', 'image', or file extension
            
        Returns:
            Dict with extracted text
        """
        # Create temp file
        suffix = f".{file_type.replace('.', '')}"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        
        try:
            result = self.process_file(tmp_path)
        finally:
            os.unlink(tmp_path)
        
        return result
    
    def process_base64(self, base64_data: str, file_type: str) -> Dict[str, Any]:
        """
        Process file from base64 encoded string.
        
        Args:
            base64_data: Base64 encoded file content
            file_type: File type/extension
            
        Returns:
            Dict with extracted text
        """
        try:
            file_bytes = base64.b64decode(base64_data)
            return self.process_bytes(file_bytes, file_type)
        except Exception as e:
            return {"success": False, "error": f"Base64 decode error: {str(e)}"}
    
    def _process_pdf(self, file_path: Path) -> Dict[str, Any]:
        """Extract text from PDF."""
        text_content = []
        tables = []
        
        # Try pdfplumber first (best for text-based PDFs)
        if HAS_PDFPLUMBER:
            try:
                with pdfplumber.open(file_path) as pdf:
                    for i, page in enumerate(pdf.pages):
                        # Extract text
                        page_text = page.extract_text() or ""
                        if page_text.strip():
                            text_content.append(f"--- Page {i+1} ---\n{page_text}")
                        
                        # Extract tables (useful for bills)
                        page_tables = page.extract_tables()
                        for table in page_tables:
                            tables.append(table)
                
                if text_content:
                    return {
                        "success": True,
                        "method": "pdfplumber",
                        "text": "\n\n".join(text_content),
                        "tables": tables,
                        "page_count": len(pdf.pages)
                    }
            except Exception as e:
                print(f"pdfplumber error: {e}")
        
        # Fallback: Convert PDF to images and OCR
        return self._pdf_to_image_ocr(file_path)
    
    def _pdf_to_image_ocr(self, file_path: Path) -> Dict[str, Any]:
        """Convert PDF to images and perform OCR."""
        try:
            from pdf2image import convert_from_path
            
            # Convert PDF to images
            images = convert_from_path(file_path, dpi=300)
            
            text_content = []
            for i, image in enumerate(images):
                page_text = self._ocr_image(image)
                if page_text:
                    text_content.append(f"--- Page {i+1} ---\n{page_text}")
            
            return {
                "success": True,
                "method": "pdf2image+ocr",
                "text": "\n\n".join(text_content),
                "page_count": len(images)
            }
        except Exception as e:
            return {"success": False, "error": f"PDF OCR error: {str(e)}"}
    
    def _process_image(self, file_path: Path) -> Dict[str, Any]:
        """Extract text from image using OCR."""
        try:
            image = Image.open(file_path)
            text = self._ocr_image(image)
            
            return {
                "success": True,
                "method": "easyocr" if self.use_easyocr else "tesseract",
                "text": text,
                "image_size": image.size
            }
        except Exception as e:
            return {"success": False, "error": f"Image OCR error: {str(e)}"}
    
    def _ocr_image(self, image: Image.Image) -> str:
        """Perform OCR on a PIL Image."""
        # Try EasyOCR first (better accuracy for complex documents)
        if self.use_easyocr and HAS_EASYOCR:
            try:
                reader = get_easyocr_reader()
                # Convert PIL to numpy array
                import numpy as np
                image_np = np.array(image)
                results = reader.readtext(image_np)
                # Combine detected text
                text = "\n".join([r[1] for r in results])
                return text
            except Exception as e:
                print(f"EasyOCR error: {e}, falling back to Tesseract")
        
        # Tesseract OCR
        if HAS_TESSERACT:
            try:
                # Preprocess image for better OCR
                image = self._preprocess_image(image)
                text = pytesseract.image_to_string(image, lang='eng')
                return text
            except Exception as e:
                return f"OCR Error: {str(e)}"
        
        return "No OCR engine available. Install pytesseract or easyocr."
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """Preprocess image for better OCR results."""
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Convert to grayscale
        image = image.convert('L')
        
        # Increase contrast (simple thresholding)
        # This helps with scanned documents
        threshold = 150
        image = image.point(lambda p: 255 if p > threshold else 0)
        
        return image


class MedicalDocumentParser:
    """
    Parses extracted text to identify medical document fields.
    Works with prescriptions and medical bills.
    """
    
    def __init__(self):
        self.processor = DocumentProcessor(use_easyocr=False)  # Tesseract by default
    
    def parse_prescription(self, text: str) -> Dict[str, Any]:
        """
        Parse prescription text to extract structured data.
        
        Args:
            text: Raw text from prescription document
            
        Returns:
            Structured prescription data
        """
        result = {
            "doctor_name": None,
            "doctor_reg": None,
            "diagnosis": None,
            "medicines_prescribed": [],
            "tests_prescribed": [],
            "procedures": [],
            "prescription_date": None,
            "patient_name": None,
            "raw_text": text
        }
        
        lines = text.split('\n')
        
        # Extract doctor name (usually near "Dr." or "Doctor")
        for line in lines:
            if re.search(r'\bDr\.?\s+[A-Z]', line, re.IGNORECASE):
                match = re.search(r'Dr\.?\s+([A-Za-z\s\.]+)', line, re.IGNORECASE)
                if match:
                    result["doctor_name"] = match.group(1).strip()
                    break
        
        # Extract registration number
        reg_patterns = [
            r'Reg\.?\s*(?:No\.?)?\s*:?\s*([A-Z]{2,4}/\d+/\d{4})',  # KA/12345/2020
            r'Registration\s*:?\s*([A-Z]{2,4}/\d+/\d{4})',
            r'MCI\s*(?:No\.?)?\s*:?\s*(\d+)',
            r'([A-Z]{2,4}/\d{4,6}/\d{4})'  # Generic pattern
        ]
        for pattern in reg_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result["doctor_reg"] = match.group(1)
                break
        
        # Extract diagnosis (look for keywords)
        diagnosis_patterns = [
            r'Diagnosis\s*:?\s*(.+?)(?:\n|$)',
            r'Chief\s+Complaint\s*:?\s*(.+?)(?:\n|$)',
            r'Impression\s*:?\s*(.+?)(?:\n|$)',
            r'Provisional\s+Diagnosis\s*:?\s*(.+?)(?:\n|$)'
        ]
        for pattern in diagnosis_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result["diagnosis"] = match.group(1).strip()
                break
        
        # Extract medicines (look for common medicine patterns)
        medicine_section = False
        for line in lines:
            line = line.strip()
            if re.search(r'R[xX]|Medicines?|Prescription|Tab\.|Cap\.', line, re.IGNORECASE):
                medicine_section = True
                continue
            
            if medicine_section and line:
                # Check if it looks like a medicine entry
                if re.search(r'Tab\.|Cap\.|Syrup|mg|ml|Inj\.|times|daily|BD|TDS|OD', line, re.IGNORECASE):
                    result["medicines_prescribed"].append(line)
                elif re.search(r'^[A-Z][a-z]+\s+\d', line):  # Medicine name with dosage
                    result["medicines_prescribed"].append(line)
        
        # Extract tests
        test_patterns = [
            r'(?:Investigations?|Tests?|Lab)\s*:?\s*(.+?)(?:\n|$)',
            r'Advice[d]?\s+(?:for\s+)?(?:Tests?|Investigations?)\s*:?\s*(.+?)(?:\n|$)'
        ]
        for pattern in test_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                tests = match.group(1).split(',')
                result["tests_prescribed"] = [t.strip() for t in tests if t.strip()]
                break
        
        # Common test names
        common_tests = ['CBC', 'LFT', 'KFT', 'Blood Sugar', 'X-Ray', 'MRI', 'CT Scan', 
                       'Ultrasound', 'ECG', 'Lipid Profile', 'Thyroid', 'Urine']
        for test in common_tests:
            if re.search(rf'\b{test}\b', text, re.IGNORECASE):
                if test not in result["tests_prescribed"]:
                    result["tests_prescribed"].append(test)
        
        # Extract date
        date_patterns = [
            r'Date\s*:?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})'
        ]
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result["prescription_date"] = match.group(1)
                break
        
        return result
    
    def parse_bill(self, text: str) -> Dict[str, Any]:
        """
        Parse medical bill text to extract structured data.
        
        Args:
            text: Raw text from bill document
            
        Returns:
            Structured bill data
        """
        result = {
            "hospital_name": None,
            "bill_number": None,
            "bill_date": None,
            "patient_name": None,
            "consultation_fee": 0,
            "diagnostic_tests": 0,
            "medicines": 0,
            "procedures": 0,
            "total_amount": 0,
            "line_items": [],
            "raw_text": text
        }
        
        lines = text.split('\n')
        
        # Extract hospital name (usually in header)
        hospital_patterns = [
            r'([\w\s]+(?:Hospital|Clinic|Healthcare|Medical\s+Centre|Diagnostics))',
            r'^([A-Z][\w\s]+)(?:\n|$)'  # First capitalized line
        ]
        for pattern in hospital_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result["hospital_name"] = match.group(1).strip()
                break
        
        # Extract bill number
        bill_patterns = [
            r'(?:Bill|Invoice|Receipt)\s*(?:No\.?|#)?\s*:?\s*([A-Z0-9-]+)',
            r'(?:Bill|Invoice)\s*:?\s*([A-Z0-9-]+)'
        ]
        for pattern in bill_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result["bill_number"] = match.group(1)
                break
        
        # Extract amounts using regex
        amount_patterns = {
            "consultation_fee": [
                r'Consultation\s*(?:Fee|Charges?)?\s*:?\s*(?:Rs\.?|₹)?\s*([\d,]+)',
                r'Doctor\s*(?:Fee|Charges?)?\s*:?\s*(?:Rs\.?|₹)?\s*([\d,]+)'
            ],
            "diagnostic_tests": [
                r'(?:Lab|Diagnostic|Test)\s*(?:Charges?)?\s*:?\s*(?:Rs\.?|₹)?\s*([\d,]+)',
                r'Investigation\s*(?:Charges?)?\s*:?\s*(?:Rs\.?|₹)?\s*([\d,]+)'
            ],
            "medicines": [
                r'(?:Medicine|Pharmacy|Drug)\s*(?:Charges?)?\s*:?\s*(?:Rs\.?|₹)?\s*([\d,]+)'
            ],
            "procedures": [
                r'Procedure\s*(?:Charges?)?\s*:?\s*(?:Rs\.?|₹)?\s*([\d,]+)',
                r'(?:Surgery|Operation)\s*(?:Charges?)?\s*:?\s*(?:Rs\.?|₹)?\s*([\d,]+)'
            ]
        }
        
        for field, patterns in amount_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    amount_str = match.group(1).replace(',', '')
                    try:
                        result[field] = float(amount_str)
                    except ValueError:
                        pass
                    break
        
        # Extract total
        total_patterns = [
            r'(?:Total|Grand\s+Total|Net\s+Amount)\s*:?\s*(?:Rs\.?|₹)?\s*([\d,]+)',
            r'(?:Rs\.?|₹)\s*([\d,]+)\s*(?:/-|only)?$'
        ]
        for pattern in total_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    result["total_amount"] = float(amount_str)
                except ValueError:
                    pass
                break
        
        # Extract line items (amount patterns in lines)
        for line in lines:
            amount_match = re.search(r'(.+?)\s+(?:Rs\.?|₹)?\s*([\d,]+(?:\.\d{2})?)\s*$', line)
            if amount_match:
                item_name = amount_match.group(1).strip()
                try:
                    amount = float(amount_match.group(2).replace(',', ''))
                    if amount > 0 and len(item_name) > 2:
                        result["line_items"].append({
                            "description": item_name,
                            "amount": amount
                        })
                except ValueError:
                    pass
        
        # Calculate total if not found
        if result["total_amount"] == 0:
            result["total_amount"] = (
                result["consultation_fee"] + 
                result["diagnostic_tests"] + 
                result["medicines"] + 
                result["procedures"]
            )
        
        return result
    
    def process_document(self, file_path: str, doc_type: str = "auto") -> Dict[str, Any]:
        """
        Process a document file and extract structured data.
        
        Args:
            file_path: Path to document file
            doc_type: 'prescription', 'bill', or 'auto' (detect automatically)
            
        Returns:
            Structured document data
        """
        # Extract text from file
        extraction_result = self.processor.process_file(file_path)
        
        if not extraction_result.get("success"):
            return extraction_result
        
        text = extraction_result.get("text", "")
        
        # Auto-detect document type
        if doc_type == "auto":
            if any(word in text.lower() for word in ['prescription', 'rx', 'diagnosis', 'medicine']):
                doc_type = "prescription"
            elif any(word in text.lower() for word in ['bill', 'invoice', 'receipt', 'total']):
                doc_type = "bill"
            else:
                doc_type = "unknown"
        
        # Parse based on type
        if doc_type == "prescription":
            parsed = self.parse_prescription(text)
        elif doc_type == "bill":
            parsed = self.parse_bill(text)
        else:
            parsed = {"raw_text": text, "type": "unknown"}
        
        parsed["extraction_method"] = extraction_result.get("method")
        parsed["success"] = True
        
        return parsed


# Singleton instance
_document_parser = None

def get_document_parser() -> MedicalDocumentParser:
    """Get or create document parser instance."""
    global _document_parser
    if _document_parser is None:
        _document_parser = MedicalDocumentParser()
    return _document_parser


def extract_from_file(file_path: str, doc_type: str = "auto") -> Dict[str, Any]:
    """
    Convenience function to extract data from a document file.
    
    Args:
        file_path: Path to document
        doc_type: Document type
        
    Returns:
        Extracted and parsed data
    """
    parser = get_document_parser()
    return parser.process_document(file_path, doc_type)


def extract_from_bytes(file_bytes: bytes, file_type: str, doc_type: str = "auto") -> Dict[str, Any]:
    """
    Extract data from document bytes.
    
    Args:
        file_bytes: Document content as bytes
        file_type: File extension (pdf, jpg, png)
        doc_type: Document type (prescription, bill, auto)
        
    Returns:
        Extracted and parsed data
    """
    parser = get_document_parser()
    
    # First extract text
    extraction = parser.processor.process_bytes(file_bytes, file_type)
    
    if not extraction.get("success"):
        return extraction
    
    text = extraction.get("text", "")
    
    # Parse based on type
    if doc_type == "prescription" or (doc_type == "auto" and 
        any(word in text.lower() for word in ['prescription', 'rx', 'diagnosis'])):
        return parser.parse_prescription(text)
    elif doc_type == "bill" or (doc_type == "auto" and 
        any(word in text.lower() for word in ['bill', 'invoice', 'total'])):
        return parser.parse_bill(text)
    else:
        return {"success": True, "raw_text": text, "type": "unknown"}
