#!/usr/bin/env python3
"""
Scrolls CLI
-----------
The main command-line interface for interacting with the Scrolls synchronization system.
"""
import argparse
import scrolls_local
from typing import Dict, Any

def handle_init(args):
    """Handler for the 'init' subcommand."""
    scrolls_local.init_manifest()

def handle_status(args):
    """Handler for the 'status' subcommand."""
    manifest = scrolls_local.read_manifest()
    if manifest:
        print("Project Status:")
        print(f"  Project Name: {manifest.get('project_name', 'N/A')}")
        print(f"  Version: {manifest.get('version', 'N/A')}")

        files = manifest.get("files", {})
        if not files:
            print("  No files are currently tracked in the manifest.")
        else:
            print(f"  Tracked Files ({len(files)}):")
            for path, details in files.items():
                modified_time = details.get('last_modified', 'N/A')
                checksum = details.get('checksum', 'N/A')
                print(f"    - {path}")
                print(f"      Modified: {modified_time}")
                print(f"      Checksum: {checksum[:12]}...")

def main():
    """
    Main function to set up and run the CLI.
    """
    parser = argparse.ArgumentParser(
        description="Scrolls: A distributed, self-correcting file synchronization system."
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        help="Available subcommands"
    )

    # 'init' subcommand
    parser_init = subparsers.add_parser(
        "init",
        help="Initialize a new scrolls project in the current directory."
    )
    parser_init.set_defaults(func=handle_init)

    # 'status' subcommand
    parser_status = subparsers.add_parser(
        "status",
        help="Show the current status of the project and tracked files."
    )
    parser_status.set_defaults(func=handle_status)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
