# writetofillet — Specification

This document documents the current feature set, CLI surface, modes, configuration, internal behaviors, and examples for `writetofillet` based on the present code.

**Project summary**
- Small CLI utility to generate and write synthetic data to files or stdout.
- Supports text-word and several binary/random-generation modes, multiple buffering and concurrency models, and safety/limits (disk guard, RAM guard, error budgets).

**Quick invocation**
- `writetofillet [path] [OPTIONS]`
- If `path` is omitted or `-` is used, writes to stdout.

**Primary goals**
- Produce deterministic or random tokens or raw binary data.
- Support size-bound and count-bound writes.
- Provide configurable throughput, concurrency, and resource guards.

**High-level concepts**
- Pump mode: what kind of bytes are generated (word/dictionary vs random binary/text).
- Write mode: condensed presets (normal-append, normal-write, binary-append, binary-write).
- Buffering: either aggregate into RAM then dump, or stream directly to file/threads.
- Concurrency: writer threads (`--concurrency write`) or generator threads (`--concurrency generate`).

**CLI Options (surface)**
- Positional
  - `path` (optional): Target file or `-` for stdout. Defaults to `-`.

- I/O
  - `--encoding` (default `utf-8`): encoding for text tokens; `auto` attempts detection when reading a dictionary.
  - `--newline` (legacy): add newline after token; mapped to `--newline-mode word` if used.

- Workload
  - `--times N`: repeat tokens N times (count-bound mode).
  - `--times-range MIN,MAX`: choose random count between bounds.
  - `--size SIZE`: target size (human-parsed, e.g. `10MiB`).
  - `--max-bytes SIZE`: hard stop at this size regardless of other limits.

- Source
  - `--word WORD`: token to write for `pump-mode=word` when no dictionary is provided.
  - `--dict PATH`: path to a newline-separated wordlist.
  - `--dict-list PATH`: path listing multiple dictionary files (one per line); relative paths resolved against the list file.
  - `--dict-order {sequential,reverse,random,presorted}`: ordering when using dictionaries (default `random`).
  - `--dict-ram`: load dictionary files into RAM. Required for non-sequential multi-file orders.
  - `--markov`: enable a simple N-gram (Markov) generator from dictionaries (requires `--dict-ram`).
  - `--ngram N` (default 2): N for the N-gram model when `--markov` is set.

- Modes
  - `--write-mode {normal-append, normal-write, binary-append, binary-write}` (default `normal-append`): condensed presets that set append vs truncate and default pump-mode.
  - `--pump-mode {word, bin1, bin0, randbin, randutf8, randascii, randhex, random}` (default determined by `--write-mode`): generator mode.
  - `--mode {fixed, random}` (default `fixed`): whether a single token is emitted or varied.

- Performance
  - `--workers N` (default 1): number of writer threads (when using `--concurrency write`).
  - `--chunk SIZE` (default `64KiB`): chunk size used in buffered and random modes.
  - `--seed N`: random seed for reproducibility.
  - `--rate SIZE`: throttle to RATE bytes/sec.
  - `--cpu-limit PERCENT`: best-effort CPU usage limit per process.
  - `--concurrency {write, generate}` (default `write`): parallelize writers or generators.
  - `--gen-workers N` (default 1): number of generator threads when `--concurrency generate`.
  - `--benchmark`: run a local benchmark to recommend chunk/workers/concurrency.
  - `--bench-size SIZE` (default `64MiB`): bytes per benchmark run.
  - `--compress {none,gzip}` (default `none`): compress output; disables multi-writer threads when enabled.

- Buffering
  - `--buffer-mode {ram, stream}` (default `ram`): aggregate to RAM then dump, or stream directly to file.
  - `--ram-max SIZE` (default `256MiB`): max RAM to use in RAM buffering mode before falling back to streaming.
  - `--sparse`: attempt to create sparse files (skip zero chunks and mark sparse on supported filesystems; Windows sparse support attempted).

- Limits & Safety
  - `--max-times N` (default 10_000_000): guardrail for `--times`.
  - `--disable-disk-guard`: disable global per-device free-space checking.
  - `--disk-guard-margin SIZE` (default `100MiB`): additional free space required beyond expected output size.
  - `--ram-limit SIZE`: abort if RSS exceeds this size (best-effort requiring `psutil`).
  - `--fsync-enable`: enable periodic fsync of writes.
  - `--fsync-interval SIZE` (default `8MiB`): flush+fsync every SIZE bytes when fsync enabled.
  - `--hash {md5,sha1,sha256,sha512}`: compute a running hash while writing.
  - `--verify`: re-read and verify hash after write (only for non-compressed output).
  - `--io-retries N` (default 0): retries on I/O error per-chunk (single-writer mode).
  - `--error-budget N` (default 10): number of tolerated write errors before abort.
  - `--resume`: continue at file end for size-bound writes.
  - `--offset SIZE`: start writing at this byte offset (overrides `--resume`).
  - `--truncate SIZE`: truncate file to this size before writing.
  - `--fallocate SIZE`: try to preallocate file space (posix_fallocate or ftruncate fallback).

- Targets
  - `--filelist PATH`: path to a file listing files to pump (one per line). Relative paths resolved against the list file.
  - `--recursive`: when the positional `path` is a directory, recurse into subdirectories to collect files.

- UX
  - `--progress`: print simple progress to stderr.
  - `--progress-interval FLOAT` (default 1.0): progress update interval in seconds.
  - `--newline-mode {none, word, char}`: insert newline "word" or after every character.
  - `--newline-style {lf, cr, crlf}` (default `lf`): newline style to use (affects inserted newline bytes).

- Info & Config
  - `-V, --version`: show version and exit.
  - `--release-link`: print URL of rolling release.
  - `--check-updates`: check GitHub releases for updates.
  - `--config PATH`: load defaults from TOML/JSON/YAML file and apply them to CLI defaults.
  - `--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}` (default `INFO`).
  - `--log-file PATH`: append logs to file.

**Behavior details**
- Write-mode mapping
  - `normal-append`: append text tokens; default `pump-mode=word`.
  - `normal-write`: truncate then write text tokens; default `pump-mode=word`.
  - `binary-append`: append binary chunks; default `pump-mode=randbin`.
  - `binary-write`: truncate then write binary chunks; default `pump-mode=randbin`.

- Target expansion
  - If `path` equals `-`, the single target is stdout.
  - If `path` is a directory and `--recursive` is set, it recursively enumerates files; otherwise lists files in the directory.
  - `--filelist` reads file paths (comments starting with `#` ignored) and resolves relative paths against the list file's parent.

- Expected size estimation (used for disk-guard)
  - If `--max-bytes` provided, used as expected size.
  - Else, if `--times` or `--times-range` provided, the code attempts to estimate expected bytes using simple heuristics (word mode with `--word` and `--mode fixed` uses encoding lengths and newline options; random modes use chunk * times).

- Disk guard
  - By default, the CLI computes expected output size per-device and checks the free space plus `--disk-guard-margin`. If insufficient, it aborts with exit code `3` unless `--disable-disk-guard` is used.

- Buffering and fallbacks
  - Default `--buffer-mode` is `ram`. If expected data exceeds `--ram-max`, it falls back to streaming with an informative message.
  - `--buffer-mode ram` forces single-threaded writer (`--workers` forced to 1).

- Concurrency and compression
  - `--compress gzip` forces single-writer (workers set to 1) because compression requires serial output.

- Rates and throttles
  - `--rate` enforces a global bytes-per-second limit. When multiple writers are used (`--workers`), per-writer sleep logic attempts to respect the global limit approximately.
  - CPU limiting is best-effort using process CPU-time sampling and sleeping when exceeded.
  - RAM limiting requires `psutil` to measure RSS; absent `psutil`, RAM checks are no-ops.

- Sparse files
  - If `--sparse` is provided, the writer will attempt to avoid writing zero-only chunks by seeking to create holes and will call platform-specific ioctl on Windows to mark files sparse where supported.

- Hash and verification
  - If `--hash` is set, the writer computes a running hash during the write. If `--verify` is set and output was not compressed and not to stdout, the file is re-read after close and the computed hash is compared. On mismatch an error is printed and exit code `5` may be raised.

- Error handling
  - For `--io-retries N`, the writer will retry failed chunk writes up to N times, consuming the `--error-budget` (default 10) on each retry.

- Generator modes
  - `word`: emits tokens from `--word` or `--dict`. Supports newline insertion scope (`none`, `word`, `char`) and newline style (`lf`, `cr`, `crlf`). Dictionary modes support `--dict-ram` to preload into RAM and ordering choices (`sequential`, `reverse`, `presorted`, `random`). `--markov` builds an N-gram model from in-memory dictionaries.
  - `bin1`: chunks of 0xFF bytes.
  - `bin0`: chunks of 0x00 bytes.
  - `randbin`: cryptographically secure random bytes via `os.urandom`.
  - `randutf8`: printable UTF-8-like characters (uses Python `string.printable` subset) encoded as UTF-8.
  - `randascii`: printable 7-bit ASCII including space.
  - `randhex`: ASCII hex representation of random bytes.
  - `random`: pick one random random-mode per chunk.

**Configuration files**
- `--config PATH` accepts JSON, TOML, or YAML files. The top-level keys are used to set default CLI arguments (parser.set_defaults), so keys should match CLI argument names (e.g. `chunk`, `write_mode`, `dict_path`, etc.). Example formats are present in `examples/`.

**Exit codes**
- `0`: success.
- `2`: no targets resolved.
- `3`: disk guard failure (not enough space) or other pre-check aborts.
- `4`: RAM limit exceeded or similar resource guard abort.
- `5`: hash verification failed.
- Other non-zero codes may be used via SystemExit in argument parsing or unexpected exceptions.

**Internals & modules**
- `cli.py` — argument orchestration, config loading, targets expansion, disk guard, spawn main thread.
- `_args.py` — builds `argparse` parser, human-size parsing helpers, resolves `--times-range` and expressions (supports caret power `a^b` and scientific `1e6`).
- `_genutil.py` — token generation utilities, encoding detection heuristic, random byte generators, `make_token_iter` which returns an infinite byte iterator for the selected pump mode and text/dictionary options.
- `_dictutil.py` — dictionary streaming and in-memory iteration helpers (used by `make_token_iter` logic when `--dict-ram` is used).
- `_pump.py` — core writing implementations:
  - `pump_to_file` — single-writer sequential writer supporting fsync intervals, hashing, verification, rate/cpu/ram throttles, sparse writes, io-retries.
  - `buffer_and_dump` — aggregate in RAM then perform a single write; checks `--ram-max`.
  - `threaded_pump` — multiple threads sharing a file handle protected by a coarse-grained lock.
  - `pipeline_generate` — multiple generator threads enqueue chunks to a single writer thread.
- `_sizeutil.py` — parse human sizes and format bytes/ETA for progress messages.
- `_bench.py` — benchmark harness to test combinations of chunk sizes, worker counts, and concurrency to recommend a configuration.

**Examples**
- Write the word "hello" 1000 times to `out.txt`:
  - `writetofillet out.txt --word hello --times 1000`

- Create a 10 MiB random binary file:
  - `writetofillet file.bin --write-mode binary-write --size 10MiB`

- Stream printable ASCII at 1 MiB/s to stdout:
  - `writetofillet - --pump-mode randascii --rate 1MiB`

- Use a dictionary file, preserve order, and insert newline after each word:
  - `writetofillet out.txt --dict words.txt --dict-order sequential --newline-mode word`

- Run a local benchmark to get recommendations:
  - `writetofillet --benchmark`

**Testing surface**
- Tests under `tests/` cover: buffer modes, newline modes, pump modes (word vs binary), filelist/targets resolution, disk guard margin behavior, hash/verify behaviors, concurrent generation, size parsing, and mode/size combinations.

**Limitations and notes**
- CPU and RAM limiting are best-effort; accurate enforcement depends on `psutil` for RAM and process CPU sampling for CPU.
- `--verify` re-reads the file for hash verification; compressed (`gzip`) output is not verified.
- Detection of dictionary encoding with `--encoding auto` probes the first dictionary file and falls back to `latin-1` if not decodable as UTF-8.
- Sparse file support is attempted on Windows via DeviceIoControl; on other platforms marking sparse may not be implemented.
- `--dict-list` resolves relative paths against the list file location.
- `--dict-order` non-sequential options require `--dict-ram` for multi-file lists.

**Mapping to tests**
- See `tests/test_*` files for exact behavior checks. Key tests:
  - `test_buffer_modes.py` — checks RAM vs stream behaviors.
  - `test_newline_modes.py` — newline style and mode tests.
  - `test_cli_dict_modes.py`, `test_cli_dict_ram.py` — dictionary ordering and RAM-loading.
  - `test_cli_multithread.py` — threaded writing correctness.
  - `test_size_parse.py` — human size parsing.
  - `test_write_mode_overwrite.py`, `test_write_mode_condensed.py` — write-mode behaviors.

**Changelog notes (current)**
- `--newline` retained for compatibility and maps to `--newline-mode word` when used.
- `--config` supports JSON/TOML/YAML and applies top-level keys to CLI defaults.

**Open items and suggestions**
- Document expected config keys and provide example `spec` config snippets in `examples/`.
- Add more robust sparse-file support for POSIX (fallocate/truncate interplay) and explicit detection.
- Add optional unit tests for `--fsync-enable` behavior and `--hash --verify` on compressed files.


----

Generated from repository code (modules: `src/writetofillet/*`).
