"""Small, local-only TLS certificate helper for the phone server."""

from __future__ import annotations

import datetime as dt
import socket
from ipaddress import ip_address
from pathlib import Path


def certificate_paths(data_dir: Path) -> tuple[Path, Path]:
    tls_dir = data_dir / ".tls"
    return tls_dir / "touchkeys-phone.crt", tls_dir / "touchkeys-phone.key"


def ensure_certificate(data_dir: Path, lan_ip: str) -> tuple[Path, Path]:
    """Create a self-signed certificate containing the current LAN IP.

    The certificate is deliberately local and short-lived. Users who want
    Safari/Chrome sensor access should trust this certificate, or replace it
    with a certificate issued by a locally trusted CA (for example mkcert).
    """
    cert_path, key_path = certificate_paths(data_dir)
    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
    except ImportError as exc:  # pragma: no cover - dependency install issue
        raise RuntimeError("TLS support requires the 'cryptography' package") from exc

    tls_dir = cert_path.parent
    tls_dir.mkdir(parents=True, exist_ok=True)
    names = {"localhost", socket.gethostname(), "touchkeys.local", lan_ip}

    if cert_path.exists() and key_path.exists():
        try:
            cert = x509.load_pem_x509_certificate(cert_path.read_bytes())
            san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
            if lan_ip in {str(item.value) for item in san if hasattr(item, "value")}:  # type: ignore[attr-defined]
                if cert.not_valid_after_utc > dt.datetime.now(dt.timezone.utc):
                    return cert_path, key_path
        except Exception:
            pass

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "TouchKeys local phone server")])
    san_names = []
    for name in sorted(names):
        try:
            san_names.append(x509.IPAddress(ip_address(name)))
        except ValueError:
            san_names.append(x509.DNSName(name))
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=1))
        .not_valid_after(dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=365))
        .add_extension(x509.SubjectAlternativeName(san_names), critical=False)
        .sign(key, hashes.SHA256())
    )
    key_path.write_bytes(key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ))
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    return cert_path, key_path
