"""
Test suite for VisualPython file monitoring system.
"""

import unittest
import tempfile
import os
import time
import threading
from pathlib import Path
from unittest.mock import Mock, patch

from visualpython.monitor import (
    FileChangeEvent, FileMonitor, WatchdogFileMonitor, 
    LiveCodeSession, live_monitor
)


class TestFileChangeEvent(unittest.TestCase):
    """Test FileChangeEvent data structure."""
    
    def test_event_creation(self):
        """Test basic event creation."""
        event = FileChangeEvent(
            filepath="/test/file.py",
            event_type="modified",
            timestamp=1234567890.0,
            new_content="x = 42"
        )
        
        self.assertEqual(event.filepath, "/test/file.py")
        self.assertEqual(event.event_type, "modified")
        self.assertEqual(event.timestamp, 1234567890.0)
        self.assertEqual(event.new_content, "x = 42")
    
    def test_auto_timestamp(self):
        """Test automatic timestamp assignment."""
        event = FileChangeEvent(
            filepath="/test/file.py",
            event_type="modified",
            timestamp=0  # Should auto-assign current time
        )
        
        # Should have assigned current time
        self.assertGreater(event.timestamp, 0)
        self.assertLess(abs(event.timestamp - time.time()), 1.0)


class TestFileMonitor(unittest.TestCase):
    """Test the base FileMonitor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.events_received = []
        self.monitor = FileMonitor(self._on_file_change)
        
        # Create temporary test file
        self.temp_file = tempfile.NamedTemporaryFile(
            mode='w', 
            suffix='.py', 
            delete=False
        )
        self.temp_file.write("x = 1\n")
        self.temp_file.close()
        self.temp_filepath = self.temp_file.name
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.monitor.stop_monitoring()
        try:
            os.unlink(self.temp_filepath)
        except:
            pass
    
    def _on_file_change(self, event: FileChangeEvent):
        """Test callback for file changes."""
        self.events_received.append(event)
    
    def test_add_file(self):
        """Test adding files to monitor."""
        success = self.monitor.add_file(self.temp_filepath)
        
        self.assertTrue(success)
        self.assertIn(self.temp_filepath, self.monitor.monitored_files)
        self.assertEqual(self.monitor.get_statistics()['files_monitored'], 1)
    
    def test_add_nonexistent_file(self):
        """Test adding non-existent file."""
        success = self.monitor.add_file("/nonexistent/file.py")
        
        self.assertFalse(success)
        self.assertEqual(len(self.monitor.monitored_files), 0)
    
    def test_remove_file(self):
        """Test removing files from monitor."""
        self.monitor.add_file(self.temp_filepath)
        success = self.monitor.remove_file(self.temp_filepath)
        
        self.assertTrue(success)
        self.assertNotIn(self.temp_filepath, self.monitor.monitored_files)
        self.assertEqual(self.monitor.get_statistics()['files_monitored'], 0)
    
    def test_file_change_detection(self):
        """Test file change detection."""
        self.monitor.add_file(self.temp_filepath)
        self.monitor.start_monitoring()
        
        # Wait for monitor to start
        time.sleep(0.1)
        
        # Modify file
        with open(self.temp_filepath, 'w') as f:
            f.write("x = 42\n")
        
        # Wait for change detection
        time.sleep(0.3)
        
        self.monitor.stop_monitoring()
        
        # Should have detected the change
        self.assertGreater(len(self.events_received), 0)
        self.assertEqual(self.events_received[-1].event_type, 'modified')
    
    def test_content_hash_tracking(self):
        """Test content hash change tracking."""
        self.monitor.add_file(self.temp_filepath)
        original_info = self.monitor.monitored_files[self.temp_filepath]
        original_hash = original_info['content_hash']
        
        # Modify file content
        with open(self.temp_filepath, 'w') as f:
            f.write("x = 999\n")
        
        # Manually check for changes
        self.monitor._check_file_for_changes(self.temp_filepath)
        
        # Hash should have changed
        new_hash = self.monitor.monitored_files[self.temp_filepath]['content_hash']
        self.assertNotEqual(original_hash, new_hash)
    
    def test_statistics_tracking(self):
        """Test monitoring statistics."""
        self.monitor.add_file(self.temp_filepath)
        stats = self.monitor.get_statistics()
        
        self.assertEqual(stats['files_monitored'], 1)
        self.assertEqual(stats['changes_detected'], 0)
        self.assertEqual(stats['callback_executions'], 0)
        self.assertIn('monitored_files', stats)
        self.assertIn('file_change_counts', stats)
    
    def test_debouncing_interval(self):
        """Test debouncing configuration."""
        # Set very short debounce time for testing
        self.monitor.debounce_time = 0.05
        self.monitor.check_interval = 0.02
        
        self.monitor.add_file(self.temp_filepath)
        self.monitor.start_monitoring()
        
        time.sleep(0.1)
        
        # Make multiple rapid changes
        for i in range(3):
            with open(self.temp_filepath, 'w') as f:
                f.write(f"x = {i}\n")
            time.sleep(0.01)  # Very short delay
        
        # Wait for debouncing
        time.sleep(0.2)
        
        self.monitor.stop_monitoring()
        
        # Should have received events (exact count may vary due to timing)
        self.assertGreater(len(self.events_received), 0)


class TestWatchdogFileMonitor(unittest.TestCase):
    """Test the Watchdog-based file monitor."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.events_received = []
        
        # Create temporary test file
        self.temp_file = tempfile.NamedTemporaryFile(
            mode='w', 
            suffix='.py', 
            delete=False
        )
        self.temp_file.write("x = 1\n")
        self.temp_file.close()
        self.temp_filepath = self.temp_file.name
    
    def tearDown(self):
        """Clean up test fixtures."""
        try:
            os.unlink(self.temp_filepath)
        except:
            pass
    
    def _on_file_change(self, event: FileChangeEvent):
        """Test callback for file changes."""
        self.events_received.append(event)
    
    def test_watchdog_monitor_creation(self):
        """Test creating watchdog monitor."""
        try:
            monitor = WatchdogFileMonitor(self._on_file_change)
            monitor.add_file(self.temp_filepath)
            
            self.assertIsInstance(monitor, WatchdogFileMonitor)
            self.assertIn(self.temp_filepath, monitor.monitored_files)
            
            monitor.stop_monitoring()
            
        except ImportError:
            # Watchdog not available, skip test
            self.skipTest("Watchdog not available")
    
    @unittest.skipIf(not hasattr(WatchdogFileMonitor, '_setup_watchdog_for_file'), 
                     "Watchdog not available")
    def test_watchdog_file_detection(self):
        """Test file change detection with watchdog."""
        monitor = WatchdogFileMonitor(self._on_file_change)
        monitor.add_file(self.temp_filepath)
        monitor.start_monitoring()
        
        # Wait for monitor to start
        time.sleep(0.2)
        
        # Modify file
        with open(self.temp_filepath, 'w') as f:
            f.write("x = 123\n")
        
        # Wait for watchdog detection
        time.sleep(0.3)
        
        monitor.stop_monitoring()
        
        # Should have detected the change
        # Note: watchdog may generate multiple events
        self.assertGreater(len(self.events_received), 0)


class TestLiveCodeSession(unittest.TestCase):
    """Test the LiveCodeSession integration."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary test file
        self.temp_file = tempfile.NamedTemporaryFile(
            mode='w', 
            suffix='.py', 
            delete=False
        )
        self.temp_file.write("""
x = 100
y = 200
print(f"Values: x={x}, y={y}")
""")
        self.temp_file.close()
        self.temp_filepath = self.temp_file.name
    
    def tearDown(self):
        """Clean up test fixtures."""
        try:
            os.unlink(self.temp_filepath)
        except:
            pass
    
    def test_live_session_creation(self):
        """Test creating live code session."""
        session = LiveCodeSession(backend='console')
        
        self.assertIsNotNone(session.engine)
        self.assertIsNotNone(session.monitor)
        self.assertEqual(len(session.active_files), 0)
        
        session.stop_session()
    
    def test_add_file_to_session(self):
        """Test adding file to live session."""
        session = LiveCodeSession(backend='console')
        
        success = session.add_file(self.temp_filepath)
        
        self.assertTrue(success)
        self.assertIn(self.temp_filepath, session.active_files)
        self.assertGreater(session.session_stats['files_processed'], 0)
        
        # Engine should have executed the file
        self.assertIn('x', session.engine.variables)
        self.assertEqual(session.engine.variables['x'], 100)
        
        session.stop_session()
    
    def test_live_session_file_change(self):
        """Test live session responding to file changes."""
        session = LiveCodeSession(backend='console')
        session.add_file(self.temp_filepath)
        
        # Simulate file change
        new_content = """
x = 500
y = 600
print("Updated values!")
"""
        
        event = FileChangeEvent(
            filepath=self.temp_filepath,
            event_type='modified',
            timestamp=time.time(),
            new_content=new_content
        )
        
        session._on_file_change(event)
        
        # Engine should have updated variables
        self.assertEqual(session.engine.variables['x'], 500)
        self.assertEqual(session.engine.variables['y'], 600)
        
        session.stop_session()
    
    def test_session_statistics(self):
        """Test session statistics tracking."""
        session = LiveCodeSession(backend='console')
        session.add_file(self.temp_filepath)
        
        # Check initial statistics
        self.assertGreater(session.session_stats['files_processed'], 0)
        self.assertGreater(session.session_stats['total_executions'], 0)
        self.assertGreater(session.session_stats['session_start_time'], 0)
        
        session.stop_session()


class TestLiveMonitorFunction(unittest.TestCase):
    """Test the live_monitor convenience function."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary test file
        self.temp_file = tempfile.NamedTemporaryFile(
            mode='w', 
            suffix='.py', 
            delete=False
        )
        self.temp_file.write("print('Hello from live monitor!')")
        self.temp_file.close()
        self.temp_filepath = self.temp_file.name
    
    def tearDown(self):
        """Clean up test fixtures."""
        try:
            os.unlink(self.temp_filepath)
        except:
            pass
    
    def test_live_monitor_function(self):
        """Test live_monitor convenience function."""
        # This test just verifies the function can be called
        # without starting the actual monitoring loop
        
        with patch('visualpython.monitor.LiveCodeSession') as mock_session_class:
            mock_session = Mock()
            mock_session.add_file.return_value = True
            mock_session_class.return_value = mock_session
            
            # Call function
            result = live_monitor(self.temp_filepath, backend='console')
            
            # Verify session was created and configured
            mock_session_class.assert_called_once_with(backend='console')
            mock_session.add_file.assert_called_once_with(self.temp_filepath)
    
    def test_live_monitor_invalid_file(self):
        """Test live_monitor with invalid file."""
        with patch('visualpython.monitor.LiveCodeSession') as mock_session_class:
            mock_session = Mock()
            mock_session.add_file.return_value = False
            mock_session_class.return_value = mock_session
            
            # Call function with non-existent file
            result = live_monitor("/nonexistent/file.py", backend='console')
            
            # Should still return session even if file add failed
            self.assertEqual(result, mock_session)


if __name__ == '__main__':
    unittest.main()