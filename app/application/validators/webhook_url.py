"""SSRF validation for webhook target URLs.

Rejects loopback, link-local, and private RFC1918 addresses so tenants cannot
trigger server-side requests to internal services.
"""

import ipaddress
from urllib.parse import urlparse


# Hostnames that resolve to loopback or are commonly used for internal services
_UNSAFE_HOSTNAMES = frozenset(
    {"localhost", "ip6-localhost", "ip6-loopback", "localhost.localdomain"}
)


def validate_webhook_target_url(url: str) -> None:
    """Raise ValueError if the URL is unsafe for webhook delivery (SSRF).

    Allows only http/https. Rejects:
    - Non-http(s) schemes
    - Loopback (127.0.0.0/8, ::1)
    - Link-local (169.254.0.0/16, fe80::/10)
    - Private RFC1918 (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
    - Hostnames: localhost, *.localhost, *.local, and similar
    """
    if not url or not url.strip():
        raise ValueError("target_url is required")
    parsed = urlparse(url.strip())
    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        raise ValueError(
            "target_url must use http or https scheme"
        )
    host = parsed.hostname
    if not host:
        raise ValueError("target_url must have a valid host")
    host_lower = host.lower()
    if host_lower in _UNSAFE_HOSTNAMES:
        raise ValueError(
            "target_url host is not allowed (loopback or reserved)"
        )
    if host_lower.endswith(".localhost") or host_lower.endswith(".local"):
        raise ValueError(
            "target_url host is not allowed (reserved TLD)"
        )
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        # Host is a hostname, not an IP; already checked blocklist
        return
    if addr.is_loopback:
        raise ValueError(
            "target_url must not be loopback (127.x, ::1)"
        )
    if addr.is_link_local:
        raise ValueError(
            "target_url must not be link-local (169.254.x, fe80::)"
        )
    if addr.is_private:
        raise ValueError(
            "target_url must not be a private network (10.x, 172.16-31.x, 192.168.x)"
        )
