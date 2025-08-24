import argparse
from .monitor import create_live_session, live_monitor

def main():
    """CLI entry point for VisualPython."""
    parser = argparse.ArgumentParser(
        description="VisualPython - Execute Python files visually without compilation"
    )
    subparsers = parser.add_subparsers(dest='command')

    # Run command
    run_parser = subparsers.add_parser('run', help='Run a Python file once')
    run_parser.add_argument('file', help='Python file to execute')
    run_parser.add_argument('--backend', choices=['tkinter'], default='tkinter', help='Visual backend')
    run_parser.add_argument('--width', type=int, default=800, help='Display width')
    run_parser.add_argument('--height', type=int, default=600, help='Display height')

    # Live command
    live_parser = subparsers.add_parser('live', help='Monitor a Python file for live updates')
    live_parser.add_argument('file', help='Python file to monitor')
    live_parser.add_argument('--backend', choices=['tkinter'], default='tkinter', help='Visual backend')
    live_parser.add_argument('--width', type=int, default=800, help='Display width')
    live_parser.add_argument('--height', type=int, default=600, help='Display height')
    live_parser.add_argument('--interval', type=float, default=0.1, help='File check interval in seconds')

    args = parser.parse_args()

    if args.command == 'run':
        from .core import VisualPythonEngine
        engine = VisualPythonEngine(backend=args.backend, width=args.width, height=args.height)
        with open(args.file, 'r', encoding='utf-8') as f:
            code = f.read()
        engine.execute(code)
        engine.renderer.root.mainloop()
    elif args.command == 'live':
        session = live_monitor(args.file, backend=args.backend, width=args.width, height=args.height)
        session.monitor.check_interval = args.interval
    else:
        parser.print_help()
