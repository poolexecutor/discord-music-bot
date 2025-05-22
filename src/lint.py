#!/usr/bin/env python3
"""Lint script for the Discord Music Bot project.

This script runs the linting tools configured in pyproject.toml:
- black: Code formatter
- ruff: Fast Python linter
- mypy: Static type checker

Usage:
    python src/lint.py [--check] [--fix]

Options:
    --check: Only check for issues without fixing them
    --fix: Automatically fix issues where possible
"""

import argparse
import subprocess
import sys
from pathlib import Path


def check_tool_installed(tool):
    """Check if a command-line tool is installed."""
    try:
        subprocess.run([tool, "--version"], capture_output=True, check=False)
        return True
    except FileNotFoundError:
        return False


def run_command(cmd, description):
    """Run a shell command and print its output."""
    print(f"\n=== Running {description} ===")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(f"Errors:\n{result.stderr}")
    return result.returncode


def main():
    """Run linting tools on the project."""
    parser = argparse.ArgumentParser(description="Run linting tools on the project")
    parser.add_argument(
        "--check", action="store_true", help="Only check for issues without fixing them"
    )
    parser.add_argument(
        "--fix", action="store_true", help="Automatically fix issues where possible"
    )
    parser.add_argument("--install", action="store_true", help="Install missing linting tools")
    args = parser.parse_args()

    # Get the project root directory
    project_root = Path(__file__).parent.parent.absolute()

    # Change to the project root directory
    import os

    os.chdir(project_root)

    # Check if required tools are installed
    missing_tools = []
    for tool in ["black", "ruff", "mypy"]:
        if not check_tool_installed(tool):
            missing_tools.append(tool)

    if missing_tools:
        print(f"\n❌ The following tools are not installed: {', '.join(missing_tools)}")
        print("\nTo install the missing tools, run:")
        print("pip install " + " ".join(missing_tools))

        if args.install:
            print("\nInstalling missing tools...")
            install_cmd = "pip install " + " ".join(missing_tools)
            run_command(install_cmd, "pip install")
            # Recheck if tools are installed
            missing_tools = [tool for tool in missing_tools if not check_tool_installed(tool)]
            if missing_tools:
                print(f"\n❌ Failed to install: {', '.join(missing_tools)}")
                return 1
            print("\n✅ All tools installed successfully!")
        else:
            print("\nOr run this script with --install to install them automatically:")
            print(f"python {sys.argv[0]} --install")
            return 1

    # Track exit code
    exit_code = 0

    # Run black
    if check_tool_installed("black"):
        black_cmd = "black ."
        if args.check:
            black_cmd += " --check"
        black_exit = run_command(black_cmd, "black (code formatter)")
        exit_code = exit_code or black_exit

    # Run ruff
    if check_tool_installed("ruff"):
        ruff_cmd = "ruff check ."
        if args.fix:
            ruff_cmd += " --fix"
        ruff_exit = run_command(ruff_cmd, "ruff (linter)")
        exit_code = exit_code or ruff_exit

    # Run mypy
    if check_tool_installed("mypy"):
        mypy_cmd = "mypy src"
        mypy_exit = run_command(mypy_cmd, "mypy (type checker)")
        exit_code = exit_code or mypy_exit

    # Print summary
    if exit_code == 0:
        print("\n✅ All checks passed!")
    else:
        print("\n❌ Some checks failed. See above for details.")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
