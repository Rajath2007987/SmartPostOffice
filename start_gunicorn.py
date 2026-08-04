#!/usr/bin/env python3
"""Start shim for Render: ensure setuptools is installed before importing gunicorn.

This script installs/updates setuptools, wheel and packaging using the same
interpreter, then replaces the current process with gunicorn serving `wsgi:app`.
Using this prevents `ModuleNotFoundError: No module named 'pkg_resources'` when
gunicorn imports pkg_resources early.
"""
import sys
import os
import subprocess

def ensure_pkg():
    cmd = [sys.executable, "-m", "pip", "install", "-U", "--force-reinstall", "setuptools", "wheel", "packaging"]
    subprocess.check_call(cmd)

def main():
    ensure_pkg()
    # exec gunicorn with same interpreter so paths match
    os.execvp(sys.executable, [sys.executable, "-m", "gunicorn", "wsgi:app"]) 

if __name__ == '__main__':
    main()
