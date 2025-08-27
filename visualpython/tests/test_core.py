"""
Test suite for VisualPython core functionality.
"""

import unittest
import tempfile
import os
from unittest.mock import Mock, patch

from visualpython.core import VisualPythonEngine, VisualElement
from visualpython.signals import SignalData


class TestVisualPythonEngine(unittest.TestCase):
    """Test the core VisualPython engine."""
    
    def setUp(self):
        """Set up test engine with console backend."""
        self.engine = VisualPythonEngine(backend='console')
    
    def tearDown(self):
        """Clean up after tests."""
        self.engine.cleanup()
    
    def test_simple_variable_assignment(self):
        """Test basic variable assignment."""
        code = "x = 42"
        execution_time = self.engine.execute(code)
        
        self.assertGreater(execution_time, 0)
        self.assertIn('x', self.engine.variables)
        self.assertEqual(self.engine.variables['x'], 42)
        self.assertGreater(len(self.engine.operations), 0)
    
    def test_multiple_variables(self):
        """Test multiple variable assignments."""
        code = """
x = 100
y = 200
z = x + y
"""
        self.engine.execute(code)
        
        self.assertEqual(self.engine.variables['x'], 100)
        self.assertEqual(self.engine.variables['y'], 200)
        self.assertEqual(self.engine.variables['z'], 300)
    
    def test_print_statements(self):
        """Test print statement handling."""
        code = 'print("Hello, VisualPython!")'
        self.engine.execute(code)
        
        # Check that output operation was created
        output_ops = [op for op in self.engine.operations if op.element_type == 'output']
        self.assertGreater(len(output_ops), 0)
        self.assertEqual(output_ops[0].content, "Hello, VisualPython!")
    
    def test_for_loop_execution(self):
        """Test for loop processing."""
        code = """
for i in range(3):
    x = i * 10
    print(f"Value: {x}")
"""
        self.engine.execute(code)
        
        # Check loop variable
        self.assertIn('i', self.engine.variables)
        self.assertEqual(self.engine.variables['i'], 2)  # Last iteration value
        
        # Check that loop operations were created
        loop_ops = [op for op in self.engine.operations if 'loop' in op.element_type]
        self.assertGreater(len(loop_ops), 0)
    
    def test_if_statement_execution(self):
        """Test if statement processing."""
        code = """
x = 50
if x > 25:
    result = "large"
else:
    result = "small"
"""
        self.engine.execute(code)
        
        self.assertEqual(self.engine.variables['x'], 50)
        self.assertEqual(self.engine.variables['result'], "large")
        
        # Check condition operation
        if_ops = [op for op in self.engine.operations if op.element_type == 'if_condition']
        self.assertGreater(len(if_ops), 0)
    
    def test_math_operations(self):
        """Test mathematical operations."""
        code = """
a = 10
b = 5
add_result = a + b
sub_result = a - b
mul_result = a * b
div_result = a / b
"""
        self.engine.execute(code)
        
        self.assertEqual(self.engine.variables['add_result'], 15)
        self.assertEqual(self.engine.variables['sub_result'], 5)
        self.assertEqual(self.engine.variables['mul_result'], 50)
        self.assertEqual(self.engine.variables['div_result'], 2.0)
    
    def test_comparison_operations(self):
        """Test comparison operations."""
        code = """
x = 10
y = 20
is_greater = x > y
is_equal = x == 10
is_less_equal = x <= y
"""
        self.engine.execute(code)
        
        self.assertEqual(self.engine.variables['is_greater'], False)
        self.assertEqual(self.engine.variables['is_equal'], True)
        self.assertEqual(self.engine.variables['is_less_equal'], True)
    
    def test_f_string_support(self):
        """Test f-string formatting."""
        code = """
name = "VisualPython"
version = 2.0
message = f"Welcome to {name} v{version}!"
print(message)
"""
        self.engine.execute(code)
        
        expected_message = "Welcome to VisualPython v2.0!"
        self.assertEqual(self.engine.variables['message'], expected_message)
        
        # Check print output
        output_ops = [op for op in self.engine.operations if op.element_type == 'output']
        self.assertTrue(any(op.content == expected_message for op in output_ops))
    
    def test_signal_generation(self):
        """Test signal generation for hardware export."""
        code = """
led_brightness = 128
servo_angle = 90
print("Hardware control active")
"""
        self.engine.execute(code)
        
        # Check that signals were generated
        self.assertGreater(len(self.engine.signals), 0)
        
        # Verify signal content
        assign_signals = [s for s in self.engine.signals if s.operation == 'assign']
        self.assertGreater(len(assign_signals), 0)
        
        print_signals = [s for s in self.engine.signals if s.operation == 'print']
        self.assertGreater(len(print_signals), 0)
    
    def test_error_handling(self):
        """Test error handling for invalid code."""
        # Test syntax error
        code = "x = (invalid syntax"
        execution_time = self.engine.execute(code)
        
        # Should not crash, should return execution time
        self.assertGreater(execution_time, 0)
    
    def test_division_by_zero_handling(self):
        """Test division by zero handling."""
        code = """
x = 10
y = 0
result = x / y
"""
        self.engine.execute(code)
        
        # Should handle gracefully and return 0
        self.assertEqual(self.engine.variables['result'], 0)
    
    def test_while_loop_with_safety_limit(self):
        """Test while loop with safety iteration limit."""
        code = """
counter = 0
while counter < 5:
    counter = counter + 1
"""
        self.engine.execute(code)
        
        self.assertEqual(self.engine.variables['counter'], 5)
        
        # Check that loop operations were created
        loop_ops = [op for op in self.engine.operations if 'loop' in op.element_type]
        self.assertGreater(len(loop_ops), 0)
    
    def test_statistics_tracking(self):
        """Test execution statistics tracking."""
        code = "x = 42"
        self.engine.execute(code)
        
        stats = self.engine.get_statistics()
        
        self.assertEqual(stats['execution_count'], 1)
        self.assertGreater(stats['total_execution_time_ms'], 0)
        self.assertEqual(stats['variable_count'], 1)
        self.assertGreater(stats['operation_count'], 0)
        self.assertIn('x', stats['current_variables'])
    
    def test_visual_element_creation(self):
        """Test visual element creation."""
        code = """
x = 100
print("Test output")
for i in range(2):
    y = i
"""
        self.engine.execute(code)
        
        # Check different types of visual elements were created
        element_types = {op.element_type for op in self.engine.operations}
        
        self.assertIn('variable', element_types)
        self.assertIn('output', element_types)
        self.assertIn('loop_start', element_types)
    
    def test_timeline_os_integration(self):
        """Test Timeline OS keyframe integration."""
        # Timeline OS keyframes should be initialized
        self.assertGreater(len(self.engine.keyframes), 0)
        
        # Should have boot sequence keyframes
        boot_keyframes = [kf for kf in self.engine.keyframes if kf.get('type') == 'boot_message']
        self.assertGreater(len(boot_keyframes), 0)
        
        # Should have font system keyframe
        font_keyframes = [kf for kf in self.engine.keyframes if kf.get('type') == 'font_system']
        self.assertEqual(len(font_keyframes), 1)
        self.assertEqual(font_keyframes[0]['time'], 5.0)


class TestVisualElement(unittest.TestCase):
    """Test VisualElement data structure."""
    
    def test_visual_element_creation(self):
        """Test basic visual element creation."""
        element = VisualElement(
            element_type='variable',
            content='x = 42',
            x=100,
            y=50,
            color='#ffff00'
        )
        
        self.assertEqual(element.element_type, 'variable')
        self.assertEqual(element.content, 'x = 42')
        self.assertEqual(element.x, 100)
        self.assertEqual(element.y, 50)
        self.assertEqual(element.color, '#ffff00')
        self.assertIsInstance(element.metadata, dict)
    
    def test_visual_element_with_metadata(self):
        """Test visual element with metadata."""
        metadata = {'bar_width': 150, 'value': 75}
        
        element = VisualElement(
            element_type='variable_bar',
            content='',
            x=200,
            y=100,
            metadata=metadata
        )
        
        self.assertEqual(element.metadata['bar_width'], 150)
        self.assertEqual(element.metadata['value'], 75)


class TestSignalData(unittest.TestCase):
    """Test SignalData structure."""
    
    def test_signal_data_creation(self):
        """Test basic signal data creation."""
        signal = SignalData(
            timestamp=1234567890.0,
            operation='assign',
            x=100,
            y=50,
            r=255,
            g=128,
            b=0,
            variable='led_brightness',
            value=200
        )
        
        self.assertEqual(signal.operation, 'assign')
        self.assertEqual(signal.variable, 'led_brightness')
        self.assertEqual(signal.value, 200)
        self.assertEqual(signal.r, 255)
        self.assertEqual(signal.g, 128)
        self.assertEqual(signal.b, 0)
    
    def test_signal_to_dict(self):
        """Test signal conversion to dictionary."""
        signal = SignalData(
            timestamp=1234567890.0,
            operation='print',
            x=20,
            y=80,
            r=0,
            g=255,
            b=255,
            variable='output',
            value='Hello World'
        )
        
        signal_dict = signal.to_dict()
        
        self.assertEqual(signal_dict['operation'], 'print')
        self.assertEqual(signal_dict['variable'], 'output')
        self.assertEqual(signal_dict['value'], 'Hello World')
        self.assertIn('timestamp', signal_dict)


if __name__ == '__main__':
    unittest.main()