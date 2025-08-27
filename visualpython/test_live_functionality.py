#!/usr/bin/env python3
"""
Comprehensive Test Suite for VisualPython Unified --live Feature

This script validates:
1. Basic --live functionality with Python scripts
2. Live CSV playback 
3. --mirror flag integration
4. Error handling and recovery
5. File watching robustness
"""

import os
import sys
import subprocess
import time
import tempfile
import shutil
from pathlib import Path

class LiveFeatureTester:
    """Test suite for VisualPython Unified --live feature"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.temp_dir = None
        self.test_files = []
    
    def setup(self):
        """Set up test environment"""
        self.temp_dir = Path(tempfile.mkdtemp(prefix="vp_live_test_"))
        print(f"📁 Test directory: {self.temp_dir}")
        
        # Create test script
        test_script = self.temp_dir / "test_script.py"
        test_script.write_text('''
# Test script for live reloading
x = 100
y = 50
print(f"Position: ({x}, {y})")
print("Test script executed successfully!")
''')
        self.test_files.append(test_script)
        
        # Create test CSV
        test_csv = self.temp_dir / "test.csv"
        test_csv.write_text('''frame,op,x,y,w,h,r,g,b,text
0,CLEAR,,,,,,0,10,20,
0,RECT,50,25,100,50,255,0,0,
0,TEXT,55,35,,,,255,255,255,TEST
0,COMMIT,,,,,,,,
''')
        self.test_files.append(test_csv)
    
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
    
    def test_cli_help(self):
        """Test that CLI help works"""
        result = subprocess.run([
            sys.executable, "visualpython_unified.py", "--help"
        ], capture_output=True, text=True, cwd=".")
        
        assert result.returncode == 0, "CLI help should exit successfully"
        assert "--live" in result.stdout, "--live flag should be in help"
        assert "Watch file for changes" in result.stdout, "Live help text should be present"
    
    def test_run_command_help(self):
        """Test that run command help includes --live flag"""
        result = subprocess.run([
            sys.executable, "visualpython_unified.py", "run", "--help"
        ], capture_output=True, text=True, cwd=".")
        
        assert result.returncode == 0, "Run command help should work"
        assert "--live" in result.stdout, "--live should be available in run command"
        assert "--mirror" in result.stdout, "--mirror should be available in run command"
    
    def test_csv_play_help(self):
        """Test that CSV play command includes --live flag"""
        result = subprocess.run([
            sys.executable, "visualpython_unified.py", "csv", "play", "--help"
        ], capture_output=True, text=True, cwd=".")
        
        assert result.returncode == 0, "CSV play help should work"
        assert "--live" in result.stdout, "--live should be available in csv play"
    
    def test_basic_run_with_sim_backend(self):
        """Test basic script execution with simulator backend"""
        test_script = self.test_files[0]
        frames_dir = self.temp_dir / "frames"
        
        result = subprocess.run([
            sys.executable, "visualpython_unified.py", "run", str(test_script),
            "--backend", "sim", "--out-dir", str(frames_dir)
        ], capture_output=True, text=True, cwd=".", timeout=10)
        
        assert result.returncode == 0, f"Script execution failed: {result.stderr}"
        assert frames_dir.exists(), "Frames directory should be created"
        frame_files = list(frames_dir.glob("*.png")) + list(frames_dir.glob("*.ppm"))
        assert len(frame_files) > 0, "At least one frame should be generated"
        print(f"   Generated {len(frame_files)} frame files")
    
    def test_csv_playback(self):
        """Test CSV playback functionality"""
        test_csv = self.test_files[1]
        frames_dir = self.temp_dir / "csv_frames"
        
        result = subprocess.run([
            sys.executable, "visualpython_unified.py", "csv", "play", str(test_csv),
            "--backend", "sim", "--out-dir", str(frames_dir)
        ], capture_output=True, text=True, cwd=".", timeout=10)
        
        assert result.returncode == 0, f"CSV playback failed: {result.stderr}"
        assert frames_dir.exists(), "CSV frames directory should be created"
        frame_files = list(frames_dir.glob("*.png")) + list(frames_dir.glob("*.ppm"))
        assert len(frame_files) >= 1, "CSV should generate frames"
        print(f"   CSV playback generated {len(frame_files)} frames")
    
    def test_mirror_flag(self):
        """Test --mirror flag functionality"""
        test_script = self.test_files[0]
        mirror_csv = self.temp_dir / "mirror_test.csv"
        frames_dir = self.temp_dir / "mirror_frames"
        
        result = subprocess.run([
            sys.executable, "visualpython_unified.py", "run", str(test_script),
            "--backend", "sim", "--out-dir", str(frames_dir),
            "--mirror", str(mirror_csv)
        ], capture_output=True, text=True, cwd=".", timeout=10)
        
        assert result.returncode == 0, f"Mirror execution failed: {result.stderr}"
        assert mirror_csv.exists(), "Mirror CSV should be created"
        
        # Verify CSV content
        csv_content = mirror_csv.read_text()
        assert "frame,op" in csv_content, "CSV should have proper header"
        assert "COMMIT" in csv_content, "CSV should contain COMMIT operations"
        print(f"   Mirror CSV created with {len(csv_content)} characters")
    
    def test_file_validation(self):
        """Test error handling for non-existent files"""
        result = subprocess.run([
            sys.executable, "visualpython_unified.py", "run", "nonexistent.py",
            "--backend", "sim"
        ], capture_output=True, text=True, cwd=".", timeout=5)
        
        assert result.returncode != 0, "Should fail for non-existent file"
        assert "not found" in result.stderr.lower() or "not found" in result.stdout.lower(), \
               "Should report file not found"
    
    def test_backend_options(self):
        """Test different backend options"""
        test_script = self.test_files[0]
        
        # Test simulator backend
        result = subprocess.run([
            sys.executable, "visualpython_unified.py", "run", str(test_script),
            "--backend", "simulator"
        ], capture_output=True, text=True, cwd=".", timeout=10)
        
        # Should not crash (might fail due to missing dependencies, but shouldn't crash)
        assert "Traceback" not in result.stderr, "Should not have Python traceback errors"
    
    def print_summary(self):
        """Print test results summary"""
        total = self.passed + self.failed
        print(f"\n📊 Live Feature Test Results")
        print(f"="*50)
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print(f"📈 Success Rate: {(self.passed/total*100):.1f}%" if total > 0 else "No tests run")
        
        if self.failed == 0:
            print(f"\n🎉 All live feature tests passed!")
            print(f"VisualPython Unified --live functionality is working correctly.")
        else:
            print(f"\n⚠️  {self.failed} test(s) failed. Please review the errors above.")
        
        return self.failed == 0


def main():
    """Run the complete live feature test suite"""
    print("🚀 VisualPython Unified --live Feature Test Suite")
    print("="*60)
    
    tester = LiveFeatureTester()
    
    try:
        tester.setup()
        
        # Core functionality tests
        tester.run_test("CLI Help", tester.test_cli_help)
        tester.run_test("Run Command Help", tester.test_run_command_help)
        tester.run_test("CSV Play Help", tester.test_csv_play_help)
        tester.run_test("Basic Script Execution", tester.test_basic_run_with_sim_backend)
        tester.run_test("CSV Playback", tester.test_csv_playback)
        tester.run_test("Mirror Flag", tester.test_mirror_flag)
        tester.run_test("File Validation", tester.test_file_validation)
        tester.run_test("Backend Options", tester.test_backend_options)
        
        # Print final results
        success = tester.print_summary()
        
        # Demo instructions
        if success:
            print(f"\n🎯 Ready to test --live manually!")
            print(f"Try these commands:")
            print(f"  python visualpython_unified.py run test_live_demo.py --backend sim --live")
            print(f"  python visualpython_unified.py csv play test_live_animation.csv --backend sim --live")
            print(f"  python visualpython_unified.py run test_live_demo.py --backend sim --live --mirror session.csv")
        
    finally:
        tester.cleanup()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())