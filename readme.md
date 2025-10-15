<img width="1536" height="1024" alt="20251015_1313_Cyberpunk Tuna Fillet_simple_compose_01k7kwj05de0m99krbdavj722n" src="https://github.com/user-attachments/assets/4e2dccc3-9c9b-497d-b2a4-ddf85a0c2b55" />

[![Format](https://github.com/supermarsx/writetofillet/actions/workflows/format.yml/badge.svg)](https://github.com/supermarsx/writetofillet/actions/workflows/format.yml)
[![Lint](https://github.com/supermarsx/writetofillet/actions/workflows/lint.yml/badge.svg)](https://github.com/supermarsx/writetofillet/actions/workflows/lint.yml)
[![Test](https://github.com/supermarsx/writetofillet/actions/workflows/test.yml/badge.svg)](https://github.com/supermarsx/writetofillet/actions/workflows/test.yml)
[![Build](https://github.com/supermarsx/writetofillet/actions/workflows/build.yml/badge.svg)](https://github.com/supermarsx/writetofillet/actions/workflows/build.yml)
[![Release](https://github.com/supermarsx/writetofillet/actions/workflows/release.yml/badge.svg)](https://github.com/supermarsx/writetofillet/actions/workflows/release.yml)
[![Coverage](https://raw.githubusercontent.com/supermarsx/writetofillet/refs/heads/main/badges/coverage.svg)](https://raw.githubusercontent.com/supermarsx/writetofillet/refs/heads/main/badges/coverage.svg)
[![Stars](https://img.shields.io/github/stars/supermarsx/writetofillet.svg)](https://github.com/supermarsx/writetofillet/stargazers)
[![Forks](https://img.shields.io/github/forks/supermarsx/writetofillet.svg)](https://github.com/supermarsx/writetofillet/fork)
[![Watchers](https://img.shields.io/github/watchers/supermarsx/writetofillet.svg)](https://github.com/supermarsx/writetofillet/watchers)
[![Issues](https://img.shields.io/github/issues/supermarsx/writetofillet.svg)](https://github.com/supermarsx/writetofillet/issues)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](license.md)
[![Downloads](https://img.shields.io/github/downloads/supermarsx/writetofillet/total.svg)](https://github.com/supermarsx/writetofillet/releases)
[![Commit Activity](https://img.shields.io/github/commit-activity/m/supermarsx/writetofillet.svg)](https://github.com/supermarsx/writetofillet/graphs/code-frequency)
[![Made with Python](https://img.shields.io/badge/Made%20with-Python-blue.svg)](https://www.python.org/)

A fast, multithreaded file pumper for generating large files on demand. It can write text or binary data by count or target size, append to existing files or overwrite, and operate across multiple targets (a file, a whole folder, or a file list). It supports RAM-buffered dumps or streaming writes with guardrails for memory and disk space, plus progress, throttling, sparse files, and periodic fsync for safer workloads. Built as a pure CLI, it’s cross‑platform and tuned with a built‑in benchmark to suggest optimal chunk size, concurrency, and threading model.
- Repeat a word N times or pump until target size.
- Dictionary mode: sequential, reverse, random, presorted (multiple dictionaries supported).
- Pumping modes: word, bin1, bin0, randbin, randutf8, randhex, random.
- Encoding: auto‑detect or choose (utf‑8, utf‑16/le/be, utf‑32, latin‑1, cp1252, ascii, shift_jis, gb18030).

## Why / Use Cases
- Storage/load testing: generate large files quickly to exercise disks and filesystems.
- Benchmarking: compare throughput across chunk sizes, thread counts, and modes.
- CI fixtures: create reproducible data sets of exact sizes for pipelines.
- Data simulation: produce dictionary-driven or random text/binary streams.
- Space management: preallocate files (with sparse support) to test quotas/alerts.
- Robustness checks: throttle, fsync, and multi-target writes to validate apps under stress.

## Limitations
- Sparse files depend on filesystem/OS support; behavior varies by platform.
- Fsync and small intervals can significantly reduce throughput.
- Rate limiting and progress use coarse timing; values are approximate.
- Size estimation is exact only when token size is known; dictionary/random modes or char-newline scopes may vary.
- RAM buffer mode forces single-thread and may refuse large buffers per `--ram-max`.
- Global disk guard sums per-target expected sizes; bypass with `--disable-disk-guard` if you know the risks.
- Update check and badges require network access in CI.

Legacy `writetofillet` usage is still supported via a thin wrapper.

## Install & Run

- Local install (dev): `pip install -e .`
- Console command: `writetofillet --help`
- Run from source (without install): `PYTHONPATH=src python -m writetofillet --help`
- Build single binary: `pyinstaller --onefile -n writetofillet src/writetofillet/cli.py`

- One-click scripts (from repo root):
  - Unix/macOS: `scripts/install.sh`, `scripts/update.sh`, `scripts/package.sh`
  - Windows: `scripts\install.bat`, `scripts\update.bat`, `scripts\package.bat`

### Homebrew (macOS/Linux)
- Tap and install (using tap `supermarsx/tap` once created):
```
brew tap supermarsx/tap
brew install writetofillet
```
- Alternatively, install directly from a raw formula file:
```
brew install https://raw.githubusercontent.com/supermarsx/writetofillet/refs/heads/main/Formula/writetofillet.rb
```

### Scoop (Windows)
- Add bucket and install (using bucket in this repo path):
```
scoop bucket add supermarsx https://github.com/supermarsx/writetofillet
scoop install writetofillet
```
- Or install straight from a manifest URL:
```
scoop install https://raw.githubusercontent.com/supermarsx/writetofillet/refs/heads/main/bucket/writetofillet.json
```

## Quick Examples
```
# 1) Fast sparse binary preallocation (10GiB image)
writetofillet --write-mode binary-write --pump-mode bin0 --size 10GiB \
  --sparse --fallocate 10GiB big.img

# 2) Durable text append, one line per token, fsync enabled
writetofillet --write-mode normal-append --word EVENT --times 100000 \
  --newline-mode word --fsync-enable --fsync-interval 8MiB events.log

# 3) Dictionary-driven random with weights + Markov (N=3)
writetofillet --dict-list examples/wordlists.txt --dict-ram \
  --dict-order random --markov --ngram 3 --times 10000 --newline-mode word corpus.txt

# 4) Pump every file under a directory (recursive), 100MiB each
writetofillet --write-mode binary-append --pump-mode randbin --size 100MiB \
  --recursive ./data/

# 5) Large binary with hashing + verification (1GiB)
writetofillet --write-mode binary-write --pump-mode randbin --size 1GiB \
  --hash sha256 --verify out.bin

# 6) Throttled printable UTF-8 with CPU limit and progress (200MiB)
writetofillet --pump-mode randutf8 --size 200MiB \
  --rate 5MiB --cpu-limit 150 --progress out.txt
```

## CLI Reference

- `path` (positional)
  - Target file to create/append. Parent directories are created as needed.
  - Example: `out/data.bin`
  
- `--encoding ENC|auto`
  - Text encoding for word/dictionary modes. Default `utf-8`. `auto` detects dict file (UTF-8 else Latin-1).
  - Common encodings supported out of the box: `utf-8`, `utf-16`, `utf-16le`, `utf-16be`, `utf-32`, `latin-1` (iso-8859-1), `cp1252`, `ascii`, `shift_jis`, `gb18030`. Python codecs are also accepted.
- `--newline-mode {none|word|char}` and `--newline-style {lf|cr|crlf}`
  - Newline insertion control for text modes. Scope can be per word token or per character; style chooses line ending. Legacy `--newline` maps to `--newline-mode word`.
- `--times N`
  - Repeat token N times. Guarded by `--max-times`.
- `--times-range MIN,MAX`
  - Choose a random repetition count in the inclusive range `[MIN, MAX]`.
  - Supports power/scientific notation: `2^20`, `1e6`, underscores.
- `--size SIZE`
  - Target total size (bytes). Supports `KiB/MiB/GiB` and `KB/MB/GB`.
  - Also accepts `B`/`bytes` and `TB` for terabytes.
- `--max-bytes SIZE`
  - Hard stop regardless of other limits. Takes precedence over `--size`.
- `--word TEXT`
  - Word/token to write (text). Required in `--pump-mode word` when `--dict` is not used.
- `--dict PATH`
  - Wordlist file (newline-separated). Used with `--dict-order`.
- `--dict-list PATH`
  - A file containing newline-separated dictionary file paths (relative to the list file or absolute). Combined with `--dict` if both are provided.
  - Non-sequential orders (`reverse`, `presorted`, `random`) require `--dict-ram` so all dictionaries are loaded into memory.
- `--dict-order {sequential|reverse|random|presorted}`
  - Selection order for dictionary tokens. Default `random`.
- `--dict-ram`
  - Load dictionary file into RAM. Required for non-sequential orders; streaming only supports sequential.
- `--pump-mode {word|bin1|bin0|randbin|randutf8|randhex|random}`
  - Generation mode. `random` picks among other random modes per chunk.
- `--write-mode {normal-append|normal-write|binary-append|binary-write}`
  - Convenience switch that sets append/write and defaults the data mode:
    - normal-* defaults `--pump-mode word` (text) unless explicitly set.
    - binary-* defaults `--pump-mode randbin` (binary) unless explicitly set.
  - `*-append` sets append; `*-write` sets overwrite. This replaces `--append/--overwrite`.
- `--mode {fixed|random}`
  - Applies to `word` mode: fixed uses the same token; random varies per write.
- `--workers N`
  - Number of writer threads. Default `1`.
- `--chunk SIZE`
  - Chunk size for buffered writes. Default `64KiB`.
- `--seed SEED`
  - Random seed for reproducibility in random/dictionary selection.
- `--concurrency {write|generate}`
  - Choose where to apply parallelism: multiple writers (default) or multiple generators feeding a single writer.
- `--gen-workers N`
  - Number of generator threads when using `--concurrency generate`. Default `1`.
- `--benchmark`, `--bench-size SIZE`
  - Runs a quick local benchmark (writes temp files) to suggest optimal `--chunk`, `--concurrency`, and `--workers`/`--gen-workers`. Default size: `64MiB`.
- `--rate BYTES/S`
  - Throttle overall throughput (bytes/sec). In multithread mode, shared across workers.
- `--cpu-limit PCT`
  - Approximate CPU throttling. Limits process CPU usage using coarse timing (percent is relative to total CPU across cores).
- `--max-times N`
  - Upper guard for `--times` to avoid accidental huge writes. Default `10,000,000`.
- `--disable-disk-guard`
  - Disable free-disk-space guardrail. Warning is printed when disabled; writes may fail or fill disk if insufficient space.
- `--disk-guard-margin SIZE`
  - Additional free space required beyond the expected output size (default `100MiB`). Helps avoid filling disks in edge cases.
  - The tool performs a global upfront estimate per filesystem/device (summing expected sizes across targets) and a per-target check. Both respect the margin.
- `--progress`
  - Show periodic progress (bytes, percent, rate, ETA) to stderr.
- `--progress-interval SEC`
  - Seconds between progress updates. Default `1.0`.
- `--buffer-mode {ram|stream}`
  - ram: build in memory then dump (default); stream: write progressively to avoid large memory usage.
- `--ram-max SIZE`
  - Maximum RAM buffer before refusal/fallback. Default `256MiB`. If target exceeds, the tool auto-streams.
- `--fsync-enable`, `--fsync-interval SIZE`
  - Enable periodic flush+fsync. When enabled, defaults to `8MiB` unless overridden by `--fsync-interval`. Small intervals can significantly reduce throughput.
- `--sparse`
  - Attempts to create sparse files where supported. On Windows/NTFS, marks files as sparse; on other systems, zero-only chunks may be skipped (creating holes). Actual sparseness depends on filesystem support.
- `--ram-limit SIZE`
  - Abort if process RSS exceeds this size (best effort; requires `psutil` if available).
- `--hash {md5|sha1|sha256|sha512}`, `--verify`
  - Compute a running hash while writing and optionally verify by re-reading the file (non-compressed only). Prints an error if verification fails.
- `--io-retries N`, `--error-budget N`
  - Retry transient I/O errors per chunk up to N times; abort once error budget is exceeded. Default error budget is 10.
- `--resume`, `--offset BYTES`
  - Resume continues size-bound writes from the end of file; `--offset` seeks to a byte offset before writing (overrides resume).
- `--truncate SIZE`, `--fallocate SIZE`
  - Truncate the file before writing or preallocate space (uses `posix_fallocate`/`ftruncate` where available).
- `--compress gzip`
  - Gzip-compress output (forces single-writer mode). Use `-` as path to stream to stdout (named pipes supported).
- `--recursive`
  - When the positional path is a directory, recurse into subdirectories and pump all files.

- `-V`, `--version`
  - Print version and link to latest rolling release, then exit.
- `--release-link`
  - Print the latest rolling release URL and exit.
- `--check-updates`
  - Query GitHub for the latest rolling release and print the tag/URL.
- `--log-level`, `--log-file`
  - Configure logging verbosity and optional log file output.
- `--config PATH`
  - Load CLI defaults from a config file (`.toml`, `.json`, `.yaml/.yml`). CLI args override config values.

## Write Modes
- normal-append: Appends text tokens to the end of the file. Defaults `--pump-mode word` (unless explicitly set).
- normal-write: Truncates the file first, then writes text tokens. Defaults `--pump-mode word`.
- binary-append: Appends binary chunks to the file. Defaults `--pump-mode randbin`.
- binary-write: Truncates the file, then writes binary chunks. Defaults `--pump-mode randbin`.

Use `--write-mode` for convenience; you can still override the generator via `--pump-mode`.

## Pump Modes
- word: Encodes `--word` or dictionary tokens using `--encoding`. Combine with `--mode fixed|random` and newline options.
- bin1: Fills with 0xFF bytes.
- bin0: Fills with 0x00 bytes.
- randbin: Cryptographically random bytes (os.urandom).
- randutf8: Random printable UTF-8 text.
- randhex: Hex characters of random bytes.
- random: Randomly picks among other random modes per chunk.

### Throttling & Limits
- Write: `--rate` for throughput, `--fsync-enable`/`--fsync-interval` for durability.
- CPU: `--cpu-limit PCT` uses coarse process time to limit CPU usage.
- RAM: `--ram-max` limits buffer mode; `--ram-limit` aborts if process RSS grows beyond the limit.

- `--filelist PATH`
  - A file containing newline-separated file paths (relative to the filelist location or absolute). Each target file is pumped sequentially.
  - If the positional `path` is a directory, all files within that directory are also pumped (non-recursive).

General notes
- Human-readable sizes: `KB/MB/GB` or `KiB/MiB/GiB`.
- Encoding `auto` tries UTF-8, falls back to Latin-1.
 - Sizes also support `B/bytes` and `TB`.

Notes on buffering behavior
- RAM mode forces single-thread to avoid excessive memory usage.
- If expected output exceeds `--ram-max`, the tool automatically falls back to streaming and prints an info message.

Version and releases
- Show version and rolling release link: `writetofillet --version`
- Show latest rolling release URL only: `writetofillet --release-link`

 

## Contributing
- See `agents.md` for development guidelines.
- PRs should include rationale, usage examples, and updated docs when behavior changes.

## Releases
- Rolling versioning: `yy.N` (two-digit year, then incremental per year).
- Example: first release in 2025 is `25.1`, then `25.2`, etc.

## License
- Licensed under the MIT License. See `license.md` for full text.
