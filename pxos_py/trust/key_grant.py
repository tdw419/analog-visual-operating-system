import json
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.exceptions import InvalidSignature
from datetime import datetime, timezone

class KeyGrantVerifier:
    """
    Verifies a key grant against a TPM-backed root public key.
    The grant attests that a specific developer key is authorized for a purpose (e.g., build-signing).
    """
    def __init__(self, root_pub_path):
        """
        Initializes the verifier with the root public key.

        Args:
            root_pub_path (str): Path to the TPM root public key in PEM format (e.g., root_pub.der).
        """
        try:
            with open(root_pub_path, "rb") as f:
                self.root_pub = load_pem_public_key(f.read())
        except FileNotFoundError:
            print(f"Error: Root public key not found at {root_pub_path}")
            self.root_pub = None
        except Exception as e:
            print(f"Error loading root public key: {e}")
            self.root_pub = None

    def verify(self, grant_path, sig_path):
        """
        Verifies a key grant by checking its signature and expiration.

        Args:
            grant_path (str): Path to the key grant JSON file.
            sig_path (str): Path to the signature file for the key grant.

        Returns:
            bytes: The developer's public key if the grant is valid, otherwise None.
        """
        if not self.root_pub:
            return None

        try:
            with open(grant_path, "r") as f:
                grant = json.load(f)
            with open(sig_path, "rb") as f:
                signature = f.read()
        except FileNotFoundError as e:
            print(f"Error: Grant file or signature not found: {e}")
            return None
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in grant file: {grant_path}")
            return None

        # Verify the signature over the canonical JSON representation
        grant_bytes = json.dumps(grant, separators=(',', ':'), sort_keys=True).encode('utf-8')
        try:
            self.root_pub.verify(signature, grant_bytes, ec.ECDSA(hashes.SHA256()))
        except InvalidSignature:
            print("Error: Invalid signature for key grant.")
            return None

        # Check expiration
        try:
            # Assumes UTC if no timezone is specified
            expires_at_str = grant["expires_at"]
            expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)

            now = datetime.now(timezone.utc)

            if now > expires_at:
                print("Error: Key grant has expired.")
                return None
        except (KeyError, ValueError) as e:
            print(f"Error parsing expiration date: {e}")
            return None

        # Return the developer's public key
        try:
            return base64.b64decode(grant["dev_pub_spki_b64"])
        except (KeyError, base64.BinasciiError) as e:
            print(f"Error decoding dev public key from grant: {e}")
            return None
