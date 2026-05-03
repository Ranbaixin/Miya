import re


def test_redaction():
    # Patterns for sensitive data that should be redacted
    SENSITIVE_PATTERNS = [
        # Passwords
        (
            r'(?i)(password|passwd|pwd)["\']?\s*[:=]\s*["\']?[^"\'\s,}]+',
            r'\1="[REDACTED]"',
        ),
        (r'(?i)"?(password|passwd|pwd)"?\s*:\s*"[^"]*"', r'"\1":"[REDACTED]"'),
        # API keys/tokens
        (
            r'(?i)(api[_\s]?key|token|auth[_\s]?key|access[_\s]?token|secret[_\s]?key)["\']?\s*[:=]\s*["\']?[^"\'\s,}]+',
            r'\1="[REDACTED]"',
        ),
        (
            r'(?i)"?(api[_\s]?key|token|auth[_\s]?key|access[_\s]?token|secret[_\s]?key)"?\s*:\s*"[^"]*"',
            r'"\1":"[REDACTED]"',
        ),
        # Personal data
        (
            r'(?i)(ssn|social[_\s]?security)["\']?\s*[:=]\s*["\']?[^"\'\s,}]+',
            r'\1="[REDACTED]"',
        ),
        (r'(?i)"?(ssn|social[_\s]?security)"?\s*:\s*"[^"]*"', r'"\1":"[REDACTED]"'),
        (
            r'(?i)(credit[_\s]?card|ccv|cvc)["\']?\s*[:=]\s*["\']?[^"\'\s,}]+',
            r'\1="[REDACTED]"',
        ),
        (r'(?i)"?(credit[_\s]?card|ccv|cvc)"?\s*:\s*"[^"]*"', r'"\1":"[REDACTED]"'),
        (r'(?i)(email|e-mail)["\']?\s*[:=]\s*["\']?[^"\'\s,}]+', r'\1="[REDACTED]"'),
        (r'(?i)"?(email|e-mail)"?\s*:\s*"[^"]*"', r'"\1":"[REDACTED]"'),
    ]

    text = '{"password": "secret123", "api_key": "sk-live-abc", "ssn": "123-45-6789", "email": "test@example.com"}'
    print(f"Original: {text}")

    redacted = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        redacted = re.sub(pattern, replacement, redacted)

    print(f"Redacted: {redacted}")

    # Check if redaction worked
    if '"password":"[REDACTED]"' in redacted and '"api_key":"[REDACTED]"' in redacted:
        print("SUCCESS: Sensitive data properly redacted")
    else:
        print("FAILURE: Sensitive data not properly redacted")


if __name__ == "__main__":
    test_redaction()
