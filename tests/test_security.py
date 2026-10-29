import pytest

from app.security import is_public_ip, normalize_domain, validate_public_url


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
    "http://0.0.0.0:80/",
    "http://100.64.1.1/",
    "http://198.18.0.25/status",
    "http://[::1]:8080/",
    "http://[fe80::1]/",
    "ftp://example.com/file",
])
def test_validate_public_url_blocks_internal(url):
    with pytest.raises(ValueError):
        validate_public_url(url)

@pytest.mark.parametrize("ip,expected", [
    ("8.8.8.8", True),
    ("1.1.1.1", True),
    ("93.184.216.34", True),
    ("127.0.0.1", False),
    ("10.0.0.1", False),
    ("192.168.1.1", False),
    ("169.254.169.254", False),
    ("100.64.0.1", False),       # Carrier-Grade NAT
    ("100.127.255.254", False),   # Carrier-Grade NAT
    ("198.18.0.1", False),       # Benchmarking
    ("0.0.0.0", False),          # Unspecified
    ("255.255.255.255", False),  # Broadcast
    ("224.0.0.1", False),        # IPv4 Multicast
    ("::1", False),              # IPv6 Loopback
    ("::", False),               # IPv6 Unspecified
    ("fe80::1", False),          # IPv6 Link-Local
    ("fc00::1", False),          # IPv6 Unique Local
    ("ff02::1", False),          # IPv6 Multicast
    ("invalid-ip", False),
])
def test_is_public_ip_adversarial_matrix(ip, expected):
    assert is_public_ip(ip) is expected

def test_safe_fetch_url_blocks_redirect_to_metadata(monkeypatch):
    import anyio
    import httpx

    from app.security import safe_fetch_url

    class RedirectResponse:
        status_code = 302
        is_redirect = True
        headers = {"location": "http://169.254.169.254/latest/meta-data/"}
        url = "https://public-site.example/login"

    async def mock_get(self, url, **kwargs):
        return RedirectResponse()

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    async def run_test():
        async with httpx.AsyncClient() as client:
            with pytest.raises(ValueError, match="private or non-public"):
                await safe_fetch_url(client, "http://169.254.169.254/")

    anyio.run(run_test)

def test_safe_fetch_url_blocks_redirect_to_localhost(monkeypatch):
    import anyio
    import httpx

    from app.security import safe_fetch_url

    class RedirectResponse:
        status_code = 302
        is_redirect = True
        headers = {"location": "http://127.0.0.1:8000/internal"}
        url = "https://public-site.example/start"

    # Allow initial public-site.example, then mock client
    monkeypatch.setattr("app.security.validate_public_url", lambda u: u if "public-site" in u else validate_public_url(u))

    async def mock_get(self, url, **kwargs):
        return RedirectResponse()

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    async def run_test():
        async with httpx.AsyncClient() as client:
            with pytest.raises(ValueError, match="private or non-public"):
                await safe_fetch_url(client, "https://public-site.example/start")

    anyio.run(run_test)

def test_safe_fetch_url_detects_redirect_loop(monkeypatch):
    import anyio
    import httpx

    from app.security import safe_fetch_url

    class LoopingResponse:
        status_code = 301
        is_redirect = True
        headers = {"location": "https://public-site.example/loop"}
        url = "https://public-site.example/loop"

    monkeypatch.setattr("app.security.validate_public_url", lambda u: u)

    async def mock_get(self, url, **kwargs):
        return LoopingResponse()

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    async def run_test():
        async with httpx.AsyncClient() as client:
            with pytest.raises(ValueError, match="Exceeded maximum redirects"):
                await safe_fetch_url(client, "https://public-site.example/loop", max_redirects=3)

    anyio.run(run_test)


