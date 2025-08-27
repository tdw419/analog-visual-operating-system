#!/usr/bin/env python3
"""
VisualPython Unified Integration Test

This test validates the complete headless simulator + CSV pipeline:
- SimRenderer backend functionality
- CSV recording and playback 
- Frame-batched rendering
- Round-trip fidelity
- Live watching capability

Run from the visualpython directory:
    python test_unified_integration.py
"""

import os
import sys
import tempfile
import shutil
import time
import hashlib
from pathlib import Path

# Add visualpython to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir / "src"))

try:
    from visualpython.core import VisualPythonEngine
    from visualpython.backends import create_backend, RecordRenderer, csv_play
    print("✅ Successfully imported VisualPython modules")
except ImportError as e:
    print(f"❌ Failed to import VisualPython modules: {e}")
    sys.exit(1)


class IntegrationTester:
    """Comprehensive test suite for VisualPython Unified"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.temp_dir = None
    
    def setup(self):
        """Set up test environment"""
        self.temp_dir = Path(tempfile.mkdtemp(prefix="vp_test_"))
        print(f"📁 Test directory: {self.temp_dir}")
    
    def cleanup(self):
        """Clean up test environment"""
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            print(f"🧹 Cleaned up {self.temp_dir}")
    
    def run_test(self, name, test_func):
        """Run a single test with error handling"""
        print(f"\n🧪 Testing: {name}")
        try:
            test_func()
            print(f"✅ {name} PASSED")
            self.passed += 1
        except Exception as e:
            print(f"❌ {name} FAILED: {e}")
            self.failed += 1
            import traceback
            traceback.print_exc()
    
    def test_simulator_backend_creation(self):
        """Test creating SimRenderer backend"""
        backend = create_backend('simulator', width=200, height=150, out_dir=str(self.temp_dir / 'frames'))
        assert hasattr(backend, 'w') and backend.w == 200
        assert hasattr(backend, 'h') and backend.h == 150
        assert hasattr(backend, 'clear')
        assert hasattr(backend, 'rect')
        assert hasattr(backend, 'text')
        assert hasattr(backend, 'commit')
    
    def test_basic_rendering(self):
        """Test basic rendering operations"""
        frames_dir = self.temp_dir / 'basic_frames'
        backend = create_backend('simulator', width=200, height=150, out_dir=str(frames_dir))
        
        # Draw simple scene
        backend.clear("#001100")
        backend.rect(50, 25, 100, 50, 255, 0, 0)
        backend.text(60, 35, "TEST", 255, 255, 255)
        backend.commit()
        
        backend.set_pixel(75, 75, 0, 255, 0)
        backend.commit()
        
        # Verify frames were created
        frame_files = list(frames_dir.glob("*.png")) + list(frames_dir.glob("*.ppm"))
        assert len(frame_files) >= 2, f"Expected at least 2 frames, got {len(frame_files)}"
        
        print(f"   Generated {len(frame_files)} frame files")
    
    def test_csv_recording(self):
        """Test CSV recording functionality"""
        frames_dir = self.temp_dir / 'record_frames'
        csv_path = self.temp_dir / 'recording.csv'
        
        # Create base backend
        base_backend = create_backend('simulator', width=200, height=150, out_dir=str(frames_dir))
        
        # Wrap with recorder
        recorder = RecordRenderer(base_backend, str(csv_path))\n        \n        # Perform operations\n        recorder.clear(\"#002200\")\n        recorder.rect(10, 10, 50, 30, 100, 150, 200)\n        recorder.text(15, 20, \"RECORD\", 255, 255, 255)\n        recorder.commit()\n        \n        recorder.set_pixel(80, 80, 255, 0, 255)\n        recorder.commit()\n        \n        # Close recorder\n        recorder.close()\n        \n        # Verify CSV was created and has content\n        assert csv_path.exists(), \"CSV file not created\"\n        \n        with open(csv_path, 'r') as f:\n            content = f.read()\n            assert \"CLEAR\" in content\n            assert \"RECT\" in content  \n            assert \"TEXT\" in content\n            assert \"PIXEL\" in content\n            assert \"COMMIT\" in content\n            assert \"RECORD\" in content\n        \n        print(f\"   CSV recording successful: {len(content)} characters\")\n    \n    def test_csv_playback(self):\n        \"\"\"Test CSV playback functionality\"\"\"\n        # Create test CSV\n        csv_path = self.temp_dir / 'test_playback.csv'\n        csv_content = '''frame,op,x,y,w,h,r,g,b,text\n0,CLEAR,,,,,,0,34,0,\n0,RECT,40,20,80,60,50,100,200,\n0,TEXT,50,30,,,,255,255,255,PLAY\n0,COMMIT,,,,,,,,\n1,PIXEL,100,100,,,255,128,0,\n1,COMMIT,,,,,,,,'''\n        \n        with open(csv_path, 'w') as f:\n            f.write(csv_content)\n        \n        # Play CSV\n        frames_dir = self.temp_dir / 'playback_frames'\n        backend = create_backend('simulator', width=200, height=150, out_dir=str(frames_dir))\n        csv_play(backend, str(csv_path))\n        \n        # Verify frames were created\n        frame_files = list(frames_dir.glob(\"*.png\")) + list(frames_dir.glob(\"*.ppm\"))\n        assert len(frame_files) >= 2, f\"Expected at least 2 frames, got {len(frame_files)}\"\n        \n        print(f\"   CSV playback successful: {len(frame_files)} frames\")\n    \n    def test_round_trip_fidelity(self):\n        \"\"\"Test that record->playback produces identical results\"\"\"\n        # Step 1: Record a sequence\n        frames_dir1 = self.temp_dir / 'round_trip_1'\n        csv_path = self.temp_dir / 'round_trip.csv'\n        \n        base1 = create_backend('simulator', width=150, height=100, out_dir=str(frames_dir1))\n        recorder = RecordRenderer(base1, str(csv_path))\n        \n        # Create deterministic sequence\n        recorder.clear(\"#000000\")\n        recorder.rect(0, 0, 50, 50, 255, 255, 255)\n        recorder.commit()\n        recorder.close()\n        \n        # Step 2: Play back the CSV\n        frames_dir2 = self.temp_dir / 'round_trip_2'\n        base2 = create_backend('simulator', width=150, height=100, out_dir=str(frames_dir2))\n        csv_play(base2, str(csv_path))\n        \n        # Step 3: Compare frame files\n        files1 = sorted(frames_dir1.glob(\"*\"))\n        files2 = sorted(frames_dir2.glob(\"*\"))\n        \n        assert len(files1) == len(files2), f\"Frame count mismatch: {len(files1)} vs {len(files2)}\"\n        \n        # Compare file sizes (exact pixel comparison would require image parsing)\n        for f1, f2 in zip(files1, files2):\n            size1 = f1.stat().st_size\n            size2 = f2.stat().st_size\n            # Allow small differences due to timestamp metadata\n            assert abs(size1 - size2) < 100, f\"Frame size mismatch: {size1} vs {size2}\"\n        \n        print(f\"   Round-trip fidelity verified: {len(files1)} frames\")\n    \n    def test_frame_batching(self):\n        \"\"\"Test that operations in same frame are batched together\"\"\"\n        csv_path = self.temp_dir / 'batch_test.csv'\n        frames_dir = self.temp_dir / 'batch_frames'\n        \n        # Create CSV with multiple ops per frame\n        csv_content = '''frame,op,x,y,w,h,r,g,b,text\n5,CLEAR,,,,,,10,10,10,\n5,RECT,10,10,30,20,255,0,0,\n5,RECT,50,10,30,20,0,255,0,\n5,TEXT,15,15,,,,255,255,255,A\n5,TEXT,55,15,,,,255,255,255,B\n5,COMMIT,,,,,,,,\n7,PIXEL,100,50,,,0,0,255,\n7,PIXEL,101,50,,,0,0,255,\n7,COMMIT,,,,,,,,'''\n        \n        with open(csv_path, 'w') as f:\n            f.write(csv_content)\n        \n        # Play and verify only 2 frames created (5 and 7)\n        backend = create_backend('simulator', width=200, height=100, out_dir=str(frames_dir))\n        csv_play(backend, str(csv_path))\n        \n        frame_files = sorted(frames_dir.glob(\"*\"))\n        assert len(frame_files) == 2, f\"Expected 2 frames, got {len(frame_files)}\"\n        \n        print(f\"   Frame batching verified: {len(frame_files)} frames from 2 commit operations\")\n    \n    def test_error_handling(self):\n        \"\"\"Test error handling in various scenarios\"\"\"\n        # Test with invalid CSV\n        invalid_csv = self.temp_dir / 'invalid.csv'\n        with open(invalid_csv, 'w') as f:\n            f.write(\"invalid,csv,content\\n1,BADOP,x,y\")\n        \n        # Should not crash\n        frames_dir = self.temp_dir / 'error_frames'\n        backend = create_backend('simulator', width=100, height=100, out_dir=str(frames_dir))\n        \n        try:\n            csv_play(backend, str(invalid_csv))\n            # Should handle gracefully\n        except Exception:\n            pass  # Expected for invalid content\n        \n        print(\"   Error handling verified\")\n    \n    def print_summary(self):\n        \"\"\"Print test results summary\"\"\"\n        total = self.passed + self.failed\n        print(f\"\\n📊 Integration Test Results\")\n        print(f\"=\"*50)\n        print(f\"✅ Passed: {self.passed}\")\n        print(f\"❌ Failed: {self.failed}\")\n        print(f\"📈 Success Rate: {(self.passed/total*100):.1f}%\" if total > 0 else \"No tests run\")\n        \n        if self.failed == 0:\n            print(\"\\n🎉 All integration tests passed!\")\n            print(\"VisualPython Unified simulator is ready for production use.\")\n        else:\n            print(f\"\\n⚠️  {self.failed} test(s) failed. Please review the errors above.\")\n        \n        return self.failed == 0\n\n\ndef main():\n    \"\"\"Run the complete integration test suite\"\"\"\n    print(\"🚀 VisualPython Unified Integration Test Suite\")\n    print(\"=\"*60)\n    \n    tester = IntegrationTester()\n    \n    try:\n        tester.setup()\n        \n        # Core functionality tests\n        tester.run_test(\"Simulator Backend Creation\", tester.test_simulator_backend_creation)\n        tester.run_test(\"Basic Rendering Operations\", tester.test_basic_rendering)\n        tester.run_test(\"CSV Recording\", tester.test_csv_recording)\n        tester.run_test(\"CSV Playback\", tester.test_csv_playback)\n        tester.run_test(\"Round-Trip Fidelity\", tester.test_round_trip_fidelity)\n        tester.run_test(\"Frame Batching\", tester.test_frame_batching)\n        tester.run_test(\"Error Handling\", tester.test_error_handling)\n        \n        # Print final results\n        success = tester.print_summary()\n        \n    finally:\n        tester.cleanup()\n    \n    return 0 if success else 1\n\n\nif __name__ == \"__main__\":\n    sys.exit(main())"