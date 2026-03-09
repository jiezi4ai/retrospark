import pytest
from retrospark.privacy.anonymizer import anonymize_path
from retrospark.privacy.secrets import redact_text

def test_anonymizer_paths():
    # Use the underlying function to test logic independent of runtime `~` expansion
    original_path = "/Users/secretuser/project/file.txt"
    scrubbed = anonymize_path(original_path, "secretuser", "user_hash_123", "/Users/secretuser")
    
    assert "secretuser" not in scrubbed
    assert "user_hash_123" in scrubbed

def test_secrets_redact_api_keys():
    # Needs to be > 20 chars for Anthropic keys `sk-ant-[A-Za-z0-9_-]{20,}`
    test_text = "Here is my secret token: sk-ant-api1234567890abcdef12345 You should not see this."
    redacted, found = redact_text(test_text)
    
    assert found > 0
    assert "sk-ant-" not in redacted
    assert "<REDACTED:" not in redacted # Actually, DataClaw uses [REDACTED]
    assert "[REDACTED]" in redacted

def test_high_entropy_scan():
    # Long random string that looks like a base64 token
    secret = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ"
    text = f"My token is '{secret}'"
    
    redacted, found = redact_text(text)
    
    assert found > 0
    assert secret not in redacted
    assert "[REDACTED]" in redacted

def test_no_entropy_scan():
    text = "This is just a regular sentence with some code like var x = 10;"
    redacted, found = redact_text(text)
    assert found == 0
    assert redacted == text
