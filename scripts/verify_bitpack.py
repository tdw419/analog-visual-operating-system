import argparse
import os
import sys
import json

# Add project root to path to import pxos_py modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pxos_py.bitpack_v2 import BitPackV2Codec
from pxos_py.trust.anchor import TrustAnchor

try:
    from PIL import Image
    import numpy as np
except ImportError:
    print("Pillow and numpy are required. Please run: pip install Pillow numpy", file=sys.stderr)
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="Verify the signature of a secure PXOS v2 cartridge.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("cartridge_file", help="Path to the cartridge PNG file.")
    parser.add_argument("--key", required=True, help="Path to the developer's public Ed25519 key file (PEM format).")

    args = parser.parse_args()

    if not os.path.exists(args.cartridge_file):
        print(f"❌ Error: Cartridge file not found at {args.cartridge_file}", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(args.key):
        print(f"❌ Error: Public key file not found at {args.key}", file=sys.stderr)
        sys.exit(1)

    # 1. Decode the cartridge from the PNG file
    try:
        print(f"🔍 Decoding cartridge: {args.cartridge_file}")
        img = Image.open(args.cartridge_file).convert("RGBA")
        buffer = np.array(img, dtype=np.float32) / 255.0
        codec = BitPackV2Codec()
        cartridge = codec.decode_from_buffer(buffer)
    except Exception as e:
        print(f"❌ Error decoding cartridge: {e}", file=sys.stderr)
        sys.exit(1)

    # 2. Initialize Trust Anchor with the public key
    try:
        trust_anchor = TrustAnchor(dev_pub_pem_path=args.key)
        if not trust_anchor.dev_pub_key:
            raise ValueError("Failed to load public key.")
    except Exception as e:
        print(f"❌ Error loading public key from {args.key}: {e}", file=sys.stderr)
        sys.exit(1)

    # 3. Verify the signature
    signature = cartridge.get("signature")
    digest_hex = cartridge.get("digest")

    if not signature or not digest_hex:
        print("❌ Verification failed: Cartridge is not signed.", file=sys.stderr)
        sys.exit(1)

    digest_bytes = bytes.fromhex(digest_hex)
    if trust_anchor.verify_signature(signature, digest_bytes, trust_anchor.dev_pub_key):
        print("✅ Signature is valid.")
    else:
        print("❌ Signature is invalid.", file=sys.stderr)
        sys.exit(1)

    # 4. Check for SBOM presence
    if cartridge.get("sbom_raw"):
        print("✅ SBOM is present.")
    else:
        print("⚠️ Warning: SBOM is not present.")

    print("\nVerification successful.")

if __name__ == "__main__":
    main()
