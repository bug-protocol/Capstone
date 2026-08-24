import re
from typing import Any

EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b')
PHONE_PATTERN = re.compile(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b')
SSN_PATTERN = re.compile(r'\b\d{3}-\d{2}-\d{4}\b|\b\d{9}\b')
MRN_PATTERN = re.compile(r'\b(?:MRN|mrn|Record\s*#?|Patient\s*ID|Case\s*#?)[:\s]*[A-Z0-9-]{4,15}\b', re.IGNORECASE)
DOB_PATTERN = re.compile(r'\b(?:DOB|Date of Birth|born on|Birth Date)[:\s]*(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}|[A-Za-z]+\s+\d{1,2},?\s+\d{4})\b', re.IGNORECASE)
ZIP_PATTERN = re.compile(r'\b(?:Zip|Zipcode|Postal Code)[:\s]*\d{5}(?:-\d{4})?\b', re.IGNORECASE)
STREET_PATTERN = re.compile(r'\b\d+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Way|Court|Ct)\b', re.IGNORECASE)

NAME_PATTERNS = [
    re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+),\s*(?:a\s+)?(?:\d{1,3}-year-old|\d{1,3}\s*yo|\d{1,3}\s*years?\s*old)\b'),
    re.compile(r'\b(?:Patient|patient|pt|Subject|subject|Client|client)(?:\s+(?:name|is|named))?[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'),
    re.compile(r'\b(?:Dr\.|Doctor|Nurse|Physician|Pharmacist|Reporter|Reviewer|Mr\.|Mrs\.|Ms\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b'),
    re.compile(r'\b(?:My name is|I am|Name is|Name:)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', re.IGNORECASE),
    re.compile(r'\b(?:reported by|evaluated by|referred by|admitted by|signed by)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', re.IGNORECASE),
]


def redact_pii(text: str) -> str:
    if not text:
        return text

    sanitized = text
    sanitized = EMAIL_PATTERN.sub("[EMAIL_REDACTED]", sanitized)
    sanitized = PHONE_PATTERN.sub("[PHONE_REDACTED]", sanitized)
    sanitized = SSN_PATTERN.sub("[SSN_REDACTED]", sanitized)
    sanitized = MRN_PATTERN.sub("[MRN_REDACTED]", sanitized)
    sanitized = DOB_PATTERN.sub("[DOB_REDACTED]", sanitized)
    sanitized = STREET_PATTERN.sub("[ADDRESS_REDACTED]", sanitized)
    sanitized = ZIP_PATTERN.sub("[ZIP_REDACTED]", sanitized)

    for pattern in NAME_PATTERNS:
        sanitized = pattern.sub(
            lambda m: "[PATIENT_NAME_REDACTED]" + (", " + m.group(0).split(",", 1)[1].strip() if "," in m.group(0) else ""),
            sanitized
        )

    return sanitized


def sanitize_payload_for_logging(data: Any) -> Any:
    if isinstance(data, str):
        return redact_pii(data)
    elif isinstance(data, dict):
        return {k: sanitize_payload_for_logging(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_payload_for_logging(item) for item in data]
    return data
