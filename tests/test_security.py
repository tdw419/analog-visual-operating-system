import unittest
import os
import hashlib
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

# Add project root to path
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pxos_py.trust.anchor import TrustAnchor

class TestSecurity(unittest.TestCase):

    def setUp(self):
        """Generate a key pair for testing."""
        self.private_key = ed25519.Ed25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()

        self.priv_key_path = "test_priv.pem"
        self.pub_key_path = "test_pub.pem"

        with open(self.priv_key_path, "wb") as f:
            f.write(self.private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))

        with open(self.pub_key_path, "wb") as f:
            f.write(self.public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ))

    def tearDown(self):
        """Remove temporary key files."""
        if os.path.exists(self.priv_key_path):
            os.remove(self.priv_key_path)
        if os.path.exists(self.pub_key_path):
            os.remove(self.pub_key_path)

    def test_sign_and_verify(self):
        """Test that a signature created by a TrustAnchor can be verified."""
        # 1. Create a signing anchor
        signing_anchor = TrustAnchor(dev_priv_pem_path=self.priv_key_path)
        self.assertIsNotNone(signing_anchor.dev_priv_key)

        # 2. Sign some data
        data = b"this is some test data"
        digest = hashlib.sha256(data).digest()
        signature = signing_anchor.sign_digest(digest)

        # 3. Create a verifying anchor
        verifying_anchor = TrustAnchor(dev_pub_pem_path=self.pub_key_path)
        self.assertIsNotNone(verifying_anchor.dev_pub_key)

        # 4. Verify the signature
        is_valid = verifying_anchor.verify_signature(signature, digest, verifying_anchor.dev_pub_key)
        self.assertTrue(is_valid)

    def test_invalid_signature(self):
        """Test that an invalid signature fails verification."""
        signing_anchor = TrustAnchor(dev_priv_pem_path=self.priv_key_path)
        verifying_anchor = TrustAnchor(dev_pub_pem_path=self.pub_key_path)

        data = b"some data"
        digest = hashlib.sha256(data).digest()
        signature = signing_anchor.sign_digest(digest)

        invalid_data = b"different data"
        invalid_digest = hashlib.sha256(invalid_data).digest()

        is_valid = verifying_anchor.verify_signature(signature, invalid_digest, verifying_anchor.dev_pub_key)
        self.assertFalse(is_valid)

if __name__ == "__main__":
    unittest.main()
