import ipaddress
import socket
from urllib.parse import urlparse

from rest_framework import serializers

ALLOWED_SCHEMES = {"http", "https"}

# Hostnames that resolve to the machine itself or common internal aliases,
# blocked outright even before DNS resolution.
BLOCKED_HOSTNAMES = {"localhost"}


def _is_blocked_ip(ip_str):
    ip = ipaddress.ip_address(ip_str)
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def validate_webhook_url(url):
    """
    Rejects webhook URLs that would let a user make this server send
    requests to itself or to internal/private network destinations
    (localhost, RFC1918 ranges, link-local/cloud-metadata addresses like
    169.254.169.254, etc). Without this, the webhook dispatch feature is an
    SSRF primitive: any user can register a URL and the server will POST to
    it from inside our own network on their behalf.
    """

    parsed = urlparse(url)

    if parsed.scheme not in ALLOWED_SCHEMES:
        raise serializers.ValidationError(
            "Webhook URL must use http or https"
        )

    hostname = parsed.hostname

    if not hostname:
        raise serializers.ValidationError("Webhook URL must include a host")

    if hostname.lower() in BLOCKED_HOSTNAMES:
        raise serializers.ValidationError(
            "Webhook URL may not point to a local or internal address"
        )

    try:
        resolved = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise serializers.ValidationError("Webhook URL host could not be resolved")

    for family, _, _, _, sockaddr in resolved:
        ip_str = sockaddr[0]
        try:
            if _is_blocked_ip(ip_str):
                raise serializers.ValidationError(
                    "Webhook URL may not point to a local or internal address"
                )
        except ValueError:
            raise serializers.ValidationError("Webhook URL host could not be validated")

    return url