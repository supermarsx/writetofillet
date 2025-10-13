# Examples

This directory contains sample configuration files for using `writetofillet` with `--config`.

Quick starts
- TOML: `writetofillet --config examples/config.toml out.txt`
- JSON: `writetofillet --config examples/config.json out.bin`
- YAML: `writetofillet --config examples/config.yaml out.txt`

Notes
- CLI flags always override values loaded from the config file.
- YAML requires PyYAML to be installed. TOML uses Python 3.11+ `tomllib` (or `tomli` when available).
- The positional path (e.g., `out.txt`) is still required; use `--filelist` or pass a directory path to pump multiple files.
- For dictionary mode across multiple lists, prefer `--dict-ram` for non-sequential orders.

