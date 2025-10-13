"""
\file writetofillet.py
\brief Thin facade that forwards to the package CLI and exposes submodules.
"""

import os
import sys

# Treat this module as a package by defining __path__ to the real package under src/
_here = os.path.dirname(__file__)
__path__ = [os.path.join(_here, "src", "writetofillet")]

# Re-export package metadata for code that imports from writetofillet
try:
    import importlib

    _pkg = importlib.import_module("writetofillet.__init__")
    __version__ = getattr(_pkg, "__version__", "0.0.0")
    REPO_URL = getattr(_pkg, "REPO_URL", "")
except Exception:  # pragma: no cover
    __version__ = "0.0.0"
    REPO_URL = ""


def main(argv=None):
    """Facade entrypoint.

    \param argv Optional list of arguments (defaults to sys.argv[1:]).
    \return Process exit code from the real CLI.
    """
    try:
        from writetofillet.cli import main as runner
    except Exception as e:
        print(f"Failed to import writetofillet CLI: {e}", file=sys.stderr)
        return 1
    args = list(sys.argv[1:] if argv is None else argv)
    return runner(args)


if __name__ == "__main__":
    raise SystemExit(main())
