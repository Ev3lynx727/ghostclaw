#!/usr/bin/env python3
"""
Ghostclaw CLI — modular command dispatcher with legacy fallback.
"""

import sys
import argparse
import asyncio
from pathlib import Path

from ghostclaw.cli import __version__
from ghostclaw.cli.commander.registry import registry


def main():
    """Main entry point — auto-discovers and executes commands."""
    
    # Auto-discover commands from the commands package
    try:
        registry.auto_discover()
    except Exception as e:
        # registry logs warnings, continue
        pass

    # Build argument parser dynamically from registry
    parser = argparse.ArgumentParser(
        prog="ghostclaw",
        description="Ghostclaw — Architectural Code Review Assistant"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"Ghostclaw {__version__}"
    )
    
    subparsers = parser.add_subparsers(
        dest="command",
        metavar="<command>",
        help="Available commands"
    )
    
    # Register all discovered commands
    for cmd_cls in sorted(registry.all(), key=lambda c: c.__name__):
        try:
            cmd = cmd_cls()
            subparser = subparsers.add_parser(
                cmd.name,
                description=cmd.description,
                help=cmd.description
            )
            cmd.configure_parser(subparser)
        except Exception as e:
            print(f"Warning: failed to register command {cmd_cls.__name__}: {e}", file=sys.stderr)
    
    # Backward compatibility: if first arg is an existing directory path, default to 'analyze'
    if len(sys.argv) > 1 and not sys.argv[1].startswith('-'):
        potential_path = Path(sys.argv[1])
        if potential_path.is_dir() and sys.argv[1] not in registry._commands:
            sys.argv.insert(1, "analyze")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Try to get the command from the registry
    cmd_cls = registry.get(args.command)
    if cmd_cls:
        # Modular path — use the new command class
        cmd = cmd_cls()
        try:
            return asyncio.run(cmd.execute(args))
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            if getattr(args, 'verbose', False):
                import traceback
                traceback.print_exc()
            return 1
    
    # LEGACY FALLBACK: Command not found in registry
    print("Warning: Using legacy CLI mode...", file=sys.stderr)
    print(f"Error: Command '{args.command}' not available in modular CLI.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
