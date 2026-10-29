import ipaddress
import socket
from urllib.parse import urlparse
import tldextract

def is_public_ip(value: str) -> bool:
    try:
        ip = ipaddress.ip_address(value)
        return (
            ip.is_global
            and not ip.is_private
            and not ip.is_loopback
            and not ip.is_link_local
            and not ip.is_multicast
            and not ip.is_reserved
        )
    except ValueError:
        return False

def normalize_domain(value: str) -> str:
    candidate = value.strip()
    if not candidate:
        raise ValueError("Domain cannot be empty.")
    if "://" not in candidate:
        candidate = "https://" + candidate
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Provide a valid http(s) domain.")
    host = parsed.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith(".localhost"):
        raise ValueError("Localhost is not a valid prospect domain.")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address and not is_public_ip(str(address)):
        raise ValueError("Non-public IP addresses are not allowed.")
    if "." not in host and address is None:
        raise ValueError("A fully qualified domain is required.")
    extracted = tldextract.extract(host)
    if not extracted.domain or not extracted.suffix:
        raise ValueError("A registrable domain is required.")
    return f"{extracted.domain}.{extracted.suffix}".lower()

def validate_public_url(url: str) -> str:
    """
    Validates that a URL uses http/https and does not resolve to private,
    loopback, link-local, or cloud metadata IP addresses (SSRF protection).
    """
    parsed = urlparse(str(url).strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("URL must have http or https scheme and a valid hostname.")
    host = parsed.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith(".localhost"):
        raise ValueError("Localhost is not allowed.")

    # Check direct IP address literal
    try:
        direct_ip = ipaddress.ip_address(host)
        if not is_public_ip(str(direct_ip)):
            raise ValueError(f"Direct IP {host} is private or non-public.")
        return str(url)
    except ValueError as exc:
        if "private or non-public" in str(exc):
            raise

    # Resolve hostname via DNS
    try:
        addr_info = socket.getaddrinfo(host, None)
        for _, _, _, _, sockaddr in addr_info:
            ip_str = sockaddr[0]
            if not is_public_ip(ip_str):
                raise ValueError(f"Host {host} resolves to non-public IP: {ip_str}")
    except socket.gaierror as exc:
        raise ValueError(f"DNS resolution failed for {host}") from exc

    return str(url)
