"""PyInstaller entrypoint for the writetofillet console binary."""

from writetofillet.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
