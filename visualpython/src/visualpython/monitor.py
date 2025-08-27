"""
File monitoring system for VisualPython live coding

This module provides robust file system monitoring for the "save-to-see"
live coding experience that makes VisualPython revolutionary.
"""

import os
import time
import threading
import hashlib
from pathlib import Path
from typing import Callable, Optional, Dict, Any, List
from dataclasses import dataclass

# Try to import watchdog for better performance
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None
    FileSystemEventHandler = None


@dataclass
class FileChangeEvent:
    """Represents a file change event."""
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
    Base file monitor for tracking Python file changes and triggering visual execution.
    
    This is the core component that enables the revolutionary "save-to-see" workflow.
    """
    
    def __init__(self, callback: Callable[[FileChangeEvent], None]):
        self.callback = callback
        self.monitored_files: Dict[str, Dict[str, Any]] = {}
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.check_interval = 0.1  # Check every 100ms
        self.debounce_time = 0.2   # Wait 200ms after last change
        
        # Statistics
        self.stats = {
            'files_monitored': 0,
            'changes_detected': 0,
            'callback_executions': 0,
            'average_response_time': 0,
            'total_response_time': 0
        }
        
        # Debouncing
        self.pending_changes: Dict[str, float] = {}
        self.debounce_thread: Optional[threading.Thread] = None
        self.debounce_running = False

    def add_file(self, filepath: str) -> bool:
        """Add a file to the monitoring list."""
        try:
            filepath = os.path.abspath(filepath)
            if not os.path.exists(filepath):
                print(f"Warning: File {filepath} does not exist")
                return False
            
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
            print(f"✅ Added {os.path.basename(filepath)} to monitoring")
            return True
            
        except Exception as e:
            print(f"❌ Error adding file {filepath}: {e}")
            return False

    def remove_file(self, filepath: str) -> bool:
        """Remove a file from monitoring."""
        filepath = os.path.abspath(filepath)
        if filepath in self.monitored_files:
            del self.monitored_files[filepath]
            self.stats['files_monitored'] = len(self.monitored_files)
            return True
        return False

    def start_monitoring(self):
        """Start monitoring files for changes."""
        if self.is_monitoring:
            return
            
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        # Start debounce handler
        self.debounce_running = True
        self.debounce_thread = threading.Thread(target=self._debounce_loop, daemon=True)
        self.debounce_thread.start()
        
        print(f"🔄 Started monitoring {len(self.monitored_files)} files")

    def stop_monitoring(self):
        """Stop monitoring files."""
        self.is_monitoring = False
        self.debounce_running = False
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1.0)
        if self.debounce_thread and self.debounce_thread.is_alive():
            self.debounce_thread.join(timeout=1.0)
            
        print("⏹️  Stopped file monitoring")

    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.is_monitoring:
            try:
                for filepath in list(self.monitored_files.keys()):
                    self._check_file_for_changes(filepath)
                time.sleep(self.check_interval)
            except Exception as e:
                print(f"❌ Error in monitor loop: {e}")
                time.sleep(1)

    def _debounce_loop(self):
        """Handle debounced change events."""
        while self.debounce_running:
            try:
                current_time = time.time()
                ready_files = []
                
                for filepath, change_time in self.pending_changes.items():
                    if current_time - change_time >= self.debounce_time:
                        ready_files.append(filepath)
                
                for filepath in ready_files:
                    del self.pending_changes[filepath]
                    self._process_file_change(filepath)
                
                time.sleep(0.05)  # Check every 50ms
            except Exception as e:
                print(f"❌ Error in debounce loop: {e}")
                time.sleep(0.1)

    def _check_file_for_changes(self, filepath: str):
        """Check a file for changes."""
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

            stat_result = os.stat(filepath)
            file_info = self.monitored_files[filepath]
            
            # Check if file has been modified
            if (stat_result.st_mtime > file_info['mtime'] or
                    stat_result.st_size != file_info['size']):
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        new_content = f.read()
                    
                    new_hash = hashlib.md5(new_content.encode()).hexdigest()
                    
                    # Only process if content actually changed
                    if new_hash != file_info['content_hash']:
                        # Add to pending changes for debouncing
                        self.pending_changes[filepath] = time.time()
                        
                        # Update file info
                        file_info.update({
                            'mtime': stat_result.st_mtime,
                            'size': stat_result.st_size,
                            'content_hash': new_hash,
                            'last_content': new_content,
                            'change_count': file_info['change_count'] + 1,
                            'last_change_time': time.time()
                        })
                    else:
                        # Update metadata only
                        file_info.update({
                            'mtime': stat_result.st_mtime,
                            'size': stat_result.st_size
                        })
                        
                except Exception as e:
                    print(f"❌ Error reading file {filepath}: {e}")
                    
        except Exception as e:
            print(f"❌ Error checking file {filepath}: {e}")

    def _process_file_change(self, filepath: str):
        """Process a debounced file change."""
        try:
            file_info = self.monitored_files[filepath]
            
            event = FileChangeEvent(
                filepath=filepath,
                event_type='modified',
                timestamp=time.time(),
                old_content=None,  # We don't store old content for efficiency
                new_content=file_info['last_content'],
                content_hash=file_info['content_hash']
            )
            
            self._handle_change_event(event)
            
        except Exception as e:
            print(f"❌ Error processing file change for {filepath}: {e}")

    def _handle_change_event(self, event: FileChangeEvent):
        """Handle a file change event."""
        start_time = time.time()
        
        try:
            self.stats['changes_detected'] += 1
            
            # Show change notification
            filename = os.path.basename(event.filepath)
            print(f"📝 File changed: {filename}")
            
            # Call the callback
            self.callback(event)
            
            self.stats['callback_executions'] += 1
            response_time = time.time() - start_time
            self.stats['total_response_time'] += response_time
            self.stats['average_response_time'] = (
                self.stats['total_response_time'] /
                max(1, self.stats['callback_executions'])
            )
            
            print(f"⚡ Processed in {response_time*1000:.1f}ms")
            
        except Exception as e:
            print(f"❌ Error in change callback: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get monitoring statistics."""
        return {
            **self.stats,
            'monitored_files': list(self.monitored_files.keys()),
            'is_monitoring': self.is_monitoring,
            'check_interval_ms': self.check_interval * 1000,
            'file_change_counts': {
                os.path.basename(filepath): info['change_count']
                for filepath, info in self.monitored_files.items()
            }
        }


class WatchdogFileMonitor(FileMonitor):
    """
    Enhanced file monitor using the watchdog library for better performance.
    """
    
    def __init__(self, callback: Callable[[FileChangeEvent], None]):
        super().__init__(callback)
        self.observer: Optional[Observer] = None
        self.event_handlers: Dict[str, 'VisualPythonEventHandler'] = {}

    def start_monitoring(self):
        """Start monitoring using watchdog if available."""
        if not WATCHDOG_AVAILABLE:
            print("📦 Watchdog not available, using polling monitor")
            super().start_monitoring()
            return
            
        if self.is_monitoring:
            return
            
        self.is_monitoring = True
        self.observer = Observer()
        
        # Setup watchdog for each file
        for filepath in self.monitored_files.keys():
            self._setup_watchdog_for_file(filepath)
        
        self.observer.start()
        
        # Start debounce handler
        self.debounce_running = True
        self.debounce_thread = threading.Thread(target=self._debounce_loop, daemon=True)
        self.debounce_thread.start()
        
        print(f"👀 Started watchdog monitoring for {len(self.monitored_files)} files")

    def stop_monitoring(self):
        """Stop watchdog monitoring."""
        self.is_monitoring = False
        self.debounce_running = False
        
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            
        if self.debounce_thread and self.debounce_thread.is_alive():
            self.debounce_thread.join(timeout=1.0)
            
        self.event_handlers.clear()
        print("⏹️  Stopped watchdog monitoring")

    def _setup_watchdog_for_file(self, filepath: str):
        """Set up watchdog monitoring for a specific file."""
        try:
            file_dir = os.path.dirname(filepath)
            filename = os.path.basename(filepath)
            
            if file_dir not in self.event_handlers:
                handler = VisualPythonEventHandler(self, file_dir)
                self.event_handlers[file_dir] = handler
                self.observer.schedule(handler, file_dir, recursive=False)
            
            self.event_handlers[file_dir].add_watched_file(filename)
            
        except Exception as e:
            print(f"❌ Error setting up watchdog for {filepath}: {e}")


class VisualPythonEventHandler(FileSystemEventHandler):
    """Watchdog event handler for VisualPython file monitoring."""
    
    def __init__(self, monitor: WatchdogFileMonitor, watch_dir: str):
        self.monitor = monitor
        self.watch_dir = watch_dir
        self.watched_files: set = set()

    def add_watched_file(self, filename: str):
        """Add a file to the watch list."""
        self.watched_files.add(filename)

    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
            
        filename = os.path.basename(event.src_path)
        if filename in self.watched_files:
            filepath = os.path.join(self.watch_dir, filename)
            if filepath in self.monitor.monitored_files:
                # Add to pending changes for debouncing
                self.monitor.pending_changes[filepath] = time.time()


class LiveCodeSession:
    """
    Live coding session combining file monitoring and visual execution.
    
    This is the high-level interface for the revolutionary VisualPython experience.
    """
    
    def __init__(self, backend='tkinter', **kwargs):
        from .core import VisualPythonEngine
        
        self.engine = VisualPythonEngine(backend=backend, **kwargs)
        
        # Use watchdog if available, otherwise fall back to polling
        monitor_class = WatchdogFileMonitor if WATCHDOG_AVAILABLE else FileMonitor
        self.monitor = monitor_class(self._on_file_change)
        
        self.active_files: List[str] = []
        self.session_stats = {
            'session_start_time': time.time(),
            'total_executions': 0,
            'total_execution_time': 0,
            'files_processed': 0
        }

    def add_file(self, filepath: str):
        """Add a Python file to the live session."""
        if self.monitor.add_file(filepath):
            self.active_files.append(filepath)
            
            try:
                # Execute the file initially
                with open(filepath, 'r', encoding='utf-8') as f:
                    code = f.read()
                
                result = self.engine.execute(code)
                self.session_stats['files_processed'] += 1
                self.session_stats['total_executions'] += 1
                self.session_stats['total_execution_time'] += result.execution_time_ms
                
                print(f"✅ Added {os.path.basename(filepath)} to live session")
                return True
                
            except Exception as e:
                print(f"❌ Error executing initial file {filepath}: {e}")
                return False
                
        return False

    def start_session(self):
        """Start the live coding session."""
        if not self.active_files:
            print("❌ No files to monitor. Add files first with add_file()")
            return
            
        self.monitor.start_monitoring()
        
        print("\n🔥 VisualPython Live Session Started!")
        print("=" * 50)
        print("✨ Edit your Python files and watch changes appear instantly!")
        print("💡 No compilation, no restarts, just pure visual feedback!")
        print("🛑 Press Ctrl+C to stop the session")
        print("=" * 50)
        
        try:
            # Keep the session running
            while self.monitor.is_monitoring:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n⏹️  Stopping live session...")
            self.stop_session()

    def stop_session(self):
        """Stop the live coding session."""
        self.monitor.stop_monitoring()
        self.engine.cleanup()
        
        # Print session summary
        session_time = time.time() - self.session_stats['session_start_time']
        print("\n📊 Live Session Summary:")
        print("=" * 30)
        print(f"Duration: {session_time:.1f} seconds")
        print(f"Files processed: {self.session_stats['files_processed']}")
        print(f"Total executions: {self.session_stats['total_executions']}")
        
        if self.session_stats['total_executions'] > 0:
            avg_time = self.session_stats['total_execution_time'] / self.session_stats['total_executions']
            print(f"Average execution time: {avg_time:.2f}ms")
        
        monitor_stats = self.monitor.get_statistics()
        print(f"Changes detected: {monitor_stats['changes_detected']}")
        print(f"Average response time: {monitor_stats['average_response_time']*1000:.1f}ms")
        print("\n🎯 Thank you for using VisualPython!")

    def _on_file_change(self, event: FileChangeEvent):
        """Handle file change events."""
        if event.event_type == 'modified' and event.new_content:
            start_time = time.time()
            
            try:
                # Execute the changed file
                result = self.engine.execute(event.new_content)
                
                self.session_stats['total_executions'] += 1
                self.session_stats['total_execution_time'] += result.execution_time_ms
                
                total_time = (time.time() - start_time) * 1000
                filename = os.path.basename(event.filepath)
                
                print(f"🚀 {filename} executed in {total_time:.1f}ms (no compilation!)")
                
            except Exception as e:
                print(f"❌ Execution error in {os.path.basename(event.filepath)}: {e}")


def live_monitor(filepath: str, backend='tkinter', **kwargs):
    """
    Start monitoring a Python file with immediate visual execution.
    
    This is the main entry point for the revolutionary VisualPython experience.
    """
    session = LiveCodeSession(backend=backend, **kwargs)
    
    if session.add_file(filepath):
        session.start_session()
    else:
        print(f"❌ Failed to add file {filepath} to live session")
    
    return session


def create_live_session(files: List[str] = None, backend='tkinter', **kwargs):
    """Create a live coding session with multiple files."""
    session = LiveCodeSession(backend=backend, **kwargs)
    
    if files:
        for filepath in files:
            session.add_file(filepath)
    
    return session


def monitor_directory(directory: str, pattern: str = "*.py", backend='tkinter', **kwargs):
    """Monitor all Python files in a directory."""
    directory = Path(directory)
    if not directory.exists():
        print(f"❌ Directory {directory} does not exist")
        return None
    
    files = list(directory.glob(pattern))
    if not files:
        print(f"❌ No files matching {pattern} found in {directory}")
        return None
    
    session = create_live_session([str(f) for f in files], backend=backend, **kwargs)
    print(f"📁 Monitoring {len(files)} files in {directory}")
    
    return session