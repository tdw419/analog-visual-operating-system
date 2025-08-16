import json
import base64
import os
from datetime import datetime, timezone
from typing import Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, ed25519
from cryptography.hazmat.primitives.serialization import (
    load_pem_public_key,
    load_pem_private_key,
    load_der_public_key,
)


class TrustAnchor:
    """
    Manages cryptographic operations, including signing, verification,
    and TPM-based key attestation.

    In a production environment, the keys managed by this class should be
    handled with extreme care. Private keys should be stored in a secure
    enclave or HSM. A robust key rotation policy should be in place for
    all keys (e.g., rotating developer keys every 90 days). The TPM root
    public key forms the root of trust for developer key attestation and
    must be distributed securely.
    """

    def __init__(
        self,
        root_pub_pem_path: Optional[str] = None,
        dev_priv_pem_path: Optional[str] = None,
        dev_pub_pem_path: Optional[str] = None,
    ):
        """
        Initializes the TrustAnchor for signing or verification.

        Note: This class assumes key files are provided on the filesystem.
        In a production system, this should be integrated with a secure key
        management service (e.g., HashiCorp Vault, AWS KMS).

        Args:
            root_pub_pem_path: Path to the PEM-encoded TPM root public key (ECDSA).
            dev_priv_pem_path: Path to the PEM-encoded developer private key (Ed25519) for signing.
            dev_pub_pem_path: Path to the PEM-encoded developer public key (Ed25519) for verification.
        """
        self.root_pub_key: Optional[ec.EllipticCurvePublicKey] = None
        self.dev_priv_key: Optional[ed25519.Ed25519PrivateKey] = None
        self.dev_pub_key: Optional[ed25519.Ed25519PublicKey] = None

        if root_pub_pem_path and os.path.exists(root_pub_pem_path):
            with open(root_pub_pem_path, "rb") as f:
                self.root_pub_key = load_pem_public_key(f.read())

        if dev_priv_pem_path and os.path.exists(dev_priv_pem_path):
            with open(dev_priv_pem_path, "rb") as f:
                self.dev_priv_key = load_pem_private_key(f.read(), password=None)
                self.dev_pub_key = self.dev_priv_key.public_key()
        elif dev_pub_pem_path and os.path.exists(dev_pub_pem_path):
            with open(dev_pub_pem_path, "rb") as f:
                self.dev_pub_key = load_pem_public_key(f.read())

    def sign_digest(self, digest: bytes) -> bytes:
        """Signs a pre-computed digest using the developer's private key."""
        if not self.dev_priv_key:
            raise ValueError("Developer private key is not loaded.")
        return self.dev_priv_key.sign(digest)

    def verify_signature(
        self,
        signature: bytes,
        digest: bytes,
        public_key: ed25519.Ed25519PublicKey,
    ) -> bool:
        """Verifies an Ed25519 signature against a digest."""
        try:
            public_key.verify(signature, digest)
            return True
        except InvalidSignature:
            return False

    def verify_key_grant(
        self, grant_path: str, grant_sig_path: str
    ) -> Optional[ed25519.Ed25519PublicKey]:
        """
        Verifies a key grant signature against the TPM root public key and
        checks its validity.

        Args:
            grant_path: Path to the key grant JSON file.
            grant_sig_path: Path to the signature file for the key grant.

        Returns:
            The attested developer public key (Ed25519) if valid, otherwise None.
        """
        if not self.root_pub_key:
            return None  # Cannot verify without a root key

        with open(grant_path, "r") as f:
            grant = json.load(f)
        with open(grant_sig_path, "rb") as f:
            signature = f.read()

        # The signature is over the canonical JSON representation
        grant_bytes = json.dumps(grant, separators=(",", ":"), sort_keys=True).encode("utf-8")

        try:
            self.root_pub_key.verify(
                signature, grant_bytes, ec.ECDSA(hashes.SHA256())
            )
        except InvalidSignature:
            return None  # TPM signature is invalid

        # Check expiration
        expires_at_str = grant.get("expires_at", "")
        try:
            # Handle ISO format with 'Z' for UTC
            expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
            if datetime.now(timezone.utc) > expires_at:
                return None  # Grant has expired
        except ValueError:
            return None # Invalid date format

        # If valid, extract and return the developer's public key from the grant
        dev_pub_spki_b64 = grant.get("dev_pub_spki_b64", "")
        if not dev_pub_spki_b64:
            return None

        try:
            dev_pub_key_der = base64.b64decode(dev_pub_spki_b64)
            # load_der_public_key can handle various key types including Ed25519
            public_key = load_der_public_key(dev_pub_key_der)
            if isinstance(public_key, ed25519.Ed25519PublicKey):
                return public_key
            else:
                return None # Key type is not Ed25519
        except (ValueError, TypeError):
            return None # Base64 decoding or key loading failed
