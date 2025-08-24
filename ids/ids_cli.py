# ids_cli.py
import argparse, sys, signal
from ids_csv import CSVSession
from adapters.screen2csv import run_screen_to_csv

def main():
    ap = argparse.ArgumentParser(prog="ids", description="Intelligent Display Stack — screen→CSV")
    sub = ap.add_subparsers(dest="cmd", required=True)

    rec = sub.add_parser("record", help="Record a window to CSV via screen capture")
    rec.add_argument("--title", required=True, help="Substring of the window title to capture")
    rec.add_argument("--fps", type=int, default=30)
    rec.add_argument("--tile", type=int, default=8, help="Tile size in pixels (e.g., 4/8/16)")
    rec.add_argument("--thresh", type=float, default=10.0, help="Per-tile RGB delta threshold")
    rec.add_argument("--max-rects", type=int, default=400, help="Cap rects per frame")
    rec.add_argument("--out", required=True, help="Output CSV path")

    args = ap.parse_args()

    if args.cmd == "record":
        sess = CSVSession(args.out)
        def _shutdown(sig, frm):
            try: sess.close()
            finally: sys.exit(0)
        for s in (signal.SIGINT, signal.SIGTERM, signal.SIGBREAK if hasattr(signal, "SIGBREAK") else signal.SIGTERM):
            signal.signal(s, _shutdown)

        try:
            run_screen_to_csv(sess, args.title, args.fps, args.tile, args.thresh, args.max_rects)
        finally:
            sess.close()

if __name__ == "__main__":
    main()
