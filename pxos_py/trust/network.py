import requests
import yaml
import ssl
import hashlib
import base64
import socket
from urllib.parse import urlparse
from requests.adapters import HTTPAdapter
from requests.exceptions import SSLError

from pxos_py.ratelimit import Limiter
from cryptography import x509
from cryptography.hazmat.primitives import serialization

class PinnedHTTPAdapter(HTTPAdapter):
    """An HTTP adapter that enforces SPKI pinning."""
    def __init__(self, pins, **kwargs):
        self.pins = pins
        super().__init__(**kwargs)

    def cert_verify(self, conn, url, verify, cert):
        hostname = conn.host

        if hostname not in self.pins:
            # Fallback to default verification if no pins for this host
            return super().cert_verify(conn, url, verify, cert)

        # Get the server's certificate in DER format
        cert_der = conn.sock.getpeercert(binary_form=True)

        # Load the certificate with cryptography
        cert_obj = x509.load_der_x509_certificate(cert_der)

        # Calculate the SPKI hash
        pubkey_bytes = cert_obj.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        spki_hash = hashlib.sha256(pubkey_bytes).digest()
        spki_b64 = base64.b64encode(spki_hash).decode('utf-8')

        # Check against the configured pins
        pin_config = self.pins[hostname]
        expected_pins = pin_config.get("leaf_spki_sha256_b64", [])

        if spki_b64 not in expected_pins:
            raise SSLError(f"Certificate pin validation failed for {hostname}. Got {spki_b64}, expected one of {expected_pins}")

        # Pinning successful, continue with other default checks (like hostname matching)
        super().cert_verify(conn, url, verify, cert)

class NetworkGuard:
    """
    A network wrapper that enforces security policies like rate limiting,
    domain whitelisting, and TLS certificate pinning.
    """
    def __init__(self, policy_path: str):
        with open(policy_path, "r") as f:
            self.policy = yaml.safe_load(f)

        self.limiter = Limiter(
            self.policy.get("rate_limits", {}).get("requests_per_min", 60),
            self.policy.get("rate_limits", {}).get("burst", 20)
        )

        self.ip_blocklist = self.policy.get("ip_blocklist", [])

        self.session = requests.Session()
        pins = self.policy.get("tls_pins", {})
        if pins:
            self.session.mount("https://", PinnedHTTPAdapter(pins))

    def post(self, url, **kwargs):
        """
        Performs a POST request, guarded by security policies.
        """
        hostname = urlparse(url).hostname

        if self.policy.get("fail_closed", True) and hostname not in self.policy.get("allowed_domains", []):
            raise ConnectionError(f"Domain '{hostname}' is not in the allowed list.")

        try:
            ip_address = socket.gethostbyname(hostname)
            if ip_address in self.ip_blocklist:
                raise ConnectionError(f"IP address {ip_address} for domain '{hostname}' is on the blocklist.")
        except socket.gaierror:
            # If we can't resolve the IP, we might want to block it depending on the policy.
            # For now, we'll let it pass and let the request fail on its own.
            pass

        if not self.limiter.allow():
            raise ConnectionError(f"Rate limit exceeded for domain '{hostname}'.")

        # The 'http://localhost' case from the grep won't use the https adapter,
        # which is fine. Pinning only applies to https.
        return self.session.post(url, **kwargs)
