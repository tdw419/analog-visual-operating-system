#!/usr/bin/env python3
"""
UVIR Hardware Bridge Integration Test

This script tests the complete UVIR system including:
- Server health and serial communication
- Hardware control via natural language
- UVIR operation validation
- NDJSON logging and replay functionality
- Frontend integration

Usage:
    python test_hardware_bridge.py
    
Prerequisites:
    1. Arduino with uploaded arduino_pwm_uvir.ino sketch
    2. UVIR server running (python uvir_server.py)
    3. Environment variables set (SERIAL_PORT if using real hardware)
"""

import asyncio
import json
import time
import requests
import os
from pathlib import Path
from typing import Dict, Any, List

# Configuration
SERVER_URL = "http://localhost:8844"
TEST_TIMEOUT = 30  # seconds

class UVIRTester:
    def __init__(self):
        self.test_results = []
        self.session = requests.Session()
    
    def log_test(self, name: str, success: bool, message: str = ""):
        """Log a test result"""
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status} {name}")
        if message:
            print(f"    {message}")
        
        self.test_results.append({
            "name": name,
            "success": success,
            "message": message,
            "timestamp": time.time()
        })
    
    def test_server_health(self) -> bool:
        """Test server health and configuration"""
        try:
            response = self.session.get(f"{SERVER_URL}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.log_test("Server Health", True, f"Version {data['version']}, Mock: {data['mock_mode']}")
                
                # Check hardware connection
                if data.get('serial_connected'):
                    self.log_test("Hardware Connection", True, "Arduino connected")
                else:
                    self.log_test("Hardware Connection", False, "No Arduino (simulation mode)")
                
                return True
            else:
                self.log_test("Server Health", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Server Health", False, str(e))
            return False
    
    def test_manual_hardware_control(self) -> bool:
        """Test direct hardware control via tool endpoint"""
        try:
            tool_call = {
                "name": "serial_pwm",
                "args": {"pin": 13, "value": 200},
                "run_id": f"test_{int(time.time())}"
            }
            
            response = self.session.post(
                f"{SERVER_URL}/tools/execute",
                json=tool_call,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    self.log_test("Manual Hardware Control", True, result.get("result", {}).get("message", ""))
                    return True
                else:
                    self.log_test("Manual Hardware Control", False, result.get("result", {}).get("error", "Unknown error"))
                    return False
            else:
                self.log_test("Manual Hardware Control", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Manual Hardware Control", False, str(e))
            return False
    
    async def test_natural_language_hardware(self) -> bool:
        """Test hardware control via natural language streaming"""
        try:
            import aiohttp
            
            prompt = "Set LED on pin 13 to value 128 and confirm the action"
            request_data = {
                "prompt": prompt,
                "want_ir": True,
                "temperature": 0.7,
                "max_tokens": 100
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{SERVER_URL}/stream",
                    json=request_data,
                    timeout=aiohttp.ClientTimeout(total=TEST_TIMEOUT)
                ) as response:
                    
                    if response.status != 200:
                        self.log_test("Natural Language Hardware", False, f"HTTP {response.status}")
                        return False
                    
                    events = []
                    tool_call_found = False
                    tool_result_found = False
                    
                    async for line in response.content:
                        line = line.decode().strip()
                        if line.startswith("data: "):
                            try:
                                event = json.loads(line[6:])
                                events.append(event)
                                
                                if event.get("type") == "tool_call":
                                    tool_call_found = True
                                elif event.get("type") == "tool_result":
                                    tool_result_found = True
                                    if event.get("ok"):
                                        self.log_test("Natural Language Hardware", True, "LED controlled via natural language")
                                        return True
                                elif event.get("type") == "done":
                                    break
                            except json.JSONDecodeError:
                                continue
                    
                    if not tool_call_found:
                        self.log_test("Natural Language Hardware", False, "No tool call generated")
                        return False
                    elif not tool_result_found:
                        self.log_test("Natural Language Hardware", False, "No tool result received")
                        return False
                    
        except Exception as e:
            self.log_test("Natural Language Hardware", False, str(e))
            return False
        
        return False
    
    def test_uvir_operations(self) -> bool:
        """Test UVIR operation validation"""
        try:
            # Import validation function
            import sys
            sys.path.append(str(Path(__file__).parent))
            from uvir_server import validate_uvir_ops
            
            # Test valid operations
            valid_ops = [
                {"op": "TEXT", "x": 100, "y": 50, "text": "Test", "color": "#00FF00"},
                {"op": "BAR", "x": 50, "y": 100, "len": 200, "label": "Progress", "value": 0.75},
                {"op": "RECT", "x": 10, "y": 10, "w": 100, "h": 60, "fill": False},
                {"op": "LINK", "x1": 50, "y1": 50, "x2": 150, "y2": 150, "arrow": True},
                {"op": "TICK", "t": 5}
            ]
            
            validated = validate_uvir_ops(valid_ops)
            if len(validated) == len(valid_ops):
                self.log_test("UVIR Operation Validation", True, f"All {len(validated)} operations validated")
                return True
            else:
                self.log_test("UVIR Operation Validation", False, f"Only {len(validated)}/{len(valid_ops)} operations passed")
                return False
        except Exception as e:
            self.log_test("UVIR Operation Validation", False, str(e))
            return False
    
    def test_logging_functionality(self) -> bool:
        """Test NDJSON logging and replay"""
        try:
            # Check if logs directory exists
            logs_dir = Path("logs")
            if not logs_dir.exists():
                self.log_test("Logging Functionality", False, "Logs directory not found")
                return False
            
            # Get available logs
            response = self.session.get(f"{SERVER_URL}/logs", timeout=5)
            if response.status_code == 200:
                logs_data = response.json()
                log_files = logs_data.get("logs", [])
                
                if log_files:
                    self.log_test("Logging Functionality", True, f"Found {len(log_files)} log files")
                    
                    # Test replay functionality with the first log file
                    if log_files:
                        return self.test_replay_functionality(log_files[0])
                else:
                    self.log_test("Logging Functionality", True, "No log files yet (system ready for logging)")
                    return True
            else:
                self.log_test("Logging Functionality", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Logging Functionality", False, str(e))
            return False
    
    def test_replay_functionality(self, run_id: str) -> bool:
        """Test session replay"""
        try:
            replay_data = {"run_id": run_id, "speed": 2.0}
            response = self.session.post(
                f"{SERVER_URL}/replay",
                json=replay_data,
                timeout=10,
                stream=True
            )
            
            if response.status_code == 200:
                events_count = 0
                for line in response.iter_lines():
                    if line and line.startswith(b"data: "):
                        events_count += 1
                        if events_count >= 3:  # Sample a few events
                            break
                
                self.log_test("Replay Functionality", True, f"Replayed {events_count} events")
                return True
            else:
                self.log_test("Replay Functionality", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Replay Functionality", False, str(e))
            return False
    
    def test_frontend_integration(self) -> bool:
        """Test frontend file accessibility"""
        try:
            frontend_file = Path("uvir_frontend.html")
            if frontend_file.exists():
                content = frontend_file.read_text()
                required_elements = ["UVIRRenderer", "testHardware", "generateUVIR"]
                
                missing = [elem for elem in required_elements if elem not in content]
                if not missing:
                    self.log_test("Frontend Integration", True, "All required elements found")
                    return True
                else:
                    self.log_test("Frontend Integration", False, f"Missing: {missing}")
                    return False
            else:
                self.log_test("Frontend Integration", False, "uvir_frontend.html not found")
                return False
        except Exception as e:
            self.log_test("Frontend Integration", False, str(e))
            return False
    
    async def run_all_tests(self):
        """Run the complete test suite"""
        print("🚀 UVIR Hardware Bridge Integration Test")
        print("=" * 50)
        
        # Synchronous tests
        tests = [
            self.test_server_health,
            self.test_manual_hardware_control,
            self.test_uvir_operations,
            self.test_logging_functionality,
            self.test_frontend_integration
        ]
        
        for test in tests:
            test()
        
        # Asynchronous test
        await self.test_natural_language_hardware()
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 Test Results Summary")
        print("=" * 50)
        
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        if passed == total:
            print(f"🎉 All tests passed! ({passed}/{total})")
            print("\n✅ Your UVIR Hardware Bridge is fully functional!")
            print("\nNext steps:")
            print("1. Upload arduino_pwm_uvir.ino to your Arduino")
            print("2. Set SERIAL_PORT environment variable")
            print("3. Try: 'Set LED on pin 13 to value 200'")
            print("4. Open uvir_frontend.html and test the interface")
        else:
            print(f"❌ {total - passed} tests failed ({passed}/{total} passed)")
            print("\n🔧 Failed tests:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  • {result['name']}: {result['message']}")
        
        return passed == total

async def main():
    """Main test runner"""
    tester = UVIRTester()
    success = await tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n\nTest runner failed: {e}")
        exit(1)