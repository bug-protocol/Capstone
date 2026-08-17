import re
from typing import Any

EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b')
PHONE_PATTERN = re.compile(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b')
SSN_PATTERN = re.compile(r'\b\d{3}-\d{2}-\d{4}\b|\b\d{9}\b')
MRN_PATTERN = re.compile(r'\b(?:MRN|mrn|Record\s*#?)[:\s]*[A-Z0-9-]{5,12}\b', re.IGNORECASE)
DOB_PATTERN = re.compile(r'\b(?:DOB|Date of Birth|born on)[:\s]*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', re.IGNORECASE)

NAME_INDICATORS = [
    re.compile(r'\b(?:Patient|patient|pt|Subject|subject)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b'),
    re.compile(r'\b(?:Mr\.|Mrs\.|Ms\.|Dr\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b'),
    re.compile(r'\bName[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b', re.IGNORECASE),
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

    for pattern in NAME_INDICATORS:
        sanitized = pattern.sub("[PATIENT_NAME_REDACTED]", sanitized)

    return sanitized


def sanitize_payload_for_logging(data: Any) -> Any:
    if isinstance(data, str):
        return redact_pii(data)
    elif isinstance(data, dict):
        return {k: sanitize_payload_for_logging(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_payload_for_logging(item) for item in data]
    return data
