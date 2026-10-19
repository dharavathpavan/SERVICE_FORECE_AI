import ipaddress
import socket
from urllib.parse import urlparse
from fastapi import HTTPException, status

# Denied IP networks (SSRF prevention)
BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),          # Private RFC1918
    ipaddress.ip_network("127.0.0.0/8"),         # Loopback
    ipaddress.ip_network("169.254.0.0/16"),       # Link-local / AWS metadata
    ipaddress.ip_network("172.16.0.0/12"),       # Private RFC1918
    ipaddress.ip_network("192.168.0.0/16"),      # Private RFC1918
    ipaddress.ip_network("224.0.0.0/4"),         # Multicast
    ipaddress.ip_network("240.0.0.0/4"),         # Reserved
    ipaddress.ip_network("::1/128"),             # IPv6 Loopback
    ipaddress.ip_network("fc00::/7"),            # IPv6 Unique Local
    ipaddress.ip_network("fe80::/10"),           # IPv6 Link-Local
]


def validate_url_safety(url: str) -> None:
    """
    Validates URL to protect against Server-Side Request Forgery (SSRF).
    Blocks access to internal services, localhost, link-local, and cloud metadata (169.254.169.254).
    """
    parsed = urlparse(url)
    if parsed.scheme not in ["http", "https"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid URL protocol '{parsed.scheme}'. Only http and https are permitted."
        )

    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL is missing a valid hostname."
        )

    # Resolve IP address
    try:
        addr_info = socket.getaddrinfo(hostname, None)
        ips = {info[4][0] for info in addr_info}
    except socket.gaierror:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to resolve hostname '{hostname}'."
        )

    for ip_str in ips:
        ip_obj = ipaddress.ip_address(ip_str)
        for net in BLOCKED_NETWORKS:
            if ip_obj in net:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Security violation: Outbound requests to private/internal network ({ip_str}) are strictly prohibited."
                )
