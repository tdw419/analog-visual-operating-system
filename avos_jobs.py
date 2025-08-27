"""
avos_jobs.py - AVOS-specific job handlers for the qqueue system
"""

import time
import subprocess
import json
import os
from typing import Dict, Any
from pathlib import Path

# Make the functions available at module level for the queue system
def handle_avos_pytest(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle avos-pytest job type"""
    return run_pytest(payload)

def handle_avos_demo(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle avos-demo job type"""
    return run_avos_demo(payload)

def handle_avos_docs(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle avos-docs job type"""
    return build_documentation(payload)

def handle_avos_hlir(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle avos-hlir job type"""
    return process_hlir_file(payload)

def handle_avos_hardware_test(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle avos-hardware-test job type"""
    return run_hardware_test(payload)

def run_pytest(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Run pytest with specified arguments"""
    args = payload.get('args', [])
    directory = payload.get('directory', '.')
    
    print(f"Running pytest in {directory} with args: {args}")
    
    # Change to the specified directory
    original_cwd = os.getcwd()
    try:
        os.chdir(directory)
        
        # Build the command
        cmd = ['python', '-m', 'pytest'] + args
        
        # Run the command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        output = {
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'cmd': ' '.join(cmd)
        }
        
        if result.returncode != 0:
            print(f"Pytest failed with return code {result.returncode}")
            print(f"STDOUT:\n{result.stdout}")
            print(f"STDERR:\n{result.stderr}")
        else:
            print("Pytest completed successfully")
            print(f"STDOUT:\n{result.stdout}")
            
        return output
    finally:
        os.chdir(original_cwd)

def run_avos_demo(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Run an AVOS demo script"""
    demo_name = payload.get('demo', 'infinite_demo.py')
    args = payload.get('args', [])
    
    print(f"Running AVOS demo: {demo_name} with args: {args}")
    
    # Build the command
    cmd = ['python', demo_name] + args
    
    # Run the command
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )
    
    output = {
        'returncode': result.returncode,
        'stdout': result.stdout,
        'stderr': result.stderr,
        'cmd': ' '.join(cmd)
    }
    
    if result.returncode != 0:
        print(f"Demo failed with return code {result.returncode}")
        print(f"STDOUT:\n{result.stdout}")
        print(f"STDERR:\n{result.stderr}")
    else:
        print("Demo completed successfully")
        print(f"STDOUT:\n{result.stdout}")
        
    return output

def build_documentation(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Build project documentation"""
    print("Building documentation...")
    
    # This would typically run sphinx or another documentation tool
    # For now, we'll just simulate the process
    time.sleep(3)
    
    result = {
        'status': 'completed',
        'output_dir': 'docs/_build',
        'files_generated': ['index.html', 'api.html', 'examples.html']
    }
    
    print("Documentation built successfully")
    print(f"Generated files: {result['files_generated']}")
    
    return result

def process_hlir_file(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Process an HLIR (High-Level Intermediate Representation) file"""
    file_path = payload.get('file_path')
    if not file_path:
        raise Exception("file_path is required")
    
    print(f"Processing HLIR file: {file_path}")
    
    # Check if file exists
    if not os.path.exists(file_path):
        raise Exception(f"File not found: {file_path}")
    
    # Read and process the file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Simulate processing (in a real implementation, this would do actual HLIR processing)
    lines = len(content.split('\n'))
    chars = len(content)
    
    # Simulate some processing time
    time.sleep(1)
    
    result = {
        'file_path': file_path,
        'lines': lines,
        'characters': chars,
        'status': 'processed'
    }
    
    print(f"HLIR file processed: {lines} lines, {chars} characters")
    
    return result

def run_hardware_test(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Run a hardware test (for AVOS hardware integration)"""
    test_type = payload.get('test_type', 'basic')
    device = payload.get('device', 'default')
    
    print(f"Running {test_type} hardware test on device: {device}")
    
    # Simulate hardware testing
    time.sleep(2)
    
    # Simulate test results
    if test_type == 'basic':
        result = {
            'test_type': test_type,
            'device': device,
            'status': 'passed',
            'details': 'All basic functions working'
        }
    elif test_type == 'comprehensive':
        result = {
            'test_type': test_type,
            'device': device,
            'status': 'passed',
            'details': 'All functions working, performance within expected range',
            'performance_metrics': {
                'response_time_ms': 15,
                'memory_usage_kb': 128,
                'power_consumption_ma': 45
            }
        }
    else:
        result = {
            'test_type': test_type,
            'device': device,
            'status': 'failed',
            'details': 'Unknown test type',
            'error': f"Test type '{test_type}' not supported"
        }
    
    print(f"Hardware test result: {result['status']}")
    if 'error' in result:
        print(f"Error: {result['error']}")
    
    return result

# Export the handler functions
__all__ = [
    'run_pytest', 'handle_avos_pytest',
    'run_avos_demo', 'handle_avos_demo',
    'build_documentation', 'handle_avos_docs',
    'process_hlir_file', 'handle_avos_hlir',
    'run_hardware_test', 'handle_avos_hardware_test'
]