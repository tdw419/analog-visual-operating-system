import json
import hashlib
import time
import os
import subprocess
from typing import Dict, Any, List
from dataclasses import dataclass, asdict

from .bitpack_v2 import BitPackV2Codec
from .ide.validate import validate_graph
# from .trust.key_grant import KeyGrantVerifier # This would be used by the trust_anchor

@dataclass
class Provenance:
    """Captures build environment information."""
    builder: str = "pxos/1.2.0"
    git_commit: str = ""
    git_status: str = "unknown"
    platform_os: str = os.name
    platform_arch: str = os.uname().machine
    reproducible_build: bool = True

    def __post_init__(self):
        try:
            self.git_commit = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
            git_status_output = subprocess.check_output(["git", "status", "--porcelain"]).decode().strip()
            self.git_status = "dirty" if git_status_output else "clean"
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.git_commit = "unknown"

@dataclass
class KeyLineage:
    """Tracks the cryptographic keys used for signing."""
    dev_pub_spki_b64: str
    grant_sig_tpm_b64: str
    root_pub_fingerprint_sha256: str

@dataclass
class SBOM:
    """Represents the Software Bill of Materials for a BitPack cartridge."""
    manifest_version: str = "v1"
    build_id: str = ""
    image_digest_sha256: str
    source_digest_sha256: str
    signature_hex: str
    provenance: Provenance
    key_lineage: KeyLineage
    artifacts: List[Dict[str, Any]]

    def __post_init__(self):
        if not self.build_id:
            timestamp = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            self.build_id = f"{timestamp}+{hashlib.sha256().hexdigest()[:8]}"

    def to_json(self):
        """Serializes the SBOM to a JSON string."""
        return json.dumps(asdict(self), indent=2)

class Builder:
    """
    Orchestrates the building of a signed, verifiable BitPack cartridge.
    """
    def __init__(self, trust_anchor):
        """
        Args:
            trust_anchor: An object capable of signing data and providing key info.
        """
        self.codec = BitPackV2Codec()
        self.trust_anchor = trust_anchor

    def build_from_ide_graph(self, graph: Dict[str, Any], key_lineage: KeyLineage):
        """
        Builds a cartridge from an IDE graph.

        Args:
            graph (Dict[str, Any]): The IDE graph structure.
            key_lineage (KeyLineage): Cryptographic key lineage information.

        Returns:
            A tuple of (encoded_buffer, sbom_json) or (None, None) on failure.
        """
        # 1. Validate the graph
        is_valid, message = validate_graph(graph)
        if not is_valid:
            print(f"IDE graph validation failed: {message}")
            return None, None

        # 2. Compile the graph to a source code representation (MVP)
        # This is a simplified compilation for the demo.
        source_code = "# Auto-generated from PXOS IDE\n\n"
        source_code += "def run():\n"
        for node in graph.get("nodes", []):
            node_type = node.get("type")
            props = node.get("props", {})
            if node_type == "Shader":
                source_code += f"    # Shader node: {node.get('id')}\n"
                source_code += f"    code = \"\"\"{props.get('code', '')}\"\"\"\n"
                source_code += "    print(f'Executing shader...')\n"
            elif node_type == "Input":
                source_code += f"    # Input node: {node.get('id')}\n"
                source_code += f"    value = {props.get('value')}\n"
        source_code += "\nrun()\n"

        print("Compiled IDE graph to source code:")
        print(source_code)

        # 3. Build the cartridge from the compiled source
        return self.build_cartridge(source_code, "pixelpy", key_lineage)

    def build_cartridge(self, source_code: str, lang_id: str, key_lineage: KeyLineage):
        """
        Builds a cartridge from source code.

        This involves encoding the source, generating an SBOM, signing it,
        and returning the final artifacts.
        """
        # 1. Encode source to pixel buffer
        encoded_buffer = self.codec.encode_to_buffer(source_code, lang_id)
        image_digest = hashlib.sha256(encoded_buffer.tobytes()).digest()

        source_digest = hashlib.sha256(source_code.encode('utf-8')).digest()

        # 2. Sign the image digest (using placeholder)
        # signature = self.trust_anchor.sign(image_digest)
        signature = b'\xde\xad\xbe\xef' * 16 # Placeholder signature

        # 3. Generate SBOM
        provenance = Provenance()
        sbom = SBOM(
            image_digest_sha256=image_digest.hex(),
            source_digest_sha256=source_digest.hex(),
            signature_hex=signature.hex(),
            provenance=provenance,
            key_lineage=key_lineage,
            artifacts=[{"lang_id": lang_id, "size": len(source_code)}]
        )

        # 4. Return artifacts
        print("Build process complete. SBOM generated.")
        return encoded_buffer, sbom.to_json()

# Example usage (for demonstration)
if __name__ == '__main__':
    class MockTrustAnchor:
        def sign(self, data):
            return b'\xde\xad\xbe\xef' * 16

    # Create dummy key lineage info
    lineage = KeyLineage(
        dev_pub_spki_b64="DEV_PUB_KEY_B64_HERE",
        grant_sig_tpm_b64="GRANT_SIG_B64_HERE",
        root_pub_fingerprint_sha256="ROOT_FINGERPRINT_HERE"
    )

    builder = Builder(trust_anchor=MockTrustAnchor())

    # --- Demo building from a text file ---
    print("--- Building from source file ---")
    builder.build_cartridge(
        source_code="print('hello world')",
        lang_id="pixelpy",
        key_lineage=lineage
    )
    print("\n" + "="*30 + "\n")

    # --- Demo building from an IDE graph ---
    print("--- Building from IDE graph ---")
    ide_graph = {
        "nodes": [
            {"id": "input1", "type": "Input", "props": {"value": 42}},
            {"id": "shader1", "type": "Shader", "props": {"code": "color = vec4(1,0,0,1);"}},
            {"id": "output1", "type": "Output", "props": {}}
        ]
    }
    builder.build_from_ide_graph(ide_graph, lineage)
