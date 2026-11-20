# backend/app/core/certificates.py
"""
ObserVault Mutual TLS (mTLS) & X.509 Certificate Management Engine.
Manages CA provisioning, collector client certificate issuance, expiration tracking,
revocation status, and TLS connection verification.
"""

import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding

CERTS_DIR = Path(__file__).resolve().parent.parent.parent / "certs"

class CertificateManager:
    """
    Manages cryptographic identity and mTLS lifecycle for ObserVault edge nodes.
    """
    def __init__(self, certs_dir: Optional[Path] = None):
        self.certs_dir = certs_dir or CERTS_DIR
        self.certs_dir.mkdir(parents=True, exist_ok=True)
        self.ca_key_path = self.certs_dir / "ca.key"
        self.ca_cert_path = self.certs_dir / "ca.crt"
        self._revoked_serials: set[int] = set()

    def init_ca(self, common_name: str = "ObserVault Root CA", validity_days: int = 3650) -> Tuple[str, str]:
        """
        Generates or loads the ObserVault Root Certificate Authority.
        """
        if self.ca_key_path.exists() and self.ca_cert_path.exists():
            return self.ca_cert_path.read_text(), self.ca_key_path.read_text()

        # Generate RSA 4096-bit CA key
        ca_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096
        )

        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "ObserVault Security"),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ])

        now = datetime.now(timezone.utc)
        ca_cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(ca_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now)
            .not_valid_after(now + timedelta(days=validity_days))
            .add_extension(
                x509.BasicConstraints(ca=True, path_length=None),
                critical=True
            )
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    content_commitment=False,
                    key_encipherment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=True,
                    crl_sign=True,
                    encipher_only=False,
                    decipher_only=False
                ),
                critical=True
            )
            .sign(ca_key, hashes.SHA256())
        )

        # Write to disk
        ca_key_pem = ca_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')

        ca_cert_pem = ca_cert.public_bytes(serialization.Encoding.PEM).decode('utf-8')

        self.ca_key_path.write_text(ca_key_pem)
        self.ca_cert_path.write_text(ca_cert_pem)

        return ca_cert_pem, ca_key_pem

    def issue_collector_certificate(
        self,
        collector_id: str,
        tenant_id: str,
        hostname: str,
        validity_days: int = 90
    ) -> Dict[str, Any]:
        """
        Issues an X.509 client certificate for an on-premises collector, signed by the CA.
        """
        self.init_ca()
        ca_key = serialization.load_pem_private_key(
            self.ca_key_path.read_bytes(),
            password=None
        )
        ca_cert = x509.load_pem_x509_certificate(self.ca_cert_path.read_bytes())

        # Generate Collector Private Key (RSA 2048)
        collector_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )

        subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, f"Tenant:{tenant_id}"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Edge Observability Node"),
            x509.NameAttribute(NameOID.COMMON_NAME, f"collector-{collector_id}"),
        ])

        now = datetime.now(timezone.utc)
        serial = x509.random_serial_number()

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(ca_cert.subject)
            .public_key(collector_key.public_key())
            .serial_number(serial)
            .not_valid_before(now)
            .not_valid_after(now + timedelta(days=validity_days))
            .add_extension(
                x509.BasicConstraints(ca=False, path_length=None),
                critical=True
            )
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_encipherment=True,
                    content_commitment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=False,
                    crl_sign=False,
                    encipher_only=False,
                    decipher_only=False
                ),
                critical=True
            )
            .add_extension(
                x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]),
                critical=True
            )
            .add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName(hostname),
                    x509.DNSName("localhost"),
                    x509.DNSName(f"collector-{collector_id}.observault.internal")
                ]),
                critical=False
            )
            .sign(ca_key, hashes.SHA256())
        )

        cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode('utf-8')
        key_pem = collector_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')

        return {
            "serial_number": str(serial),
            "certificate_pem": cert_pem,
            "private_key_pem": key_pem,
            "ca_certificate_pem": self.ca_cert_path.read_text(),
            "valid_from": now.isoformat(),
            "valid_until": (now + timedelta(days=validity_days)).isoformat(),
            "subject_cn": f"collector-{collector_id}",
            "tenant_id": tenant_id,
            "hostname": hostname
        }

    def verify_collector_certificate(self, cert_pem: str) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Validates a collector client certificate against the Root CA and revocation status.
        """
        try:
            cert = x509.load_pem_x509_certificate(cert_pem.encode('utf-8'))
            ca_cert = x509.load_pem_x509_certificate(self.ca_cert_path.read_bytes())
            
            # 1. Check revocation
            if cert.serial_number in self._revoked_serials:
                return False, "Certificate has been revoked by security administrator", None

            # 2. Check expiration window
            now = datetime.now(timezone.utc)
            if now < cert.not_valid_before_utc:
                return False, "Certificate is not yet valid", None
            if now > cert.not_valid_after_utc:
                return False, f"Certificate expired on {cert.not_valid_after_utc.isoformat()}", None

            # 3. Check signature validity against Root CA
            ca_public_key = ca_cert.public_key()
            ca_public_key.verify(
                cert.signature,
                cert.tbs_certificate_bytes,
                padding.PKCS1v15(),
                cert.signature_hash_algorithm
            )

            # Metadata extract
            common_name = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
            days_remaining = (cert.not_valid_after_utc - now).days

            metadata = {
                "serial_number": str(cert.serial_number),
                "common_name": common_name,
                "days_remaining": days_remaining,
                "not_valid_after": cert.not_valid_after_utc.isoformat(),
                "issuer": cert.issuer.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value,
                "is_expired": days_remaining < 0
            }

            return True, None, metadata

        except Exception as e:
            return False, f"Certificate verification failure: {str(e)}", None

    def revoke_certificate(self, serial_number: int):
        """Adds a certificate serial number to the revocation set."""
        self._revoked_serials.add(serial_number)

    def is_revoked(self, serial_number: int) -> bool:
        return serial_number in self._revoked_serials

cert_manager = CertificateManager()
