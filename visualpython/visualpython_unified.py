#!/usr/bin/env python3
"""
VisualPython Unified CLI

Extended version of the VisualPython CLI that includes:
- Headless simulator backend for testing and automation
- CSV recording and playback for frame-based visualization
- Multiple backend support (tk, sim, console)
- Full round-trip workflow support

Usage:
    python visualpython_unified.py run script.py --backend sim
    python visualpython_unified.py csv play data.csv --backend sim
    python visualpython_unified.py csv record script.py --csv-out recording.csv
"""

import argparse
import os
import sys
import time
from pathlib import Path
from threading import Thread

# Add src directory to path for imports
current_dir = Path(__file__).parent
src_path = current_dir / "src"
sys.path.insert(0, str(src_path))

try:
    from visualpython.core import VisualPythonEngine
    from visualpython.backends import create_backend, csv_play, RecordRenderer
except ImportError as e:
    print(f"❌ Failed to import VisualPython modules: {e}")
    print("Make sure you're running this from the VisualPython directory")
    sys.exit(1)


def add_common_args(parser):
    """Add common arguments to a subparser."""
    parser.add_argument("--width", type=int, default=800, help="Display width")
    parser.add_argument("--height", type=int, default=600, help="Display height")
    parser.add_argument("--backend", choices=["tkinter", "simulator", "sim", "console"], 
                       default="tkinter", help="Rendering backend")
    parser.add_argument("--out-dir", default="vp_sim_frames", 
                       help="Output directory for simulator frames")
    parser.add_argument("--mirror", help="Mirror all operations to CSV file")
    parser.add_argument("--live", action="store_true", 
                       help="Watch file for changes and auto-reload")


def watch_file(file_path, callback, interval=0.5):
    """
    Watch a file for changes and trigger callback when modified.
    Simple polling-based approach that works everywhere.
    """
    file_path = Path(file_path)
    last_mtime = 0
    
    print(f"👀 Watching {file_path} for changes... (Ctrl+C to stop)")
    
    while True:
        try:
            if file_path.exists():
                mtime = file_path.stat().st_mtime
                if mtime != last_mtime:
                    last_mtime = mtime
                    print(f"🔄 File changed, reloading...")
                    callback()
            time.sleep(interval)
        except KeyboardInterrupt:
            print("\n✅ Stopped watching")
            break
        except Exception as e:
            print(f"⚠️  Watch error: {e}")
            time.sleep(interval)


def run_command(args):
    """Execute a Python file once with visual output."""
    if not os.path.exists(args.file):
        print(f"❌ Error: File {args.file} not found")
        return 1
    
    print(f"🔥 Running {args.file} with VisualPython...")
    
    def execute_once():
        try:
            # Create engine with optional CSV recording
            engine = VisualPythonEngine(
                backend=args.backend,
                width=args.width,
                height=args.height,
                out_dir=getattr(args, 'out_dir', 'vp_sim_frames')
            )
            
            # Wrap with recorder if mirror is specified
            if hasattr(args, 'mirror') and args.mirror:
                engine.backend = RecordRenderer(engine.backend, args.mirror)
            
            with open(args.file, 'r', encoding='utf-8') as f:
                code = f.read()
            
            execution_time = engine.execute(code)
            
            print(f"✅ Executed in {execution_time:.2f}ms")
            
            # Keep window open for interactive backends (only on first run)
            if not args.live and hasattr(engine.backend, 'root'):
                try:
                    engine.backend.root.mainloop()
                except KeyboardInterrupt:
                    print("\n👋 Goodbye!")
            
            engine.cleanup()
            return 0
            
        except Exception as e:
            print(f"❌ Error executing {args.file}: {e}")
            return 1
    
    if args.live:
        # Initial execution
        execute_once()
        # Watch for changes
        watch_file(args.file, execute_once)
        return 0
    else:
        return execute_once()


def csv_play_command(args):
    """Play a CSV file frame by frame."""
    if not os.path.exists(args.csvfile):
        print(f"❌ Error: CSV file {args.csvfile} not found")
        return 1
    
    print(f"🎬 Playing CSV: {args.csvfile}")
    
    def play_once():
        try:
            # Create renderer directly
            backend = create_backend(
                args.backend,
                width=args.width,
                height=args.height,
                out_dir=args.out_dir
            )
            
            # Play the CSV
            csv_play(backend, args.csvfile, frame_delay=args.frame_delay)
            
            print("✅ CSV playback complete")
            return 0
            
        except Exception as e:
            print(f"❌ Error playing CSV: {e}")
            return 1
    
    if getattr(args, 'live', False):
        # Initial playback
        play_once()
        # Watch for changes
        watch_file(args.csvfile, play_once)
        return 0
    else:
        return play_once()


def csv_record_command(args):
    """Record a script execution to CSV."""
    if not os.path.exists(args.script):
        print(f"❌ Error: Script {args.script} not found")
        return 1
    
    print(f"🎥 Recording {args.script} to {args.csv_out}")
    
    try:
        # Create engine
        engine = VisualPythonEngine(
            backend=args.backend,
            width=args.width,
            height=args.height,
            out_dir=args.out_dir
        )
        
        # Wrap with recorder
        engine.backend = RecordRenderer(engine.backend, args.csv_out)
        
        with open(args.script, 'r', encoding='utf-8') as f:
            code = f.read()
        
        execution_time = engine.execute(code)
        
        print(f"✅ Recorded in {execution_time:.2f}ms")
        print(f"📁 CSV saved to: {args.csv_out}")
        
        # Clean up
        engine.backend.close()
        return 0
        
    except Exception as e:
        print(f"❌ Error recording: {e}")
        return 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="VisualPython Unified - Direct visual execution with simulator support",
        epilog="Examples:\n"
               "  python visualpython_unified.py run script.py --backend sim\n"
               "  python visualpython_unified.py csv play data.csv --backend sim\n"
               "  python visualpython_unified.py csv record script.py --csv-out demo.csv\n"
               "  python visualpython_unified.py run script.py --mirror recording.csv",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Run command
    run_parser = subparsers.add_parser('run', help='Execute a Python file once')
    run_parser.add_argument('file', help='Python file to execute')
    add_common_args(run_parser)
    run_parser.set_defaults(func=run_command)
    
    # CSV subcommands
    csv_parser = subparsers.add_parser('csv', help='CSV tools for recording and playback')
    csv_subparsers = csv_parser.add_subparsers(dest='csv_command', help='CSV operations')
    
    # CSV play
    play_parser = csv_subparsers.add_parser('play', help='Play a CSV file frame by frame')
    play_parser.add_argument('csvfile', help='CSV file to play')
    play_parser.add_argument('--frame-delay', type=float, default=0.0,
                            help='Delay between frames in seconds')
    add_common_args(play_parser)
    play_parser.set_defaults(func=csv_play_command)
    
    # CSV record
    record_parser = csv_subparsers.add_parser('record', help='Record script execution to CSV')
    record_parser.add_argument('script', help='Python script to record')
    record_parser.add_argument('--csv-out', default='vp_record.csv',
                              help='Output CSV file')
    add_common_args(record_parser)
    record_parser.set_defaults(func=csv_record_command)
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Handle CSV subcommands
    if args.command == 'csv':
        if not hasattr(args, 'csv_command') or not args.csv_command:
            csv_parser.print_help()
            return 1
    
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\n🛑 Operation cancelled")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())