"""
platform/csr_generator.py
Phase 2 - CSR Generation and Management
Generates Certificate Signing Requests using the cryptography library.
All private keys are handled in-memory and written only to the csr/ directory.
Private keys are never logged.
"""

import os
import json
import datetime
from pathlib import Path
from typing import List, Optional

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509 import DNSName

from platform.logger import get_logger

logger = get_logger(__name__)


class CSRGenerator:
    """
    Generates CSR and private key for a given domain.
    Output files are written to the csr/ directory (gitignored).
    """

    def __init__(self, output_dir: str = "csr"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self,
                 common_name: str,
                 san_list: Optional[List[str]] = None,
                 key_size: int = 2048,
                 country: str = "US",
                 state: str = "",
                 locality: str = "",
                 organization: str = "",
                 org_unit: str = "") -> dict:
        """
        Generate a CSR and private key.
        Returns a dict with paths to the generated files.
        """
        logger.info(f"Generating CSR for CN: {common_name}")
        if san_list:
            logger.info(f"SANs: {san_list}")

        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
        )

        # Build subject
        name_attrs = [x509.NameAttribute(NameOID.COMMON_NAME, common_name)]
        if country:      name_attrs.append(x509.NameAttribute(NameOID.COUNTRY_NAME, country))
        if state:        name_attrs.append(x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, state))
        if locality:     name_attrs.append(x509.NameAttribute(NameOID.LOCALITY_NAME, locality))
        if organization: name_attrs.append(x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization))
        if org_unit:     name_attrs.append(x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, org_unit))
        subject = x509.Name(name_attrs)

        # Build CSR
        csr_builder = x509.CertificateSigningRequestBuilder().subject_name(subject)

        # Add SANs
        dns_names = [DNSName(common_name)]
        if san_list:
            for san in san_list:
                san = san.strip()
                if san and san != common_name:
                    dns_names.append(DNSName(san))

        csr_builder = csr_builder.add_extension(
            x509.SubjectAlternativeName(dns_names),
            critical=False
        )

        # Sign CSR
        csr = csr_builder.sign(private_key, hashes.SHA256())

        # Write files
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = common_name.replace("*", "wildcard").replace(".", "_")
        csr_path = self.output_dir / f"{safe_name}_{timestamp}.csr"
        key_path = self.output_dir / f"{safe_name}_{timestamp}.key"

        # Write CSR (PEM)
        csr_path.write_bytes(csr.public_bytes(serialization.Encoding.PEM))
        logger.info(f"CSR written: {csr_path}")

        # Write private key (PEM, no encryption)
        key_path.write_bytes(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            )
        )
        logger.info("Private key written: [PATH MASKED FOR SECURITY]")

        result = {
            "common_name": common_name,
            "san_list": san_list or [],
            "csr_path": str(csr_path),
            "key_path": str(key_path),
            "key_size": key_size,
            "generated_at": timestamp
        }

        logger.info(f"CSR generation complete for {common_name}")
        return result

    def validate_csr(self, csr_path: str) -> dict:
        """
        Validate a CSR file and return its details.
        """
        from cryptography.hazmat.primitives.serialization import load_pem_private_key
        csr_bytes = Path(csr_path).read_bytes()
        csr = x509.load_pem_x509_csr(csr_bytes)
        cn = csr.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        cn_value = cn[0].value if cn else "unknown"
        try:
            san_ext = csr.extensions.get_extension_for_class(x509.SubjectAlternativeName)
            sans = [str(name.value) for name in san_ext.value]
        except Exception:
            sans = []
        is_valid = csr.is_signature_valid
        result = {
            "common_name": cn_value,
            "sans": sans,
            "signature_valid": is_valid,
            "csr_path": csr_path
        }
        logger.info(f"CSR validation: CN={cn_value} SANs={sans} Valid={is_valid}")
        return result
