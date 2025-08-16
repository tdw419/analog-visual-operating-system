import json
import sys
import base64
import binascii
from nacl.signing import VerifyKey
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.exceptions import InvalidSignature

def verify_key_grant(grant_path, sig_path, root_pub_path):
    """Verify TPM signature on key grant and return the dev public key if valid."""
    try:
        with open(root_pub_path, "rb") as f:
            root_pub = load_pem_public_key(f.read())

        with open(grant_path, "r") as f:
            grant = json.load(f)

        with open(sig_path, "rb") as f:
            signature = f.read()

        grant_bytes = json.dumps(grant, separators=(',', ':')).encode('utf-8')

        root_pub.verify(signature, grant_bytes, ec.ECDSA(hashes.SHA256()))

        print("[ok] Key grant signature is valid.")
        return base64.b64decode(grant["dev_pub_spki_b64"])
    except FileNotFoundError as e:
        print(f"[error] Could not find a required file: {e.filename}", file=sys.stderr)
        return None
    except (InvalidSignature, json.JSONDecodeError, KeyError, Exception) as e:
        print(f"[error] Key grant verification failed: {e}", file=sys.stderr)
        return None

def main(manifest_path, dev_pub_key_b64, grant_path, sig_path, root_pub_path):
    # Verify the key grant first
    dev_pub_from_grant = verify_key_grant(grant_path, sig_path, root_pub_path)
    if not dev_pub_from_grant:
        print("[error] Halting due to invalid key grant.", file=sys.stderr)
        sys.exit(1)

    # Verify the manifest signature
    try:
        with open(manifest_path, "r") as f:
            manifest = json.load(f)

        sig_hex = manifest["trust"]["sig_hex"]
        img_digest = binascii.unhexlify(manifest["digests"]["image_sha256"])

        # Use the dev public key from the verified grant
        vk = VerifyKey(dev_pub_from_grant)

        vk.verify(img_digest, binascii.unhexlify(sig_hex))
        print("[ok] ed25519 signature is valid.")
    except FileNotFoundError:
        print(f"[error] Manifest file not found at {manifest_path}", file=sys.stderr)
        sys.exit(1)
    except (binascii.Error, InvalidSignature, json.JSONDecodeError, KeyError) as e:
        print(f"[error] Manifest signature verification failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 6:
        print("Usage: python verify_bitpack.py <path_to_sbom.json> <dev_pub_b64> <key_grant.json> <grant.sig> <root_pub.der>", file=sys.stderr)
        sys.exit(1)
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
