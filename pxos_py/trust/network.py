import ssl
import yaml
import hashlib
import base64
from cryptography import x509
from cryptography.hazmat.primitives.serialization import Encoding
from pxos_py.ratelimit import Limiter

class NetworkGuard:
    """
    Provides network security features, including TLS certificate pinning and rate limiting.
    """
    def __init__(self, policy_path):
        """
        Initializes the NetworkGuard with a security policy.

        Args:
            policy_path (str): Path to the network policy YAML file.
        """
        try:
            with open(policy_path, "r") as f:
                self.policy = yaml.safe_load(f)
        except (FileNotFoundError, yaml.YAMLError) as e:
            print(f"Warning: Could not load network policy from {policy_path}. Failing closed. Error: {e}")
            self.policy = {"fail_closed": True}

        rate_limits = self.policy.get("rate_limits", {"requests_per_min": 60, "burst": 10})
        self.limiter = Limiter(
            rate_limits.get("requests_per_min", 60),
            rate_limits.get("burst", 10)
        )

    def _get_spki_hash(self, cert):
        """Calculates the SHA-256 hash of a certificate's Subject Public Key Info."""
        spki = cert.public_key().public_bytes(
            encoding=Encoding.DER,
            format=x509.SubjectPublicKeyInfo
        )
        return hashlib.sha256(spki).digest()

    def verify_spki(self, cert_chain_pem, domain):
        """
        Verifies the certificate chain against the SPKI pins in the policy.

        Args:
            cert_chain_pem (list): A list of PEM-encoded certificates in the chain.
            domain (str): The domain being connected to.

        Returns:
            bool: True if the pin is valid, False otherwise.
        """
        pin_config = self.policy.get("tls_pins", {}).get(domain)
        if not pin_config:
            # If no pins are defined for this domain, the connection is allowed by default.
            # For stricter policy, you could return False here.
            return True

        pin_level = pin_config.get("pin_level", "leaf")
        allowed_pins_b64 = pin_config.get("leaf_spki_sha256_b64", [])

        if not allowed_pins_b64:
            return False # No pins configured for this entry.

        allowed_pins = {base64.b64decode(pin) for pin in allowed_pins_b64}

        certs = [x509.load_pem_x509_certificate(c.encode('ascii')) for c in cert_chain_pem]

        if pin_level == "leaf":
            # Check only the leaf certificate
            cert_hash = self._get_spki_hash(certs[0])
            if cert_hash in allowed_pins:
                return True
        elif pin_level == "intermediate":
            # Check all certificates in the chain except the leaf
            for cert in certs[1:]:
                cert_hash = self._get_spki_hash(cert)
                if cert_hash in allowed_pins:
                    return True

        print(f"Error: SPKI pin validation failed for domain {domain}")
        return False

    def create_ssl_context(self, domain):
        """
        Creates an SSL context that can be used for secure connections.
        This is a placeholder as direct SSL context manipulation is complex.
        In a real application, you would hook the `verify_spki` method
        into your HTTP client's verification process.
        """
        if not self.policy.get("require_tls", True):
            return None # TLS is not required

        # This is a simplified representation. A real implementation would
        # use a library like `requests` with a custom verify adapter or
        # `pyOpenSSL` to manually verify the chain.
        context = ssl.create_default_context()
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        print("SSL context created. Manual SPKI verification is required during the handshake.")
        return context

    def allow_request(self):
        """Checks if a network request should be allowed based on rate limits."""
        if self.policy.get("fail_closed", False) and not self.limiter:
            return False
        return self.limiter.allow()
