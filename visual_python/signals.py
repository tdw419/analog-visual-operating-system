"""
Analog Signal Export System

This module converts VisualPython execution into analog signal data
that can be exported as CSV files or used to drive hardware systems.

The revolutionary aspect: Python execution becomes analog signals
that can drive LEDs, displays, or other hardware devices.
"""

import csv
import time
import json
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SignalData:
    """Represents a single analog signal data point"""
    timestamp: float
    signal_type: str  # 'digital', 'analog', 'text', 'color'
    channel: int      # Pin/channel number
    value: Union[int, float, str]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            'timestamp': self.timestamp,
            'signal_type': self.signal_type,
            'channel': self.channel,
            'value': self.value,
            'metadata': self.metadata
        }
    
    def to_csv_row(self) -> List[str]:
        """Convert to CSV row format"""
        metadata_str = json.dumps(self.metadata) if self.metadata else ''
        return [
            str(self.timestamp),
            self.signal_type,
            str(self.channel),
            str(self.value),
            metadata_str
        ]


class AnalogSignalExporter:
    """
    Converts Python execution results into analog signal data
    
    This enables the revolutionary capability of turning code execution
    into hardware control signals.
    """
    
    def __init__(self):
        self.signal_data: List[SignalData] = []
        self.channel_mapping = self._create_default_channel_mapping()
        self.signal_count = 0
        self.start_time = time.time()
        
        # Export settings
        self.export_settings = {
            'include_metadata': True,
            'time_format': 'relative',  # 'relative' or 'absolute'
            'signal_resolution': 1000,  # Signals per second
            'auto_export': False,
            'max_signals': 10000
        }
    
    def _create_default_channel_mapping(self) -> Dict[str, int]:
        """Create default mapping of signal types to hardware channels"""
        return {
            # Variable signals - Arduino analog pins
            'variable_int': 1,
            'variable_float': 2,
            'variable_string': 3,
            
            # Output signals - Digital pins
            'output_text': 13,  # LED pin
            'print_statement': 12,
            'loop_iteration': 11,
            
            # System signals - PWM pins
            'execution_start': 9,
            'execution_end': 10,
            'error_signal': 8,
            
            # Visual signals - Analog pins
            'bar_width': 4,
            'color_red': 5,
            'color_green': 6,
            'color_blue': 7
        }
    
    def add_execution_data(self, execution_result):
        """
        Convert execution result to analog signals
        
        Args:
            execution_result: ExecutionResult from VisualPython engine
        """
        current_time = time.time() - self.start_time
        
        # Execution start signal
        self._add_signal(
            'digital',
            self.channel_mapping['execution_start'],
            1,  # HIGH
            current_time,
            metadata={'execution_time_ms': execution_result.execution_time_ms}
        )
        
        # Process visual elements
        for element in execution_result.visual_elements:
            self._process_visual_element(element, current_time)
        
        # Variable signals
        for name, value in execution_result.variables.items():
            self._process_variable(name, value, current_time)
        
        # Execution end signal
        self._add_signal(
            'digital',
            self.channel_mapping['execution_end'],
            1,  # HIGH
            current_time + 0.001,  # Slight delay
            metadata={'success': execution_result.success}
        )
        
        # Error signal if execution failed
        if not execution_result.success:
            self._add_signal(
                'digital',
                self.channel_mapping['error_signal'],
                1,  # HIGH
                current_time + 0.002,
                metadata={'error': execution_result.error_message}
            )
    
    def _process_visual_element(self, element, base_time: float):
        """Convert visual element to analog signals"""
        element_time = base_time + (element.timestamp - self.start_time)
        
        if element.element_type == 'variable':
            # Variable display triggers LED
            self._add_signal(
                'digital',
                self.channel_mapping['variable_string'],
                1,  # HIGH
                element_time,
                metadata={
                    'variable_name': element.metadata.get('variable_name'),
                    'variable_type': element.metadata.get('variable_type')
                }
            )
            
            # Bar width as analog signal
            if 'bar_width' in element.metadata:
                bar_value = min(element.metadata['bar_width'], 255)
                self._add_signal(
                    'analog',
                    self.channel_mapping['bar_width'],
                    bar_value,
                    element_time,
                    metadata={'original_width': element.metadata['bar_width']}
                )
        
        elif element.element_type == 'output':
            # Print statement triggers pulse
            self._add_signal(
                'digital',
                self.channel_mapping['print_statement'],
                1,  # HIGH
                element_time,
                metadata={'output_text': element.content}
            )
            
            # Convert text length to analog signal
            text_length = min(len(element.content), 255)
            self._add_signal(
                'analog',
                self.channel_mapping['output_text'],
                text_length,
                element_time + 0.001
            )
        
        elif element.element_type == 'loop_iteration':
            # Loop iteration pulse
            self._add_signal(
                'digital',
                self.channel_mapping['loop_iteration'],
                1,  # HIGH
                element_time,
                metadata={'loop_info': element.content}
            )
        
        # Color signals from element color
        self._process_color_signals(element.color, element_time)
    
    def _process_variable(self, name: str, value: Any, base_time: float):
        """Convert variable to analog signals"""
        if isinstance(value, (int, float)):
            # Numeric variables become analog signals
            channel = self.channel_mapping.get('variable_int', 1)
            
            # Scale value to 0-255 range
            if isinstance(value, float):
                # Handle float values
                scaled_value = min(abs(value) * 10, 255)
                channel = self.channel_mapping.get('variable_float', 2)
            else:
                # Handle integer values
                scaled_value = min(abs(value), 255)
            
            self._add_signal(
                'analog',
                channel,
                int(scaled_value),
                base_time,
                metadata={
                    'variable_name': name,
                    'original_value': value,
                    'value_type': type(value).__name__
                }
            )
        
        elif isinstance(value, str):
            # String variables become text signals
            self._add_signal(
                'text',
                self.channel_mapping.get('variable_string', 3),
                value,
                base_time,
                metadata={'variable_name': name}
            )
    
    def _process_color_signals(self, color_hex: str, signal_time: float):
        """Convert hex color to RGB analog signals"""
        try:
            # Parse hex color
            if color_hex.startswith('#'):
                color_hex = color_hex[1:]
            
            if len(color_hex) == 6:
                r = int(color_hex[0:2], 16)
                g = int(color_hex[2:4], 16)
                b = int(color_hex[4:6], 16)
                
                # Send RGB as analog signals
                self._add_signal('analog', self.channel_mapping['color_red'], r, signal_time)
                self._add_signal('analog', self.channel_mapping['color_green'], g, signal_time + 0.001)
                self._add_signal('analog', self.channel_mapping['color_blue'], b, signal_time + 0.002)
        
        except Exception:
            # Ignore color parsing errors
            pass
    
    def _add_signal(self, signal_type: str, channel: int, value: Any, 
                   timestamp: float, metadata: Dict[str, Any] = None):
        """Add a signal data point"""
        signal = SignalData(
            timestamp=timestamp,
            signal_type=signal_type,
            channel=channel,
            value=value,
            metadata=metadata or {}
        )
        
        self.signal_data.append(signal)
        self.signal_count += 1
        
        # Auto-cleanup if too many signals
        if len(self.signal_data) > self.export_settings['max_signals']:
            self.signal_data = self.signal_data[-self.export_settings['max_signals']//2:]
    
    def export_csv(self, filename: str = None) -> str:
        """
        Export signals as CSV file
        
        Args:
            filename: Output filename (auto-generated if None)
            
        Returns:
            str: Path to exported file or CSV content
        """
        if not filename:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"visual_python_signals_{timestamp}.csv"
        
        filepath = Path(filename)
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Header
            header = ['timestamp', 'signal_type', 'channel', 'value']
            if self.export_settings['include_metadata']:
                header.append('metadata')
            writer.writerow(header)
            
            # Data rows
            for signal in self.signal_data:
                row = signal.to_csv_row()
                if not self.export_settings['include_metadata']:
                    row = row[:-1]  # Remove metadata column
                writer.writerow(row)
        
        print(f"Exported {len(self.signal_data)} signals to {filepath}")
        return str(filepath)
    
    def export_json(self, filename: str = None) -> str:
        """Export signals as JSON file"""
        if not filename:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"visual_python_signals_{timestamp}.json"
        
        filepath = Path(filename)
        
        export_data = {
            'export_timestamp': time.time(),
            'signal_count': len(self.signal_data),
            'channel_mapping': self.channel_mapping,
            'export_settings': self.export_settings,
            'signals': [signal.to_dict() for signal in self.signal_data]
        }
        
        with open(filepath, 'w', encoding='utf-8') as jsonfile:
            json.dump(export_data, jsonfile, indent=2)
        
        print(f"Exported {len(self.signal_data)} signals to {filepath}")
        return str(filepath)
    
    def export_arduino_code(self, filename: str = None) -> str:
        """
        Export as Arduino code that can replay the signals
        
        Args:
            filename: Output filename
            
        Returns:
            str: Path to exported Arduino file
        """
        if not filename:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"visual_python_replay_{timestamp}.ino"
        
        filepath = Path(filename)
        
        # Generate Arduino code
        arduino_code = self._generate_arduino_code()
        
        with open(filepath, 'w', encoding='utf-8') as arduino_file:
            arduino_file.write(arduino_code)
        
        print(f"Exported Arduino replay code to {filepath}")
        return str(filepath)
    
    def _generate_arduino_code(self) -> str:
        """Generate Arduino code to replay signals"""
        code = '''// VisualPython Signal Replay
// Generated automatically from Python execution

void setup() {
  Serial.begin(9600);
  
  // Setup pins
'''
        
        # Setup pin modes
        used_pins = set()
        for signal in self.signal_data:
            if signal.signal_type in ['digital', 'analog']:
                used_pins.add(signal.channel)
        
        for pin in sorted(used_pins):
            code += f"  pinMode({pin}, OUTPUT);\n"
        
        code += '''
  Serial.println("VisualPython Signal Replay Started");
}

void loop() {
  // Replay signals
'''
        
        # Generate signal replay code
        last_time = 0
        for signal in self.signal_data[:100]:  # Limit for Arduino memory
            delay_ms = int((signal.timestamp - last_time) * 1000)
            
            if delay_ms > 0:
                code += f"  delay({delay_ms});\n"
            
            if signal.signal_type == 'digital':
                value = 'HIGH' if signal.value else 'LOW'
                code += f"  digitalWrite({signal.channel}, {value});\n"
            
            elif signal.signal_type == 'analog':
                code += f"  analogWrite({signal.channel}, {int(signal.value)});\n"
            
            last_time = signal.timestamp
        
        code += '''
  // Loop complete, wait before repeating
  delay(2000);
}
'''
        
        return code
    
    def get_signal_statistics(self) -> Dict[str, Any]:
        """Get statistics about exported signals"""
        if not self.signal_data:
            return {'total_signals': 0}
        
        # Count by type
        type_counts = {}
        channel_counts = {}
        
        for signal in self.signal_data:
            type_counts[signal.signal_type] = type_counts.get(signal.signal_type, 0) + 1
            channel_counts[signal.channel] = channel_counts.get(signal.channel, 0) + 1
        
        # Time range
        times = [s.timestamp for s in self.signal_data]
        
        return {
            'total_signals': len(self.signal_data),
            'signal_types': type_counts,
            'channels_used': channel_counts,
            'time_range': {
                'start': min(times),
                'end': max(times),
                'duration': max(times) - min(times)
            },
            'average_signal_rate': len(self.signal_data) / max(1, max(times) - min(times)),
            'channel_mapping': self.channel_mapping
        }
    
    def clear_signals(self):
        """Clear all stored signals"""
        self.signal_data.clear()
        self.signal_count = 0
        self.start_time = time.time()
    
    def set_channel_mapping(self, mapping: Dict[str, int]):
        """Update channel mapping for hardware control"""
        self.channel_mapping.update(mapping)
    
    def configure_export(self, **settings):
        """Configure export settings"""
        self.export_settings.update(settings)


class HardwareSignalController:
    """
    Controller for sending signals directly to hardware
    
    This enables real-time hardware control from Python execution
    """
    
    def __init__(self, connection_type='serial', **kwargs):
        self.connection_type = connection_type
        self.connection = None
        self.kwargs = kwargs
        
        if connection_type == 'serial':
            self._setup_serial_connection()
    
    def _setup_serial_connection(self):
        """Setup serial connection for Arduino/hardware control"""
        try:
            import serial
            
            port = self.kwargs.get('port', 'COM3')  # Default Windows
            baudrate = self.kwargs.get('baudrate', 9600)
            
            self.connection = serial.Serial(port, baudrate, timeout=1)
            print(f"Connected to hardware on {port}")
            
        except ImportError:
            print("PySerial not available - install with: pip install pyserial")
        except Exception as e:
            print(f"Hardware connection failed: {e}")
    
    def send_signal(self, signal: SignalData):
        """Send signal directly to hardware"""
        if not self.connection:
            return
        
        try:
            if signal.signal_type == 'digital':
                command = f"D{signal.channel},{int(signal.value)}\n"
            elif signal.signal_type == 'analog':
                command = f"A{signal.channel},{int(signal.value)}\n"
            else:
                return  # Unsupported signal type
            
            self.connection.write(command.encode())
            
        except Exception as e:
            print(f"Failed to send signal: {e}")
    
    def send_signal_batch(self, signals: List[SignalData]):
        """Send multiple signals to hardware"""
        for signal in signals:
            self.send_signal(signal)
    
    def cleanup(self):
        """Clean up hardware connection"""
        if self.connection:
            try:
                self.connection.close()
            except:
                pass


# Convenience functions for quick signal export
def quick_export_csv(execution_result, filename: str = None) -> str:
    """Quick CSV export of execution result"""
    exporter = AnalogSignalExporter()
    exporter.add_execution_data(execution_result)
    return exporter.export_csv(filename)

def quick_export_arduino(execution_result, filename: str = None) -> str:
    """Quick Arduino code export of execution result"""
    exporter = AnalogSignalExporter()
    exporter.add_execution_data(execution_result)
    return exporter.export_arduino_code(filename)


if __name__ == "__main__":
    # Test signal export
    print("Testing VisualPython signal export...")
    
    # Create test execution result
    from .core import ExecutionResult, VisualElement
    
    test_elements = [
        VisualElement('variable', 'x = 42', 50, 50, metadata={'variable_name': 'x', 'variable_value': 42}),
        VisualElement('output', 'Hello World!', 400, 50),
        VisualElement('variable', 'y = 84', 50, 75, metadata={'bar_width': 84})
    ]
    
    test_result = ExecutionResult(
        success=True,
        execution_time_ms=15.2,
        elements_created=3,
        variables_tracked=2,
        output_lines=1,
        visual_elements=test_elements,
        variables={'x': 42, 'y': 84}
    )
    
    # Test export
    exporter = AnalogSignalExporter()
    exporter.add_execution_data(test_result)
    
    print(f"Generated {len(exporter.signal_data)} signals")
    print("Signal statistics:", exporter.get_signal_statistics())
    
    # Export to CSV
    csv_file = exporter.export_csv("test_signals.csv")
    print(f"Exported to: {csv_file}")
    
    # Export Arduino code
    arduino_file = exporter.export_arduino_code("test_replay.ino")
    print(f"Arduino code: {arduino_file}")