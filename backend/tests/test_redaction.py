from backend.app.services.redaction_service import redact_secrets

def test_github_token_redaction():
    text = "Here is my token: ghp_abc123XYZabc123XYZabc123XYZabc123XYZab"
    redacted = redact_secrets(text)
    assert "[REDACTED_GITHUB_TOKEN]" in redacted
    assert "ghp_" not in redacted

def test_api_key_redaction():
    text = 'openai_key = "sk-proj-abc123xyz123abc123xyz123"'
    redacted = redact_secrets(text)
    assert "[REDACTED_SECRET]" in redacted
    assert "sk-proj" not in redacted

def test_connection_string_redaction():
    text = "postgres://admin:super_secret_password@localhost:5432/db"
    redacted = redact_secrets(text)
    assert "[REDACTED_PASSWORD]" in redacted
    assert "super_secret_password" not in redacted

def test_private_key_redaction():
    text = """Some text
-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEA0yGz...
...
-----END RSA PRIVATE KEY-----
Footer text"""
    redacted = redact_secrets(text)
    assert "[REDACTED_PRIVATE_KEY]" in redacted
    assert "MIIEowIBAAKCAQEA0yGz" not in redacted
