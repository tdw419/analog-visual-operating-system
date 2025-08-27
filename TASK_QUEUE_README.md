# AVOS Task Queue System

This directory contains a simple, reliable SQLite-backed task queue system for the AVOS project. The system ensures jobs keep running until completion, with automatic retries and prioritization.

## Components

1. **qqueue.py** - The main task queue system with SQLite backend
2. **jobs_example.py** - Example job functions for testing
3. **avos_jobs.py** - AVOS-specific job handlers
4. **workflow_runner.py** - Script to run workflows from YAML files
5. **avos_workflow.yaml** - Example workflow for AVOS development

## Quick Start

1. **Initialize the database:**
   ```bash
   python qqueue.py init
   ```

2. **Enqueue some work:**
   ```bash
   # Enqueue a shell command
   python qqueue.py enqueue-shell "echo Hello from qqueue" --priority 5
   
   # Enqueue a Python function
   python qqueue.py enqueue-python jobs_example:slow_add --kwargs '{"a":2,"b":3,"delay":1}'
   
   # Enqueue an AVOS-specific job
   python qqueue.py enqueue-python avos_jobs:run_pytest --kwargs '{"args":["-v","tests/"]}' --priority 5
   ```

3. **Start a worker (leave it running):**
   ```bash
   python qqueue.py worker
   ```

4. **Inspect the queue:**
   ```bash
   python qqueue.py list
   python qqueue.py list --status failed
   python qqueue.py retry --id 3
   python qqueue.py purge-done
   ```

## AVOS-Specific Jobs

The system includes several AVOS-specific job types:

- `avos-pytest` - Run pytest with specified arguments
- `avos-demo` - Run an AVOS demo script
- `avos-docs` - Build project documentation
- `avos-hlir` - Process HLIR files
- `avos-hardware-test` - Run hardware tests

## Running Workflows

You can define complex workflows in YAML files and run them:

```bash
python workflow_runner.py avos_workflow.yaml
python workflow_runner.py avos_workflow.yaml --sections testing build
```

## Extending the System

### Add a New Job Type

1. Implement a handler function in `avos_jobs.py`:
   ```python
   def my_new_handler(payload: Dict[str, Any]) -> Any:
       # Your implementation here
       pass
   ```

2. Register it in `qqueue.py`:
   ```python
   HANDLERS.update({
       'avos-my-new-job': my_new_handler,
   })
   ```

3. Add it to the handler functions list:
   ```python
   def handle_avos_my_new_job(payload: Dict[str, Any]) -> Any:
       return my_new_handler(payload)
   ```

### Schedule Jobs

Use `--delay` to run jobs after a specified number of seconds:
```bash
python qqueue.py enqueue-shell "echo Delayed job" --delay 300  # Run in 5 minutes
```

### Prioritize Jobs

Use `--priority` to prioritize critical jobs (higher numbers = higher priority):
```bash
python qqueue.py enqueue-shell "echo Important job" --priority 10
```

## Features

- **Persistent Storage**: All jobs are stored in a SQLite database (`qqueue.db`)
- **Atomic Operations**: Multiple workers can run safely in parallel
- **Automatic Retries**: Failed jobs are retried with exponential backoff
- **Priority Queue**: Higher priority jobs are executed first
- **Delayed Execution**: Schedule jobs to run in the future
- **Multiple Job Types**: Support for shell commands and Python functions
- **AVOS Integration**: Specialized handlers for AVOS-specific tasks

## Notes

- Safe to run multiple `worker` processes at once
- If a job errors, it's retried up to `--max-attempts` times (default 3)
- Everything is local and offline - perfect for development workflows
- Database file (`qqueue.db`) is created in the same directory as the script