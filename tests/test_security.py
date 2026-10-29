import pytest
from app.security import normalize_domain, is_public_ip, validate_public_url

def test_normalize_domain():
    assert normalize_domain("https://www.Example.com/path") == "example.com"

@pytest.mark.parametrize("value", [
    "http://127.0.0.1",
    "http://localhost",
    "http://192.168.1.2",
    "http://10.0.0.1",
    "http://169.254.169.254"
])
def test_reject_private_hosts(value):
    with pytest.raises(ValueError):
        normalize_domain(value)

def test_invalid_domain():
    with pytest.raises(ValueError):
        normalize_domain("not a domain")

def test_is_public_ip():
    assert is_public_ip("8.8.8.8") is True
    assert is_public_ip("127.0.0.1") is False
    assert is_public_ip("10.0.0.1") is False
    assert is_public_ip("192.168.1.1") is False
    assert is_public_ip("169.254.169.254") is False
    assert is_public_ip("invalid-ip") is False

@pytest.mark.parametrize("url", [
    "http://localhost:8080/secret",
    "http://127.0.0.1/admin",
    "http://192.168.1.5:8000/",
    "http://169.254.169.254/latest/meta-data/",
    "ftp://example.com/file"
])
def test_validate_public_url_blocks_internal(url):
    with pytest.raises(ValueError):
        validate_public_url(url)
