import ipaddress
import socket
from urllib.parse import urlparse

from rest_framework import serializers
import hashlib
import hmac

from django.conf import settings

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

def validate_mercadopago_signature(request, data_id):
    """
    Valida el header x-signature que manda Mercado Pago para confirmar que
    el webhook realmente viene de ellos. Sin esto, cualquiera puede pegarle
    a este endpoint con un payment_id ajeno y forzar una llamada real a la
    API de MP (costo + superficie de DoS), aunque no pueda falsificar el
    resultado en sí (eso ya lo protege el fetch a la API real).
    Doc: https://www.mercadopago.com.ar/developers/es/docs/checkout-api/webhooks
    """
    secret = getattr(settings, "MERCADO_PAGO_WEBHOOK_SECRET", "")

    if not secret:
        print(
            "[MP WEBHOOK] WARNING: MERCADO_PAGO_WEBHOOK_SECRET no configurado, "
            "se está aceptando el webhook SIN validar firma",
            flush=True,
        )
        return True

    signature_header = request.headers.get("x-signature", "")
    request_id = request.headers.get("x-request-id", "")

    if not signature_header:
        return False

    try:
        parts = dict(
            item.strip().split("=", 1)
            for item in signature_header.split(",")
            if "=" in item
        )
    except ValueError:
        return False

    ts = parts.get("ts")
    received_hash = parts.get("v1")

    if not ts or not received_hash:
        return False

    manifest = f"id:{data_id};request-id:{request_id};ts:{ts};"

    expected_hash = hmac.new(
        secret.encode("utf-8"),
        manifest.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected_hash, received_hash)