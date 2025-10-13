"""
\file writetofillet.py
\brief Thin facade that forwards to the package CLI.
"""

import sys


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
