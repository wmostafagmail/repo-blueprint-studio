import re

SECRET_REGEXES = [
    # Private Key blocks
    (r"-----BEGIN [A-Z\s]+ PRIVATE KEY-----\n[\s\S]+?\n-----END [A-Z\s]+ PRIVATE KEY-----", "[REDACTED_PRIVATE_KEY]"),
    # GitHub Tokens
    (r"\b(ghp|gho|ghu|ghs|ghr|github_pat)_[a-zA-Z0-9_]{36,255}\b", "[REDACTED_GITHUB_TOKEN]"),
    # Slack webhooks
    (r"https://hooks\.slack\.com/services/[A-Z0-9]+/[A-Z0-9]+/[a-zA-Z0-9]+", "[REDACTED_SLACK_WEBHOOK]"),
    # General Key-Value secrets
    (r"(?i)(\w*key|secret|password|passwd|pass|auth[-_]?token|token|client[-_]?secret|aws[-_]?secret|jwt|session[-_]?key|db[-_]?pass|db[-_]?password|database[-_]?password)\s*[:=]\s*['\"]([^'\"]{6,})['\"]", 
     lambda m: m.group(0).replace(m.group(2), "[REDACTED_SECRET]")),
    # Connection strings with password
    (r"(?i)([a-z0-9\+]+):\/\/([^:\s]+):([^@\s]+)@([^\s]+)", 
     lambda m: m.group(0).replace(m.group(3), "[REDACTED_PASSWORD]"))
]

def redact_secrets(text: str) -> str:
    """
    Scans text content and replaces any suspected secrets or passwords with a redaction placeholder.
    """
    if not text:
        return ""
    for pattern, replacement in SECRET_REGEXES:
        try:
            if callable(replacement):
                text = re.sub(pattern, replacement, text)
            else:
                text = re.sub(pattern, replacement, text)
        except Exception:
            pass
    return text
