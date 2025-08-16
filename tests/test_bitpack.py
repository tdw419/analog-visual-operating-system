import unittest
import os
import numpy as np

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pxos_py.bitpack_v2 import BitPackV2Codec

class TestBitpack(unittest.TestCase):

    def test_encode_decode_segmented(self):
        """
        Test that a cartridge with code, signature, and SBOM segments
        can be encoded and decoded correctly.
        """
        codec = BitPackV2Codec()

        # 1. Create dummy data
        source_code = "print('hello world')"
        code_bytes = source_code.encode('utf-8')

        signature = b"B" * 64 # Dummy 64-byte signature
        sbom = '{"version": 1, "name": "test_cartridge"}'
        sbom_bytes = sbom.encode('utf-8')

        # 2. Encode the cartridge
        buffer = codec.encode_to_buffer(
            code_bytes=code_bytes,
            signature=signature,
            sbom_bytes=sbom_bytes,
            lang_id="pixelpy",
            is_compressed=False
        )

        self.assertIsInstance(buffer, np.ndarray)

        # 3. Decode the cartridge
        decoded = codec.decode_from_buffer(buffer)

        # 4. Assert correctness
        self.assertEqual(decoded["text"], source_code)
        self.assertEqual(decoded["signature"], signature)
        self.assertEqual(decoded["sbom_raw"], sbom_bytes)
        self.assertEqual(decoded["lang"], "pixelpy")

if __name__ == "__main__":
    unittest.main()
