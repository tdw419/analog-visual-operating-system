#!/usr/bin/env python3
"""
qqueue - A simple, reliable SQLite-backed task queue for local development
No servers, no Redis - just a single file database and pure Python.

Features:
- enqueue-shell "..." - queue any command (builds, tests, scripts)
- enqueue-python module:function - run Python functions as jobs
- Retries with backoff, priorities, delays
- Multiple workers can run in parallel
- State saved in qqueue.db next to the script

Usage:
python qqueue.py init
python qqueue.py enqueue-shell "echo Hello from qqueue" --priority 5
python qqueue.py enqueue-python jobs_example:slow_add --kwargs '{"a":2,"b":3,"delay":1}'
python qqueue.py worker
python qqueue.py list
python qqueue.py list --status failed
python qqueue.py retry --id 3
python qqueue.py purge-done
"""

import sqlite3
import json
import time
import subprocess
import sys
import os
import importlib
import argparse
import traceback
from typing import Any, Dict, Optional
from contextlib import contextmanager

# Try to import AVOS handlers (optional)
try:
    from avos_jobs import run_pytest, run_avos_demo, build_documentation, process_hlir_file, run_hardware_test
    HAS_AVOS = True
except ImportError:
    HAS_AVOS = False

# Database schema
SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_type TEXT NOT NULL,
    payload TEXT NOT NULL,
    priority INTEGER DEFAULT 1,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    delay_until TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error TEXT
);

CREATE INDEX IF NOT EXISTS idx_status_priority ON jobs(status, priority DESC, delay_until ASC);
CREATE INDEX IF NOT EXISTS idx_delay_until ON jobs(delay_until);
"""

DB_FILE = 'qqueue.db'

@contextmanager
def get_db():
    """Get a database connection with proper cleanup"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """Initialize the database"""
    with get_db() as conn:
        conn.executescript(SCHEMA)
        conn.commit()
    print(f"✓ Initialized database {DB_FILE}")

def handle_shell(payload: Dict[str, Any]) -> str:
    """Handle shell command jobs"""
    cmd = payload['command']
    print(f"Executing shell command: {cmd}")
    
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        raise Exception(f"Command failed with exit code {result.returncode}: {result.stderr}")
    
    return result.stdout

def handle_python(payload: Dict[str, Any]) -> Any:
    """Handle Python function jobs"""
    module_func = payload['function']
    kwargs = payload.get('kwargs', {})
    
    print(f"Executing Python function: {module_func}")
    
    # Split module and function
    if ':' not in module_func:
        raise Exception("Function must be in format module:function")
    
    module_name, func_name = module_func.split(':', 1)
    
    # Import module
    try:
        module = importlib.import_module(module_name)
    except ImportError as e:
        raise Exception(f"Failed to import module {module_name}: {e}")
    
    # Get function
    if not hasattr(module, func_name):
        raise Exception(f"Function {func_name} not found in module {module_name}")
    
    func = getattr(module, func_name)
    
    # Call function
    return func(**kwargs)

# Job handlers
HANDLERS = {
    'shell': handle_shell,
    'python': handle_python,
}

# Add AVOS handlers if available
if HAS_AVOS:
    HANDLERS.update({
        'avos-pytest': run_pytest,
        'avos-demo': run_avos_demo,
        'avos-docs': build_documentation,
        'avos-hlir': process_hlir_file,
        'avos-hardware-test': run_hardware_test,
    })

def enqueue_job(job_type: str, payload: Dict[str, Any], priority: int = 1, 
                delay: int = 0, max_attempts: int = 3):
    """Enqueue a job"""
    with get_db() as conn:
        delay_until = time.time() + delay
        
        conn.execute("""
            INSERT INTO jobs (job_type, payload, priority, delay_until, max_attempts)
            VALUES (?, ?, ?, datetime(?, 'unixepoch'), ?)
        """, (job_type, json.dumps(payload), priority, delay_until, max_attempts))
        
        job_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
        
        status = "delayed" if delay > 0 else "pending"
        conn.execute("UPDATE jobs SET status = ? WHERE id = ?", (status, job_id))
        conn.commit()
        
        print(f"✓ Enqueued {job_type} job #{job_id} with priority {priority}")
        return job_id

def enqueue_shell(command: str, priority: int = 1, delay: int = 0, max_attempts: int = 3):
    """Enqueue a shell command job"""
    payload = {'command': command}
    return enqueue_job('shell', payload, priority, delay, max_attempts)

def enqueue_python(function: str, kwargs: Optional[Dict[str, Any]] = None, 
                   priority: int = 1, delay: int = 0, max_attempts: int = 3):
    """Enqueue a Python function job"""
    payload = {'function': function}
    if kwargs:
        payload['kwargs'] = kwargs
    return enqueue_job('python', payload, priority, delay, max_attempts)

def claim_job():
    """Atomically claim a pending job for execution"""
    with get_db() as conn:
        # Find a pending job with highest priority that is not delayed
        job = conn.execute("""
            SELECT * FROM jobs 
            WHERE status = 'pending' 
            AND delay_until <= datetime('now')
            ORDER BY priority DESC, created_at ASC
            LIMIT 1
        """).fetchone()
        
        if not job:
            return None
        
        # Claim the job atomically
        conn.execute("""
            UPDATE jobs 
            SET status = 'running', updated_at = datetime('now')
            WHERE id = ? AND status = 'pending'
        """, (job['id'],))
        
        conn.commit()
        
        # Check if we successfully claimed it
        updated = conn.execute("SELECT * FROM jobs WHERE id = ?", (job['id'],)).fetchone()
        if updated and updated['status'] == 'running':
            return updated
        
        return None

def complete_job(job_id: int, result: Any = None):
    """Mark a job as completed"""
    with get_db() as conn:
        conn.execute("""
            UPDATE jobs 
            SET status = 'completed', updated_at = datetime('now')
            WHERE id = ?
        """, (job_id,))
        conn.commit()
        print(f"✓ Job #{job_id} completed")

def fail_job(job_id: int, error: str):
    """Mark a job as failed, potentially for retry"""
    with get_db() as conn:
        job = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not job:
            return
        
        new_attempts = job['attempts'] + 1
        
        if new_attempts < job['max_attempts']:
            # Retry with exponential backoff (min 5 seconds, max 1 hour)
            delay = min(5 * (2 ** job['attempts']), 3600)
            delay_until = time.time() + delay
            
            conn.execute("""
                UPDATE jobs 
                SET status = 'pending', attempts = ?, updated_at = datetime('now'),
                    delay_until = datetime(?, 'unixepoch'), error = ?
                WHERE id = ?
            """, (new_attempts, delay_until, error, job_id))
            
            print(f"! Job #{job_id} failed, will retry in {delay}s (attempt {new_attempts}/{job['max_attempts']})")
        else:
            # Mark as permanently failed
            conn.execute("""
                UPDATE jobs 
                SET status = 'failed', attempts = ?, updated_at = datetime('now'), error = ?
                WHERE id = ?
            """, (new_attempts, error, job_id))
            
            print(f"✗ Job #{job_id} permanently failed after {new_attempts} attempts")
        
        conn.commit()

def worker_loop():
    """Main worker loop"""
    print("▶ Worker started, waiting for jobs...")
    print("Press Ctrl+C to stop")
    
    try:
        while True:
            job = claim_job()
            if not job:
                time.sleep(1)
                continue
            
            print(f"▶ Processing job #{job['id']} ({job['job_type']})")
            
            try:
                payload = json.loads(job['payload'])
                handler = HANDLERS.get(job['job_type'])
                
                if not handler:
                    raise Exception(f"No handler for job type: {job['job_type']}")
                
                result = handler(payload)
                complete_job(job['id'], result)
                
            except Exception as e:
                error = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
                fail_job(job['id'], error)
                
    except KeyboardInterrupt:
        print("\n⏹ Worker stopped")

def list_jobs(status: Optional[str] = None):
    """List jobs"""
    with get_db() as conn:
        if status:
            jobs = conn.execute("""
                SELECT * FROM jobs WHERE status = ? 
                ORDER BY priority DESC, created_at ASC
            """, (status,)).fetchall()
        else:
            jobs = conn.execute("""
                SELECT * FROM jobs 
                ORDER BY priority DESC, created_at ASC
            """).fetchall()
        
        if not jobs:
            print("No jobs found")
            return
        
        print(f"{'ID':<4} {'Type':<10} {'Status':<12} {'Priority':<8} {'Attempts':<8} {'Created':<20} {'Error'}")
        print("-" * 100)
        
        for job in jobs:
            error = job['error'] or ""
            if len(error) > 50:
                error = error[:47] + "..."
                
            print(f"{job['id']:<4} {job['job_type']:<10} {job['status']:<12} {job['priority']:<8} "
                  f"{job['attempts']:<8} {job['created_at']:<20} {error}")

def retry_job(job_id: int):
    """Retry a failed job"""
    with get_db() as conn:
        conn.execute("""
            UPDATE jobs 
            SET status = 'pending', attempts = 0, updated_at = datetime('now'), error = NULL
            WHERE id = ? AND status = 'failed'
        """, (job_id,))
        
        if conn.execute("SELECT changes()").fetchone()[0] > 0:
            print(f"✓ Job #{job_id} marked for retry")
        else:
            print(f"! Job #{job_id} is not in failed status or not found")
        
        conn.commit()

def purge_completed():
    """Remove completed jobs"""
    with get_db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM jobs WHERE status = 'completed'").fetchone()[0]
        conn.execute("DELETE FROM jobs WHERE status = 'completed'")
        conn.commit()
        print(f"✓ Purged {count} completed jobs")

def main():
    parser = argparse.ArgumentParser(description="qqueue - Simple SQLite-backed task queue")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Init command
    subparsers.add_parser('init', help='Initialize the database')
    
    # Enqueue-shell command
    enqueue_shell_parser = subparsers.add_parser('enqueue-shell', help='Enqueue a shell command')
    enqueue_shell_parser.add_argument('command', help='Shell command to execute')
    enqueue_shell_parser.add_argument('--priority', type=int, default=1, help='Job priority (higher = sooner)')
    enqueue_shell_parser.add_argument('--delay', type=int, default=0, help='Delay in seconds before execution')
    enqueue_shell_parser.add_argument('--max-attempts', type=int, default=3, help='Maximum retry attempts')
    
    # Enqueue-python command
    enqueue_python_parser = subparsers.add_parser('enqueue-python', help='Enqueue a Python function')
    enqueue_python_parser.add_argument('function', help='Function in format module:function')
    enqueue_python_parser.add_argument('--kwargs', help='JSON string of keyword arguments')
    enqueue_python_parser.add_argument('--priority', type=int, default=1, help='Job priority (higher = sooner)')
    enqueue_python_parser.add_argument('--delay', type=int, default=0, help='Delay in seconds before execution')
    enqueue_python_parser.add_argument('--max-attempts', type=int, default=3, help='Maximum retry attempts')
    
    # Worker command
    subparsers.add_parser('worker', help='Start a worker process')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List jobs')
    list_parser.add_argument('--status', help='Filter by status (pending, running, completed, failed)')
    
    # Retry command
    retry_parser = subparsers.add_parser('retry', help='Retry a failed job')
    retry_parser.add_argument('--id', type=int, required=True, help='Job ID to retry')
    
    # Purge-done command
    subparsers.add_parser('purge-done', help='Remove completed jobs')
    
    args = parser.parse_args()
    
    if args.command == 'init':
        init_db()
    elif args.command == 'enqueue-shell':
        kwargs_dict = {}
        enqueue_shell(args.command, args.priority, args.delay, args.max_attempts)
    elif args.command == 'enqueue-python':
        kwargs_dict = json.loads(args.kwargs) if args.kwargs else {}
        enqueue_python(args.function, kwargs_dict, args.priority, args.delay, args.max_attempts)
    elif args.command == 'worker':
        worker_loop()
    elif args.command == 'list':
        list_jobs(args.status)
    elif args.command == 'retry':
        retry_job(args.id)
    elif args.command == 'purge-done':
        purge_completed()
    else:
        parser.print_help()

if __name__ == '__main__':
    main()