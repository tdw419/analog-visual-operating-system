"""
PXOS Trust Anchor: Cryptographic signing and verification
"""
import hashlib

class TrustAnchor:
    """
    Provides cryptographic signing and verification services.
    This is a placeholder implementation. In a real system, this would
    interface with a Hardware Security Module (HSM) or a TPM.
    """
    def __init__(self):
        # In a real implementation, this key would be securely stored.
        self._private_key = b"pxos-dummy-private-key"

    def sign(self, data: bytes) -> bytes:
        """Sign data using a dummy signature scheme."""
        # This is NOT a secure signature. For demonstration purposes only.
        return hashlib.sha256(self._private_key + data).hexdigest().encode('utf-8')

    def verify(self, data: bytes, signature: bytes) -> bool:
        """Verify a signature."""
        expected_signature = self.sign(data)
        return signature == expected_signature

    def get_public_key_b64(self) -> str:
        """Return a dummy public key."""
        return "cHgwc19kdW1teV9wdWJsaWNfa2V5"

    def get_grant_signature(self) -> str:
        """Return a dummy grant signature."""
        return "dummy_grant_signature"

    def get_root_fingerprint(self) -> str:
        """Return a dummy root fingerprint."""
        return "dummy_root_fingerprint"
