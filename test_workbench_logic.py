import unittest
from analog_code_workbench import (
    source_to_ops,
    ops_to_csv,
    csv_to_ops,
    ViewerAdapter
)
from python_viewer import run_python_viewer

class TestWorkbenchLogic(unittest.TestCase):

    def test_viewer_integration_roundtrip(self):
        """
        Tests the 'Run with Viewer' data path and the CSV-to-Ops-to-CSV round-trip conversion.
        """
        print("\n--- Testing Viewer Integration and CSV Round-trip ---")

        # 1. Reset the adapter and run the viewer to capture ops in CSV format
        VA = ViewerAdapter
        VA.reset()
        run_python_viewer()

        # 2. Get the captured CSV
        captured_csv = VA.get_captured_csv()
        print(f"Captured CSV from viewer:\n{captured_csv}\n")
        self.assertTrue(len(captured_csv.strip()) > 0, "CSV should not be empty after viewer run.")

        # 3. Convert CSV back to our internal opcode format
        ops_from_csv = csv_to_ops(captured_csv)
        print(f"Opcodes converted from CSV:\n{ops_from_csv}\n")
        self.assertTrue(len(ops_from_csv) > 0, "Opcode list should not be empty after CSV conversion.")

        # 4. Convert opcodes back to CSV
        reconstructed_csv = ops_to_csv(ops_from_csv)
        print(f"Reconstructed CSV from opcodes:\n{reconstructed_csv}\n")

        # 5. Verify that the reconstructed CSV is equivalent to the captured one.
        # Using set comparison to ignore potential line order differences.
        self.assertEqual(
            set(captured_csv.strip().split('\n')),
            set(reconstructed_csv.strip().split('\n')),
            "Reconstructed CSV must match the original captured CSV."
        )
        print("SUCCESS: Viewer integration and CSV round-trip test passed.")

    def test_source_to_csv_conversion(self):
        """
        Tests the direct source code (Pane 1) to CSV conversion path.
        """
        print("\n--- Testing Source Code to CSV Conversion ---")
        source_code = "# Example source\nRECT(20,20,40,20,64)\nCOMMIT()"

        # 1. Convert source to ops
        ops = source_to_ops(source_code)
        print(f"Ops from source:\n{ops}\n")
        self.assertTrue(len(ops) > 0, "Should generate opcodes from source.")

        # 2. Convert ops to CSV
        csv = ops_to_csv(ops)
        print(f"CSV from ops:\n{csv}\n")
        self.assertIn("RECT,20,20,40,20,64,64,64", csv)
        self.assertIn("COMMIT", csv)
        print("SUCCESS: Source-to-CSV conversion test passed.")

if __name__ == '__main__':
    unittest.main()
