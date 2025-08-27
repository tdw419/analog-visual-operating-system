# hardware_hooks.py
"""
Hardware integration hooks for the Analog Code Workbench.
This module demonstrates how to connect CSV operations to real analog hardware.

Example usage in your CSV player loop:
    from hardware_hooks import AnalogHardware
    hardware = AnalogHardware()
    
    for operation in csv_operations:
        hardware.execute_operation(operation)
"""

import time
import threading
from typing import Dict, List, Any, Optional

class MockDAC:
    """Mock DAC for testing when real hardware isn't available"""
    def __init__(self, channels=8):
        self.channels = {i: 0 for i in range(channels)}
        self.max_value = 255
    
    def write(self, channel: int, value: int):
        if 0 <= channel < len(self.channels):
            self.channels[channel] = max(0, min(value, self.max_value))
            print(f"DAC[{channel}] = {self.channels[channel]} ({value/255*5:.2f}V)")
        else:
            print(f"Warning: DAC channel {channel} out of range")

class MockADC:
    """Mock ADC for testing when real hardware isn't available"""
    def __init__(self, channels=8):
        self.channels = {i: 0 for i in range(channels)}
        self.noise_level = 5  # Add some noise for realism
    
    def read(self, channel: int) -> int:
        if 0 <= channel < len(self.channels):
            # Add some noise to make it realistic
            import random
            base_value = self.channels[channel]
            noise = random.randint(-self.noise_level, self.noise_level)
            value = max(0, min(255, base_value + noise))
            print(f"ADC[{channel}] = {value} ({value/255*5:.2f}V)")
            return value
        else:
            print(f"Warning: ADC channel {channel} out of range")
            return 0
    
    def set_channel_value(self, channel: int, value: int):
        """Set a channel value for testing"""
        if 0 <= channel < len(self.channels):
            self.channels[channel] = max(0, min(255, value))

class AnalogHardware:
    """
    Hardware abstraction layer for analog operations.
    Replace mock components with real hardware interfaces.
    """
    
    def __init__(self, use_real_hardware=False):
        self.use_real_hardware = use_real_hardware
        
        if use_real_hardware:
            # Initialize real hardware here
            # Example: self.dac = RealDACInterface()
            # Example: self.adc = RealADCInterface()
            print("Real hardware mode not implemented yet")
            self.dac = MockDAC()
            self.adc = MockADC()
        else:
            # Use mock hardware for testing
            self.dac = MockDAC()
            self.adc = MockADC()
        
        self.sync_markers = []
        self.operation_log = []
    
    def execute_operation(self, operation: str) -> Optional[Any]:
        """
        Execute a single CSV operation on hardware.
        Returns any result value (e.g., from ADC_READ).
        """
        if not operation.strip():
            return None
        
        parts = operation.strip().split(',')
        if not parts:
            return None
        
        op = parts[0].upper()
        self.operation_log.append(operation)
        
        try:
            if op == "DAC_WRITE" and len(parts) >= 3:
                channel = int(parts[1])
                value = int(parts[2])
                self.dac.write(channel, value)
                return None
            
            elif op == "ADC_READ" and len(parts) >= 2:
                channel = int(parts[1])
                value = self.adc.read(channel)
                return value
            
            elif op == "SLEEP" and len(parts) >= 2:
                ms = int(parts[1])
                time.sleep(ms / 1000.0)  # Convert ms to seconds
                return None
            
            elif op == "SYNC_ROW" and len(parts) >= 2:
                row_index = int(parts[1])
                self.sync_markers.append(('ROW', row_index, time.time()))
                print(f"SYNC_ROW {row_index}")
                return None
            
            elif op == "SYNC_PAGE" and len(parts) >= 2:
                page_index = int(parts[1])
                self.sync_markers.append(('PAGE', page_index, time.time()))
                print(f"SYNC_PAGE {page_index}")
                return None
            
            elif op == "COMMIT":
                # Frame boundary - might trigger hardware sync
                print("COMMIT - frame boundary")
                return None
            
            elif op in ["RECT", "TEXT", "LINE"]:
                # Visual operations - might be ignored by pure hardware
                # or converted to display operations
                print(f"Visual operation: {operation}")
                return None
            
            else:
                print(f"Unknown operation: {operation}")
                return None
                
        except (ValueError, IndexError) as e:
            print(f"Error executing operation '{operation}': {e}")
            return None
    
    def execute_csv_program(self, csv_content: str) -> List[Any]:
        """
        Execute an entire CSV program on hardware.
        Returns list of any result values.
        """
        results = []
        
        for line in csv_content.strip().split('\n'):
            if line.strip() and not line.strip().startswith('#'):
                result = self.execute_operation(line)
                if result is not None:
                    results.append(result)
        
        return results
    
    def get_hardware_status(self) -> Dict[str, Any]:
        """Get current hardware status"""
        return {
            'dac_channels': getattr(self.dac, 'channels', {}),
            'adc_channels': getattr(self.adc, 'channels', {}),
            'sync_markers': self.sync_markers,
            'operations_executed': len(self.operation_log),
            'last_operation': self.operation_log[-1] if self.operation_log else None
        }
    
    def reset(self):
        """Reset hardware state"""
        if hasattr(self.dac, 'channels'):
            for channel in self.dac.channels:
                self.dac.channels[channel] = 0
        
        self.sync_markers.clear()
        self.operation_log.clear()
        print("Hardware reset")

# Integration example for CSV player
def csv_player_with_hardware(csv_content: str, use_real_hardware=False):
    """
    Example CSV player that executes operations on hardware.
    This shows how to integrate hardware hooks into your player loop.
    """
    hardware = AnalogHardware(use_real_hardware)
    
    print("Starting CSV execution on hardware...")
    print("=" * 50)
    
    try:
        results = hardware.execute_csv_program(csv_content)
        
        print("=" * 50)
        print("Execution complete!")
        print(f"Operations executed: {len(hardware.operation_log)}")
        print(f"Results collected: {len(results)}")
        
        if results:
            print("Results:", results)
        
        # Show final hardware status
        status = hardware.get_hardware_status()
        print("\nFinal hardware status:")
        for key, value in status.items():
            print(f"  {key}: {value}")
            
    except Exception as e:
        print(f"Execution error: {e}")
        import traceback
        traceback.print_exc()

# Example usage and testing
if __name__ == "__main__":
    # Test CSV program
    test_csv = """# Test program for hardware execution
DAC_WRITE,0,100
SLEEP,50
DAC_WRITE,1,200
ADC_READ,0
SYNC_ROW,1
DAC_WRITE,0,0
COMMIT"""
    
    print("Testing hardware hooks with mock hardware:")
    csv_player_with_hardware(test_csv, use_real_hardware=False)
    
    print("\n" + "=" * 60)
    print("Hardware hooks ready!")
    print("To use with real hardware:")
    print("1. Replace MockDAC/MockADC with real hardware interfaces")
    print("2. Set use_real_hardware=True") 
    print("3. Add your hardware initialization code")
    print("4. Integrate with your CSV player loop")