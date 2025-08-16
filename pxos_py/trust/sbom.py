import json
import hashlib
import os
import sys
import subprocess
import importlib.metadata
from datetime import datetime
from typing import List, Dict, Any, Optional

def _get_installed_dependencies() -> List[Dict[str, str]]:
    """Gets a list of installed packages and their versions."""
    return [
        {"name": dist.metadata["name"], "version": dist.version}
        for dist in importlib.metadata.distributions()
    ]

def generate_sbom(
    artifacts: List[Dict[str, Any]],
    output_path: str,
    sources: List[str],
    modules: List[str],
    dependencies: Optional[List[Dict[str, str]]] = None,
    provenance: Dict[str, Any] = None,
    key_lineage: Dict[str, Any] = None,
) -> None:
    """
    Generates an SBOM for a build, including provenance, dependencies, and key lineage.
    """
    if provenance is None:
        try:
            commit = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
            status = "dirty" if subprocess.check_output(["git", "status", "--porcelain"]).decode().strip() else "clean"
        except (subprocess.CalledProcessError, FileNotFoundError):
            commit, status = "unknown", "unknown"

        provenance = {
            "builder": "pxos/1.2.0",
            "git": {"commit": commit, "status": status},
            "platform": {"os": sys.platform, "arch": os.uname().machine},
            "repro_mode": True
        }

    # If dependencies are not provided, discover them from the environment.
    if dependencies is None:
        dependencies = _get_installed_dependencies()

    image_data = b"".join(a.get("data", b"") for a in artifacts)

    sbom = {
        "pxos_manifest": "v1",
        "build_id": f"{datetime.utcnow().isoformat()}Z",
        "inputs": sources,
        "modules": modules,
        "digests": {
            "image_sha256": hashlib.sha256(image_data).hexdigest(),
            "sources_sha256": hashlib.sha256("".join(sources).encode("utf-8")).hexdigest(),
        },
        "trust": {
            "signer": "ed25519:dev",
            "sig_hex": artifacts[0].get("signature", "") if artifacts else "",
        },
        "provenance": provenance,
        "key_lineage": key_lineage or {},
        "dependencies": dependencies,
        "vulnerabilities": [],  # Placeholder for future vulnerability scan results
        "artifacts": [
            {
                "metadata": a.get("metadata", {}),
                "signature": a.get("signature", ""),
                "checksum": hashlib.sha256(a.get("data", b"")).hexdigest(),
            }
            for a in artifacts
        ],
    }

    with open(output_path, "w") as f:
        json.dump(sbom, f, indent=2)


def validate_sbom(sbom_path: str, policy: Dict[str, Any]) -> bool:
    """
    Validates an SBOM against a given policy.
    (This is a placeholder for more complex policy validation)
    """
    if not os.path.exists(sbom_path):
        return False

    with open(sbom_path, "r") as f:
        sbom = json.load(f)

    # Example policy check: ensure the builder is a trusted version
    allowed_builders = policy.get("allowed_builders", [])
    builder = sbom.get("provenance", {}).get("builder", "")
    if allowed_builders and builder not in allowed_builders:
        return False

    # Example policy check: ensure git status was clean
    if policy.get("require_clean_git_status", False):
        git_status = sbom.get("provenance", {}).get("git", {}).get("status", "dirty")
        if git_status != "clean":
            return False

    return True
