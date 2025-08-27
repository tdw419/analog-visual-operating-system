#!/usr/bin/env python3
"""
workflow_runner.py - Run AVOS workflows using the qqueue system
"""

import yaml
import sys
import json
import argparse
from typing import Dict, Any

def load_workflow(file_path: str) -> Dict[str, Any]:
    """Load a workflow from a YAML file"""
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)

def enqueue_workflow_job(job_config: Dict[str, Any], section: str):
    """Enqueue a single job from the workflow"""
    import subprocess
    
    job_name = job_config.get('name', 'unnamed job')
    job_type = job_config.get('type')
    priority = job_config.get('priority', 1)
    delay = job_config.get('delay', 0)
    
    print(f"Enqueuing {job_name} ({job_type}) from {section} section...")
    
    if job_type == 'shell':
        command = job_config.get('command')
        if not command:
            print(f"  ❌ Error: Shell job missing 'command'")
            return
            
        cmd = [
            'python', 'qqueue.py', 'enqueue-shell',
            command,
            '--priority', str(priority)
        ]
        if delay > 0:
            cmd.extend(['--delay', str(delay)])
            
    elif job_type.startswith('avos-'):
        # For AVOS custom job types, we need to pass the payload as JSON
        payload = {k: v for k, v in job_config.items() 
                  if k not in ['name', 'type', 'priority', 'delay']}
        
        # Map avos job types to the correct handler functions
        job_type_map = {
            'avos-pytest': 'run_pytest',
            'avos-demo': 'run_avos_demo',
            'avos-docs': 'build_documentation',
            'avos-hlir': 'process_hlir_file',
            'avos-hardware-test': 'run_hardware_test'
        }
        
        handler_func = job_type_map.get(job_type)
        if not handler_func:
            print(f"  ❌ Error: Unknown AVOS job type '{job_type}'")
            return
            
        cmd = [
            'python', 'qqueue.py', 'enqueue-python',
            f'avos_jobs:{handler_func}',
            '--kwargs', json.dumps(payload),
            '--priority', str(priority)
        ]
        if delay > 0:
            cmd.extend(['--delay', str(delay)])
            
    else:
        print(f"  ❌ Error: Unknown job type '{job_type}'")
        return
    
    # Execute the command
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ❌ Error enqueuing job: {result.stderr}")
    else:
        print(f"  ✓ Job enqueued successfully")

def run_workflow(file_path: str, sections: list = None):
    """Run a workflow from a YAML file"""
    print(f"Loading workflow from {file_path}...")
    
    try:
        workflow = load_workflow(file_path)
    except Exception as e:
        print(f"❌ Error loading workflow: {e}")
        return
    
    print(f"✓ Loaded workflow: {workflow.get('name', 'unnamed workflow')}")
    
    # Process each section
    for section, jobs in workflow.items():
        if section in ['name', 'setup']:
            continue
            
        # If specific sections were requested, skip others
        if sections and section not in sections:
            continue
            
        print(f"\nProcessing {section} section...")
        for job in jobs:
            enqueue_workflow_job(job, section)
    
    print(f"\n✅ Workflow processing complete!")

def main():
    parser = argparse.ArgumentParser(description="Run AVOS workflows using qqueue")
    parser.add_argument('workflow_file', help='Path to workflow YAML file')
    parser.add_argument('--sections', nargs='+', help='Specific sections to run (default: all)')
    
    args = parser.parse_args()
    
    run_workflow(args.workflow_file, args.sections)

if __name__ == '__main__':
    main()