"""Deployment-owned certificate credentials for Microsoft delegated OAuth."""
from __future__ import annotations

import base64
import json
import uuid
from datetime import datetime, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def certificate_material(credentials: dict, now: int):
    """Validate a PEM certificate and matching unencrypted RSA private key."""
    try:
        certificate = x509.load_pem_x509_certificate(credentials["certificate"].encode())
        key = serialization.load_pem_private_key(credentials["private_key"].encode(), password=None)
        if not isinstance(key, rsa.RSAPrivateKey) or key.key_size < 2048:
            raise ValueError("RSA key must contain at least 2048 bits")
        public = certificate.public_key()
        if not isinstance(public, rsa.RSAPublicKey) or public.public_numbers() != key.public_key().public_numbers():
            raise ValueError("certificate and key do not match")
        instant = datetime.fromtimestamp(now, timezone.utc)
        if not certificate.not_valid_before_utc <= instant < certificate.not_valid_after_utc:
            raise ValueError("certificate is outside its validity period")
        return certificate, key
    except (ValueError, TypeError, KeyError, AttributeError) as error:
        # Do not include PEM material or library errors in user-facing output.
        raise ValueError("Microsoft OAuth certificate credentials are invalid") from error


def client_authentication(credentials: dict, token_url: str, now: int) -> dict:
    """Create a fresh PS256 assertion; never fall back from an invalid certificate."""
    if not any(field in credentials for field in ("certificate", "private_key")):
        return {"client_secret": credentials["client_secret"]}
    certificate, key = certificate_material(credentials, now)
    header = {"alg": "PS256", "typ": "JWT", "x5t#S256": _base64url(certificate.fingerprint(hashes.SHA256()))}
    claims = {
        "aud": token_url, "iss": credentials["client_id"], "sub": credentials["client_id"],
        "jti": str(uuid.uuid4()), "iat": now, "nbf": now,
        "exp": min(now + 300, int(certificate.not_valid_after_utc.timestamp())),
    }
    unsigned = ".".join(_base64url(json.dumps(part, separators=(",", ":")).encode()) for part in (header, claims))
    signature = key.sign(unsigned.encode("ascii"), padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32), hashes.SHA256())
    return {
        "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
        "client_assertion": unsigned + "." + _base64url(signature),
    }
