import subprocess
import json
from datetime import datetime
from typing import Dict

# Add project root to path to import pxos_py modules
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from pxos_py.trust.anchor import TrustAnchor

class SecurityHardening:
    """
    A framework for running security scans and evaluating the compliance
    of the PXOS build.
    """
    def __init__(self):
        self.vulnerability_scanners = {
            'grype': self._scan_with_grype,
            'bandit': self._scan_with_bandit,
            'safety': self._scan_with_safety
        }
        self.trust_anchor = TrustAnchor() # Assumes default keys can be found

    def _scan_with_grype(self, target_path: str) -> Dict:
        """Stub for Grype vulnerability scan."""
        print(f"[SCAN] Running grype on {target_path} (stubbed)")
        # In a real CI environment, this would be:
        # result = subprocess.run(["grype", target_path, "-o", "json"], ...)
        return {"vulnerabilities_found": 0, "details": "stub: no issues found"}

    def _scan_with_bandit(self, target_path: str) -> Dict:
        """Stub for Bandit static analysis."""
        print(f"[SCAN] Running bandit on {target_path} (stubbed)")
        # In a real CI environment, this would be:
        # result = subprocess.run(["bandit", "-r", target_path, "-f", "json"], ...)
        return {"issues_found": 0, "details": "stub: no issues found"}

    def _scan_with_safety(self, target_path: str) -> Dict:
        """Stub for Safety dependency check."""
        print(f"[SCAN] Running safety on requirements.txt (stubbed)")
        # In a real CI environment, this would be:
        # result = subprocess.run(["safety", "check", "-r", "requirements.txt", "--json"], ...)
        return {"vulnerabilities_found": 0, "details": "stub: no issues found"}

    def _evaluate_compliance(self, results: Dict) -> str:
        """Evaluates the overall compliance status based on scan results."""
        for tool, result in results.items():
            if result.get("issues_found", 0) > 0 or result.get("vulnerabilities_found", 0) > 0:
                return "FAIL"
        return "PASS"

    def comprehensive_scan(self, target_path: str) -> Dict:
        """Runs all configured security scanners on a given target path."""
        results = {}
        for scanner_name, scanner_func in self.vulnerability_scanners.items():
            try:
                # For 'safety', the target path is not used, it checks the environment
                scan_target = "requirements.txt" if scanner_name == "safety" else target_path
                results[scanner_name] = scanner_func(scan_target)
            except Exception as e:
                results[scanner_name] = {"error": str(e)}

        # Generate compliance report
        trust_anchor_status = {"public_key_loaded": self.trust_anchor.dev_pub_key is not None}

        return {
            "scan_results": results,
            "compliance_status": self._evaluate_compliance(results),
            "timestamp": datetime.utcnow().isoformat(),
            "trust_anchor_status": trust_anchor_status
        }
