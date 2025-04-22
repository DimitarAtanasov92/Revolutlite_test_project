import pytesseract
import re
import cv2
import json
import os
from deepface import DeepFace

# Set tesseract path if needed (adjust for deployment later)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def extract_text_fields(image_path):
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    text = pytesseract.image_to_string(gray)

    name = re.search(r"Name[:\-]?\s*([A-Z][A-Z\s]+)", text, re.IGNORECASE)
    birth = re.search(r"(Date of birth|DOB)[:\-]?\s*(\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4})", text, re.IGNORECASE)
    docnum = re.search(r"(ID No)[:\-]?\s*(\w+)", text, re.IGNORECASE)
    issued = re.search(r"(Date of issue|Issue)[:\-]?\s*(\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4})", text, re.IGNORECASE)

    return {
        'full_name': name.group(1).strip() if name else None,
        'birth_date': birth.group(2) if birth else None,
        'document_number': docnum.group(2) if docnum else None,
        'issue_date': issued.group(2) if issued else None
    }


def save_to_json(data, output_path="extracted_data.json"):
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
