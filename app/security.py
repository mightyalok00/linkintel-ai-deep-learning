import ipaddress
import socket
from urllib.parse import urlparse

import httpx
import tldextract

RESTRICTED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),    # Carrier-Grade NAT (RFC 6598)
    ipaddress.ip_network("127.0.0.0/8"),      # Loopback
    ipaddress.ip_network("169.254.0.0/16"),   # Link-Local & Cloud Metadata
    ipaddress.ip_network("172.16.0.0/12"),    # Private
    ipaddress.ip_network("192.0.0.0/24"),     # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),     # TEST-NET-1
    ipaddress.ip_network("192.168.0.0/16"),   # Private
    ipaddress.ip_network("198.18.0.0/15"),    # Benchmarking
    ipaddress.ip_network("198.51.100.0/24"),  # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),   # TEST-NET-3
    ipaddress.ip_network("224.0.0.0/4"),      # Multicast
    ipaddress.ip_network("240.0.0.0/4"),      # Reserved
    ipaddress.ip_network("255.255.255.255/32"),
    # IPv6
    ipaddress.ip_network("::/128"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),         # Unique Local (ULA)
    ipaddress.ip_network("fe80::/10"),        # Link-Local
    ipaddress.ip_network("ff00::/8"),         # Multicast
    ipaddress.ip_network("2001:db8::/32"),    # Documentation
]

def is_public_ip(value: str) -> bool:
    try:
        ip = ipaddress.ip_address(value)
        if (
            not ip.is_global
            or ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            return False
        for net in RESTRICTED_NETWORKS:
            if ip in net:
                return False
        return True
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
    loopback, link-local, carrier-grade NAT, or cloud metadata IP addresses (SSRF protection).
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

async def safe_fetch_url(
    client: httpx.AsyncClient,
    url: str,
    max_redirects: int = 5,
    **kwargs
) -> httpx.Response:
    """
    Safely fetches an outbound URL with multi-hop SSRF validation.
    Validates each redirect hop against public IP rules BEFORE connecting.
    Blocks DNS rebinding, internal cloud metadata (169.254.169.254),
    localhost, carrier-grade NAT, and private network addresses at every stage.
    """
    current_url = str(url).strip()
    for hop in range(max_redirects + 1):
        validate_public_url(current_url)
        response = await client.get(current_url, follow_redirects=False, **kwargs)
        if response.is_redirect and "location" in response.headers:
            if hop >= max_redirects:
                raise ValueError(f"Exceeded maximum redirects ({max_redirects}) for URL: {url}")
            location = response.headers["location"]
            redirect_url = str(httpx.URL(current_url).join(location))
            # Validate target of redirect BEFORE sending next request
            validate_public_url(redirect_url)
            current_url = redirect_url
        else:
            return response
    return response

