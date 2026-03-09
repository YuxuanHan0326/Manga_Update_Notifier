from __future__ import annotations

import ipaddress
import logging

import httpx
from fastapi import Request

from ..config import settings

log = logging.getLogger(__name__)


def extract_client_ip(request: Request) -> str | None:
    # Reverse proxies may append chain in x-forwarded-for; first hop is original client.
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        candidate = forwarded.split(",")[0].strip()
        if candidate:
            return candidate

    real_ip = request.headers.get("x-real-ip", "").strip()
    if real_ip:
        return real_ip

    if request.client and request.client.host:
        return request.client.host
    return None


def _is_public_ip(ip_raw: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip_raw)
    except ValueError:
        return False
    return not (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
    )


def _parse_timezone(payload: dict) -> str | None:
    timezone = payload.get("timezone")
    if isinstance(timezone, str):
        tz = timezone.strip()
        if tz:
            return tz
    return None


def _lookup_timezone(url: str, ip_raw: str | None) -> str | None:
    try:
        response = httpx.get(url, timeout=settings.ip_timezone_timeout_sec)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:  # noqa: BLE001
        log.warning("timezone lookup failed for ip=%s url=%s: %s", ip_raw, url, exc)
        return None
    return _parse_timezone(payload)


def detect_timezone_from_ip(ip_raw: str | None) -> str | None:
    if ip_raw and _is_public_ip(ip_raw):
        url = settings.ip_timezone_api_url_template.format(ip=ip_raw)
        timezone = _lookup_timezone(url, ip_raw)
        if timezone:
            return timezone

    # For private/LAN IP or failed public-IP lookup, fall back to provider "self" endpoint
    # that detects timezone from service outbound source address.
    if settings.ip_timezone_self_api_url:
        return _lookup_timezone(settings.ip_timezone_self_api_url, ip_raw)
    return None
