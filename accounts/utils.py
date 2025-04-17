import platform

if platform.system() != 'Windows':
    import fcntl

import pytesseract
import cv2
import re

def extract_text_fields(image_path):
    img = cv2.imread(image_path)
    pytesseract.image_to_string(img, lang='eng+bul')
    # Convert to grayscale and threshold (OCR friendly)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

    # OCR
    text = pytesseract.image_to_string(gray)

    # Debug: print extracted text
    print("OCR TEXT:\n", text)

    # Regex search
    name = re.search(r"Name[:\-]?\s*([A-Z][A-Z\s]+)", text, re.IGNORECASE)
    birth = re.search(r"(Date of birth|DOB)[:\-]?\s*(\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4})", text, re.IGNORECASE)
    docnum = re.search(r"(Ne Ha aonymenralBocumert muniber|ID No)[:\-]?\s*(\w+)", text, re.IGNORECASE)
    issued = re.search(r"(Date of issue|Issue)[:\-]?\s*(\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4})", text, re.IGNORECASE)

    extracted_data = {
        'full_name': name.group(1).strip() if name else None,
        'birth_date': birth.group(2) if birth else None,
        'document_number': docnum.group(2) if docnum else None,
        'issue_date': issued.group(2) if issued else None
    }

    return extracted_data
