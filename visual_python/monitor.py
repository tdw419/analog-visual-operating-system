"""
File monitoring system for VisualPython

This module provides live file monitoring capabilities that enable the
"edit code and see changes instantly" experience without restarting programs.
"""

import os
import time
import threading
from pathlib import Path
from typing import Callable, Optional, Dict, Any, List
from dataclasses import dataclass
import hashlib

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False


@dataclass
class FileChangeEvent:
    """Represents a file change event"""
    filepath: str
    event_type: str  # 'modified', 'created', 'deleted', 'moved'
    timestamp: float
    old_content: Optional[str] = None
    new_content: Optional[str] = None
    content_hash: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = time.time()


class FileMonitor:
    """
    Base file monitor that tracks changes to Python files
    and triggers immediate visual execution.
    
    This is the core component that enables the "no restart needed" experience.
    """
    
    def __init__(self, callback: Callable[[FileChangeEvent], None]):
        """
        Initialize file monitor
        
        Args:
            callback: Function to call when file changes are detected
        """
        self.callback = callback
        self.monitored_files: Dict[str, Dict[str, Any]] = {}
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.check_interval = 0.1  # Check every 100ms for responsiveness
        
        # Statistics
        self.stats = {
            'files_monitored': 0,
            'changes_detected': 0,
            'callback_executions': 0,
            'average_response_time': 0,
            'total_response_time': 0
        }
    
    def add_file(self, filepath: str) -> bool:
        """
        Add a file to the monitoring list
        
        Args:
            filepath: Path to the file to monitor
            
        Returns:
            bool: True if file was added successfully
        """
        try:
            filepath = os.path.abspath(filepath)
            
            if not os.path.exists(filepath):
                print(f"Warning: File {filepath} does not exist")
                return False
            
            # Get initial file state
            stat_result = os.stat(filepath)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            content_hash = hashlib.md5(content.encode()).hexdigest()
            
            self.monitored_files[filepath] = {
                'mtime': stat_result.st_mtime,
                'size': stat_result.st_size,
                'content_hash': content_hash,
                'last_content': content,
                'change_count': 0,
                'last_change_time': time.time()
            }
            
            self.stats['files_monitored'] = len(self.monitored_files)
            return True
            
        except Exception as e:
            print(f"Error adding file {filepath}: {e}")
            return False
    
    def remove_file(self, filepath: str) -> bool:
        """
        Remove a file from monitoring
        
        Args:
            filepath: Path to the file to stop monitoring
            
        Returns:
            bool: True if file was removed
        """
        filepath = os.path.abspath(filepath)
        if filepath in self.monitored_files:
            del self.monitored_files[filepath]
            self.stats['files_monitored'] = len(self.monitored_files)
            return True
        return False
    
    def start_monitoring(self):
        """Start monitoring files for changes"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        print(f"Started monitoring {len(self.monitored_files)} files")
        print("Edit your files and watch changes appear instantly!")
    
    def stop_monitoring(self):
        """Stop monitoring files"""
        self.is_monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1.0)
        
        print("Stopped file monitoring")
    
    def _monitor_loop(self):
        """Main monitoring loop that checks files for changes"""
        while self.is_monitoring:
            try:
                for filepath in list(self.monitored_files.keys()):
                    self._check_file_for_changes(filepath)
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                print(f"Error in monitor loop: {e}")
                time.sleep(1)  # Longer sleep on error
    
    def _check_file_for_changes(self, filepath: str):
        """Check a specific file for changes"""
        try:
            if not os.path.exists(filepath):
                # File was deleted
                event = FileChangeEvent(
                    filepath=filepath,
                    event_type='deleted',
                    timestamp=time.time(),
                    old_content=self.monitored_files[filepath]['last_content']
                )
                self._handle_change_event(event)
                self.remove_file(filepath)
                return
            
            # Check file modification time and size
            stat_result = os.stat(filepath)
            file_info = self.monitored_files[filepath]
            
            if (stat_result.st_mtime > file_info['mtime'] or 
                stat_result.st_size != file_info['size']):
                
                # File was modified, read new content
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        new_content = f.read()
                    
                    # Check if content actually changed (not just timestamp)
                    new_hash = hashlib.md5(new_content.encode()).hexdigest()
                    
                    if new_hash != file_info['content_hash']:
                        # Content actually changed
                        event = FileChangeEvent(
                            filepath=filepath,
                            event_type='modified',
                            timestamp=time.time(),
                            old_content=file_info['last_content'],
                            new_content=new_content,
                            content_hash=new_hash
                        )
                        
                        # Update file info
                        file_info.update({
                            'mtime': stat_result.st_mtime,
                            'size': stat_result.st_size,
                            'content_hash': new_hash,
                            'last_content': new_content,
                            'change_count': file_info['change_count'] + 1,
                            'last_change_time': time.time()
                        })
                        
                        self._handle_change_event(event)
                    else:
                        # Only timestamp changed, update silently
                        file_info.update({
                            'mtime': stat_result.st_mtime,
                            'size': stat_result.st_size
                        })
                
                except Exception as e:
                    print(f"Error reading file {filepath}: {e}")
        
        except Exception as e:
            print(f"Error checking file {filepath}: {e}")
    
    def _handle_change_event(self, event: FileChangeEvent):
        """Handle a file change event"""
        start_time = time.time()
        
        try:
            self.stats['changes_detected'] += 1
            
            # Call the user-provided callback
            self.callback(event)
            
            self.stats['callback_executions'] += 1
            
            # Update response time statistics
            response_time = time.time() - start_time
            self.stats['total_response_time'] += response_time
            self.stats['average_response_time'] = (
                self.stats['total_response_time'] / 
                max(1, self.stats['callback_executions'])
            )
            
        except Exception as e:
            print(f"Error in change callback: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get monitoring statistics"""
        return {
            **self.stats,
            'monitored_files': list(self.monitored_files.keys()),
            'is_monitoring': self.is_monitoring,
            'check_interval_ms': self.check_interval * 1000,
            'file_change_counts': {
                filepath: info['change_count'] 
                for filepath, info in self.monitored_files.items()
            }
        }


class WatchdogFileMonitor(FileMonitor):
    """
    Enhanced file monitor using the watchdog library for better performance
    
    Falls back to basic polling if watchdog is not available
    """
    
    def __init__(self, callback: Callable[[FileChangeEvent], None]):
        super().__init__(callback)
        self.observer: Optional[Observer] = None
        self.event_handlers: Dict[str, 'VisualPythonEventHandler'] = {}
    
    def start_monitoring(self):
        """Start monitoring using watchdog if available"""
        if not WATCHDOG_AVAILABLE:
            print("Watchdog not available, falling back to polling monitor")
            super().start_monitoring()
            return
        
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.observer = Observer()
        
        # Set up watchdog observers for each monitored file
        for filepath in self.monitored_files.keys():
            self._setup_watchdog_for_file(filepath)
        
        self.observer.start()
        print(f"Started watchdog monitoring for {len(self.monitored_files)} files")
    
    def stop_monitoring(self):
        """Stop watchdog monitoring"""
        self.is_monitoring = False
        
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
        
        self.event_handlers.clear()
        print("Stopped watchdog monitoring")
    
    def _setup_watchdog_for_file(self, filepath: str):
        """Set up watchdog monitoring for a specific file"""
        try:
            file_dir = os.path.dirname(filepath)
            filename = os.path.basename(filepath)
            
            if file_dir not in self.event_handlers:
                handler = VisualPythonEventHandler(self, file_dir)
                self.event_handlers[file_dir] = handler
                self.observer.schedule(handler, file_dir, recursive=False)
            
            # Add file to handler's watch list
            self.event_handlers[file_dir].add_watched_file(filename)
            
        except Exception as e:
            print(f"Error setting up watchdog for {filepath}: {e}")


class VisualPythonEventHandler(FileSystemEventHandler):
    """Watchdog event handler for VisualPython file monitoring"""
    
    def __init__(self, monitor: WatchdogFileMonitor, watch_dir: str):
        self.monitor = monitor
        self.watch_dir = watch_dir
        self.watched_files: set = set()
    
    def add_watched_file(self, filename: str):
        """Add a file to the watch list"""
        self.watched_files.add(filename)
    
    def on_modified(self, event):
        """Handle file modification events"""
        if event.is_directory:
            return
        
        filename = os.path.basename(event.src_path)
        if filename in self.watched_files:
            filepath = os.path.join(self.watch_dir, filename)
            self.monitor._check_file_for_changes(filepath)
    
    def on_created(self, event):
        """Handle file creation events"""
        if event.is_directory:
            return
        
        filename = os.path.basename(event.src_path)
        if filename in self.watched_files:
            change_event = FileChangeEvent(
                filepath=event.src_path,
                event_type='created',
                timestamp=time.time()
            )
            self.monitor._handle_change_event(change_event)
    
    def on_deleted(self, event):
        """Handle file deletion events"""
        if event.is_directory:
            return
        
        filename = os.path.basename(event.src_path)
        if filename in self.watched_files:
            change_event = FileChangeEvent(
                filepath=event.src_path,
                event_type='deleted',
                timestamp=time.time()
            )
            self.monitor._handle_change_event(change_event)


class LiveCodeSession:
    """
    Complete live coding session that combines file monitoring
    with visual Python execution
    """
    
    def __init__(self, backend='tkinter', **kwargs):
        """Initialize a live coding session"""
        from .core import VisualPythonEngine
        
        self.engine = VisualPythonEngine(backend=backend, **kwargs)
        
        # Choose best available monitor
        if WATCHDOG_AVAILABLE:
            self.monitor = WatchdogFileMonitor(self._on_file_change)
        else:
            self.monitor = FileMonitor(self._on_file_change)
        
        self.active_files: List[str] = []
        self.session_stats = {
            'session_start_time': time.time(),
            'total_executions': 0,
            'total_execution_time': 0,
            'files_processed': 0
        }
    
    def add_file(self, filepath: str):
        """Add a Python file to the live session"""
        if self.monitor.add_file(filepath):
            self.active_files.append(filepath)
            
            # Execute the file initially
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    code = f.read()
                self.engine.execute(code)
                self.session_stats['files_processed'] += 1
                
                print(f"Added {filepath} to live session")
                return True
            except Exception as e:
                print(f"Error executing initial file {filepath}: {e}")
                return False
        return False
    
    def start_session(self):
        """Start the live coding session"""
        if not self.active_files:
            print("No files to monitor. Add files first with add_file()")
            return
        
        self.monitor.start_monitoring()
        
        print("Live coding session started!")
        print("=" * 50)
        print("Edit your Python files and watch changes appear instantly!")
        print("Press Ctrl+C to stop the session")
        print("=" * 50)
        
        try:
            # Keep the session running
            while self.monitor.is_monitoring:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\nStopping live session...")
            self.stop_session()
    
    def stop_session(self):
        """Stop the live coding session"""
        self.monitor.stop_monitoring()
        self.engine.cleanup()
        
        # Print session statistics
        session_time = time.time() - self.session_stats['session_start_time']
        
        print("\nLive Session Summary:")
        print(f"Duration: {session_time:.1f} seconds")
        print(f"Files processed: {self.session_stats['files_processed']}")
        print(f"Total executions: {self.session_stats['total_executions']}")
        
        if self.session_stats['total_executions'] > 0:
            avg_time = self.session_stats['total_execution_time'] / self.session_stats['total_executions']
            print(f"Average execution time: {avg_time:.2f}ms")
        
        monitor_stats = self.monitor.get_statistics()
        print(f"Changes detected: {monitor_stats['changes_detected']}")
        print(f"Average response time: {monitor_stats['average_response_time']:.2f}ms")
    
    def _on_file_change(self, event: FileChangeEvent):
        """Handle file change events during live session"""
        if event.event_type == 'modified' and event.new_content:
            start_time = time.time()
            
            try:
                # Execute the changed code immediately
                execution_time = self.engine.execute(event.new_content, live_mode=True)
                
                self.session_stats['total_executions'] += 1
                self.session_stats['total_execution_time'] += execution_time
                
                total_time = (time.time() - start_time) * 1000
                
                print(f"File changed: {os.path.basename(event.filepath)} "
                      f"(executed in {total_time:.1f}ms)")
                
            except Exception as e:
                print(f"Execution error in {event.filepath}: {e}")


# Convenience functions for easy use
def live_monitor(filepath: str, backend='tkinter', **kwargs):
    """
    Start monitoring a Python file with immediate visual execution
    
    Args:
        filepath: Path to Python file to monitor
        backend: Rendering backend to use
        **kwargs: Additional options
        
    Returns:
        LiveCodeSession: The active session
    """
    session = LiveCodeSession(backend=backend, **kwargs)
    
    if session.add_file(filepath):
        session.start_session()
    else:
        print(f"Failed to add file {filepath} to live session")
    
    return session

def create_live_session(files: List[str] = None, backend='tkinter', **kwargs):
    """
    Create a live coding session with multiple files
    
    Args:
        files: List of Python files to monitor
        backend: Rendering backend to use
        **kwargs: Additional options
        
    Returns:
        LiveCodeSession: The configured session
    """
    session = LiveCodeSession(backend=backend, **kwargs)
    
    if files:
        for filepath in files:
            session.add_file(filepath)
    
    return session

def monitor_directory(directory: str, pattern: str = "*.py", backend='tkinter', **kwargs):
    """
    Monitor all Python files in a directory
    
    Args:
        directory: Directory to monitor
        pattern: File pattern to match (default: *.py)
        backend: Rendering backend to use
        **kwargs: Additional options
        
    Returns:
        LiveCodeSession: The active session
    """
    from glob import glob
    
    directory = Path(directory)
    if not directory.exists():
        print(f"Directory {directory} does not exist")
        return None
    
    # Find all matching files
    files = list(directory.glob(pattern))
    
    if not files:
        print(f"No files matching {pattern} found in {directory}")
        return None
    
    session = create_live_session([str(f) for f in files], backend=backend, **kwargs)
    
    print(f"Monitoring {len(files)} files in {directory}")
    
    return session


# CLI entry point
def main():
    """Main entry point for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="VisualPython Live Monitor - Execute Python files visually without compilation"
    )
    
    parser.add_argument(
        'files',
        nargs='+',
        help='Python files to monitor for changes'
    )
    
    parser.add_argument(
        '--backend',
        choices=['tkinter', 'pygame', 'web'],
        default='tkinter',
        help='Visual backend to use (default: tkinter)'
    )
    
    parser.add_argument(
        '--width',
        type=int,
        default=800,
        help='Display width (default: 800)'
    )
    
    parser.add_argument(
        '--height',
        type=int,
        default=600,
        help='Display height (default: 600)'
    )
    
    parser.add_argument(
        '--interval',
        type=float,
        default=0.1,
        help='File check interval in seconds (default: 0.1)'
    )
    
    args = parser.parse_args()
    
    # Create and start live session
    session = create_live_session(
        files=args.files,
        backend=args.backend,
        width=args.width,
        height=args.height
    )
    
    if args.interval != 0.1:
        session.monitor.check_interval = args.interval
    
    session.start_session()


if __name__ == "__main__":
    main()