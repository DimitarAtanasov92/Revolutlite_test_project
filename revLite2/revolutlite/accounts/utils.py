import pytesseract
import cv2
import re

def extract_text_fields(image_path):
    img = cv2.imread(image_path)
    text = pytesseract.image_to_string(img)

    name = re.search(r"Name[:\-]?\s*([A-Z ]+)", text)
    birth = re.search(r"(\d{2}/\d{2}/\d{4})", text)
    docnum = re.search(r"Document[:\-]?\s*(\w+)", text)
    issued = re.search(r"Issue[:\-]?\s*(\d{2}/\d{2}/\d{4})", text)

    return {
        'full_name': name.group(1).strip() if name else None,
        'birth_date': birth.group(1) if birth else None,
        'document_number': docnum.group(1) if docnum else None,
        'issue_date': issued.group(1) if issued else None
    }
