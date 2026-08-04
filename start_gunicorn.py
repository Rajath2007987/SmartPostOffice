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
    # On Windows, Gunicorn imports `fcntl` (POSIX-only) and will fail.
    if sys.platform.startswith("win") or os.name == "nt":
        print("Detected Windows: falling back to Flask dev server (use WSL/Docker for production-like testing).")
        os.execvp(sys.executable, [sys.executable, "app.py"])

    # Prefer Waitress on Render (pure-Python WSGI server, avoids gunicorn/pkg_resources issues)
    try:
        # Importing here after packages are ensured to avoid early imports during build
        from waitress import serve
        import wsgi as _wsgi

        host = "0.0.0.0"
        port = int(os.environ.get("PORT", os.environ.get("RENDER_PORT", 8000)))
        print(f"Starting Waitress on {host}:{port}")
        serve(_wsgi.app, host=host, port=port)
    except Exception:
        # Fallback to gunicorn if waitress isn't available or fails for any reason
        os.execvp(sys.executable, [sys.executable, "-m", "gunicorn", "wsgi:app"]) 

if __name__ == '__main__':
    main()
