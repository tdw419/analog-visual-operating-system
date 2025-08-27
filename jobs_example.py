"""
jobs_example.py - Example jobs for the qqueue system
"""

import time
import random

def slow_add(a: int, b: int, delay: int = 1) -> int:
    """Example job that adds two numbers after a delay"""
    print(f"Computing {a} + {b} with {delay}s delay...")
    time.sleep(delay)
    result = a + b
    print(f"Result: {result}")
    return result

def unreliable_task(success_rate: float = 0.7, delay: int = 1) -> str:
    """Example job that sometimes fails"""
    print(f"Running unreliable task with {success_rate*100}% success rate...")
    time.sleep(delay)
    
    if random.random() > success_rate:
        raise Exception("Random failure occurred!")
    
    return "Task completed successfully"

def generate_report(date: str, report_type: str = "daily") -> dict:
    """Example job that generates a report"""
    print(f"Generating {report_type} report for {date}...")
    time.sleep(2)  # Simulate work
    
    # Simulate some data
    data = {
        "date": date,
        "type": report_type,
        "metrics": {
            "users": random.randint(100, 1000),
            "sessions": random.randint(500, 5000),
            "conversion_rate": round(random.uniform(1.0, 10.0), 2)
        }
    }
    
    print(f"Report generated: {data}")
    return data

def process_data_file(filename: str) -> str:
    """Example job that processes a data file"""
    print(f"Processing data file: {filename}")
    time.sleep(3)  # Simulate file processing
    
    # Simulate processing
    lines_processed = random.randint(1000, 10000)
    result = f"Processed {lines_processed} lines from {filename}"
    print(result)
    return result

def backup_database() -> str:
    """Example job that performs a database backup"""
    print("Starting database backup...")
    time.sleep(5)  # Simulate backup process
    
    # Simulate backup
    backup_file = f"backup_{int(time.time())}.sql"
    result = f"Database backed up to {backup_file}"
    print(result)
    return result