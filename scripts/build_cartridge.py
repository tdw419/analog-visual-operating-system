import argparse
import hashlib
import json
import os
import sys
import zstd

# Add project root to path to import pxos_py modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pxos_py.trust.anchor import TrustAnchor
from pxos_py.trust.sbom import generate_sbom
from pxos_py.bitpack_v2 import BitPackV2Codec

try:
    from PIL import Image
    import numpy as np
except ImportError:
    print("Pillow and numpy are required. Please run: pip install Pillow numpy")
    sys.exit(1)

def save_buffer_to_png(buffer: np.ndarray, path: str):
    """Saves an RGBA float32 numpy buffer to a PNG file."""
    if buffer.dtype != np.float32:
        raise TypeError("Input buffer must be of type float32")
    img_array = (np.clip(buffer, 0, 1) * 255).astype(np.uint8)
    img = Image.fromarray(img_array, 'RGBA')
    img.save(path, "PNG")
    print(f"Cartridge saved to {path}")

def main():
    parser = argparse.ArgumentParser(
        description="Build a secure PXOS v2 cartridge.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("source_file", help="Path to the source code file.")
    parser.add_argument("output_file", help="Path to save the output PNG cartridge.")
    parser.add_argument("--key", required=True, help="Path to the developer's private Ed25519 key file (PEM format).")
    parser.add_argument("--compress", action="store_true", help="Compress the cartridge content with Zstandard.")
    parser.add_argument("--lang", default="pixelpy", help="Language ID for the source code.")

    args = parser.parse_args()

    # --- Pre-Build Security Checks (Future Enhancement) ---
    # In a production CI/CD pipeline, additional security checks would be run here.
    # print("Running static analysis...")
    # subprocess.run(["sonarqube-scanner", "..."], check=True)
    # print("Running dependency vulnerability scan...")
    # subprocess.run(["pip-audit"], check=True)
    # ----------------------------------------------------

    # 1. Read and optionally compress source code
    print(f"Reading source from {args.source_file}...")
    with open(args.source_file, "r", encoding="utf-8") as f:
        source_text = f.read()

    code_bytes = source_text.encode('utf-8')
    if args.compress:
        print("Compressing code with Zstandard...")
        code_bytes = zstd.compress(code_bytes)

    # 2. Hash the code content
    code_digest = hashlib.sha256(code_bytes).digest()
    print(f"Code digest (sha256): {code_digest.hex()}")

    # 3. Sign the digest
    print(f"Loading private key from {args.key}...")
    trust_anchor = TrustAnchor(dev_priv_pem_path=args.key)
    signature = trust_anchor.sign_digest(code_digest)
    print(f"Signature (first 16 bytes): {signature[:16].hex()}...")

    # 4. Generate SBOM
    print("Generating SBOM...")
    sbom_path = args.output_file.rsplit('.', 1)[0] + ".sbom.json"

    # The SBOM needs the final signature, so we create it as a dictionary first
    artifact_meta = {
        "data": code_bytes,
        "signature": signature.hex(),
        "metadata": {"lang_id": args.lang}
    }

    # For now, we pass a simplified structure to generate_sbom
    generate_sbom(
        artifacts=[artifact_meta],
        output_path=sbom_path,
        sources=[args.source_file],
        modules=["main"] # Placeholder
    )

    with open(sbom_path, "r", encoding="utf-8") as f:
        sbom_text = f.read()

    sbom_bytes = sbom_text.encode('utf-8')
    if args.compress:
        sbom_bytes = zstd.compress(sbom_bytes)

    # 5. Encode the cartridge
    print("Encoding cartridge to pixel buffer...")
    codec = BitPackV2Codec()
    buffer = codec.encode_to_buffer(
        code_bytes=code_bytes,
        lang_id=args.lang,
        is_compressed=args.compress,
        signature=signature,
        sbom_bytes=sbom_bytes,
    )

    # 6. Save the cartridge as a PNG
    save_buffer_to_png(buffer, args.output_file)
    print("\nBuild complete.")

if __name__ == "__main__":
    main()
