"""Bunny CDN signed-URL helper.

Generates expiring, token-authenticated URLs so raw file links
are never exposed to end users.

Algorithm (Basic Token Authentication — MD5):
    token = Base64URL( MD5( security_key + decoded_path + expiry ) )

The *decoded* path (with real spaces, not %20) must be used for hashing,
while the URL itself keeps the percent-encoded form.

Reference: https://docs.bunny.net/cdn/security/token-authentication/basic
"""

from __future__ import annotations

import hashlib
import base64
import time
from urllib.parse import urlparse, unquote


def sign_bunny_url(
    file_url: str,
    cdn_hostname: str,
    token_key: str,
    expiry_seconds: int = 14400,  # 4 hours default
) -> str:
    """Return a signed Bunny CDN URL with an expiration token.

    Parameters
    ----------
    file_url : str
        The raw CDN URL *or* just the path portion.
        If it starts with ``http`` the path is extracted automatically.
    cdn_hostname : str
        Full CDN origin, e.g. ``https://zrbot.b-cdn.net``.
    token_key : str
        The URL Token Authentication Key from the Bunny dashboard.
    expiry_seconds : int
        How long the link stays valid (default 4 h).

    Returns
    -------
    str
        ``https://<cdn>/path/to/file.mp4?token=<hash>&expires=<ts>``
    """
    # Extract path from full URL or use as-is
    if file_url.startswith(("http://", "https://")):
        parsed = urlparse(file_url)
        encoded_path = parsed.path
    else:
        encoded_path = file_url if file_url.startswith("/") else f"/{file_url}"

    # Bunny expects the *decoded* path in the hash
    decoded_path = unquote(encoded_path)
    expiry = int(time.time()) + expiry_seconds

    # Basic token auth: MD5
    hashable = f"{token_key}{decoded_path}{expiry}"
    raw_hash = hashlib.md5(hashable.encode("utf-8")).digest()
    token_b64 = base64.b64encode(raw_hash).decode("utf-8")
    # URL-safe Base64
    token_safe = token_b64.replace("+", "-").replace("/", "_").rstrip("=")

    # Build the signed URL (keep encoded path in the URL)
    cdn_hostname = cdn_hostname.rstrip("/")
    return f"{cdn_hostname}{encoded_path}?token={token_safe}&expires={expiry}"
