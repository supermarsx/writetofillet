"""
\file _args.py
\brief Argument parsing and basic option resolution utilities.
"""

import argparse
import random
from ._sizeutil import parse_human_size


def build_argparser() -> argparse.ArgumentParser:
    """Build the CLI argument parser.

    \return Configured ArgumentParser instance.
    """
    epilog = (
        "\nWrite modes (condensed):\n"
        "  normal-append  Append text tokens; defaults pump-mode=word.\n"
        "  normal-write   Truncate then write text tokens; defaults pump-mode=word.\n"
        "  binary-append  Append binary chunks; defaults pump-mode=randbin.\n"
        "  binary-write   Truncate then write binary chunks; defaults pump-mode=randbin.\n\n"
        "Pump modes:\n"
        "  word     Encode a word or dictionary tokens (use --mode, newline options).\n"
        "  bin1     0xFF bytes.\n"
        "  bin0     0x00 bytes.\n"
        "  randbin  Cryptographically random bytes.\n"
        "  randutf8 Printable ASCII/UTF-8 text.\n"
        "  randhex  Hex characters of random bytes.\n"
        "  random   Randomly pick one of the random modes per chunk.\n\n"
        "Defaults & safety:\n"
        "  error-budget=10 (max tolerated write errors); fsync disabled unless --fsync-enable.\n"
    )
    p = argparse.ArgumentParser(
        description="File pumper CLI: create or append data by count or size.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=epilog,
    )

    io = p.add_argument_group("I/O")
    io.add_argument("path", help="Target file path")

    work = p.add_argument_group("Workload")
    work.add_argument("--times", type=int, help="Repeat token this many times")
    work.add_argument("--times-range", help="Repeat a random number of times between MIN,MAX")
    work.add_argument("--size", type=parse_human_size, help="Target total size, e.g. 10MiB, 500KB")
    work.add_argument("--max-bytes", type=parse_human_size, help="Hard stop at this size regardless of other limits")

    source = p.add_argument_group("Source")
    source.add_argument("--word", help="Word/token to write (text mode)")
    source.add_argument("--dict", dest="dict_path", help="Path to wordlist (newline-separated)")
    source.add_argument("--dict-list", dest="dict_list", help="Path to a file containing list of dictionary files (one per line; relative to this list file or absolute)")
    source.add_argument("--dict-order", choices=["sequential", "reverse", "random", "presorted"], default="random")
    source.add_argument("--dict-ram", action="store_true", help="Load dictionary into RAM (required for non-sequential orders)")
    source.add_argument("--markov", action="store_true", help="Use a simple Markov/N-gram generator from dictionaries (requires --dict-ram)")
    source.add_argument("--ngram", type=int, default=2, help="N for N-gram model when --markov is set (default 2)")

    modes = p.add_argument_group("Modes")
    modes.add_argument("--write-mode", choices=["normal-append", "normal-write", "binary-append", "binary-write"], default="normal-append", help="Condensed write mode selector (default: normal-append)")
    modes.add_argument("--pump-mode", choices=["word", "bin1", "bin0", "randbin", "randutf8", "randhex", "random"], default=None)
    modes.add_argument("--mode", choices=["fixed", "random"], default="fixed", help="Fixed token or randomly chosen per write")

    perf = p.add_argument_group("Performance")
    perf.add_argument("--workers", type=int, default=1, help="Number of writer threads (write concurrency)")
    perf.add_argument("--chunk", type=parse_human_size, default=parse_human_size("64KiB"), help="Chunk size for buffered writes")
    perf.add_argument("--seed", type=int, help="Random seed for reproducibility")
    perf.add_argument("--rate", type=parse_human_size, help="Throttle throughput to RATE bytes/sec (e.g. 10MiB)")
    perf.add_argument("--cpu-limit", type=float, help="Approximate CPU limit in percent (e.g. 150 for 1.5 cores on a 1-core system)")
    perf.add_argument("--concurrency", choices=["write", "generate"], default="write", help="Parallelize writers or generators")
    perf.add_argument("--gen-workers", type=int, default=1, help="Number of generator threads when --concurrency generate")
    perf.add_argument("--benchmark", action="store_true", help="Run a local benchmark to suggest optimal chunk/workers/concurrency")
    perf.add_argument("--bench-size", type=parse_human_size, default=parse_human_size("64MiB"), help="Amount of data to write per benchmark run (e.g. 64MiB)")
    perf.add_argument("--compress", choices=["none", "gzip"], default="none", help="Compress output (gzip) — disables multi-writer threads")

    buffer = p.add_argument_group("Buffering")
    buffer.add_argument("--buffer-mode", choices=["ram", "stream"], default="ram", help="Write via RAM then dump (default) or stream directly to file")
    buffer.add_argument("--ram-max", type=parse_human_size, default=parse_human_size("256MiB"), help="Max RAM to use before falling back to streaming")
    buffer.add_argument("--sparse", action="store_true", help="Attempt to create sparse files (skip zero chunks, mark sparse on supported filesystems)")

    limits = p.add_argument_group("Limits & Safety")
    limits.add_argument("--max-times", type=int, default=10_000_000, help="Upper limit guard for --times")
    limits.add_argument("--disable-disk-guard", action="store_true", help="Disable free-disk-space guardrail (dangerous; may fill disk)")
    limits.add_argument("--disk-guard-margin", type=parse_human_size, default=parse_human_size("100MiB"), help="Additional free space to require beyond expected output size (e.g. 100MiB)")
    limits.add_argument("--ram-limit", type=parse_human_size, default=None, help="Abort if RSS (process memory) exceeds this size")
    limits.add_argument("--fsync-enable", action="store_true", help="Enable periodic fsync using default interval or --fsync-interval")
    limits.add_argument("--fsync-interval", type=parse_human_size, default=parse_human_size("8MiB"), help="Flush+fsync every SIZE bytes when enabled (default 8MiB)")
    limits.add_argument("--hash", choices=["md5", "sha1", "sha256", "sha512"], help="Compute a running hash while writing")
    limits.add_argument("--verify", action="store_true", help="Verify hash by rereading file after write (non-compressed only)")
    limits.add_argument("--io-retries", type=int, default=0, help="Retries on I/O error per chunk (single-writer mode)")
    limits.add_argument("--error-budget", type=int, default=10, help="Max tolerated write errors before abort (default 10)")
    limits.add_argument("--resume", action="store_true", help="Resume size-bound writes by continuing at end of file")
    limits.add_argument("--offset", type=parse_human_size, help="Start writing at this byte offset (overrides resume)")
    limits.add_argument("--truncate", type=parse_human_size, help="Truncate the target file to this size before writing")
    limits.add_argument("--fallocate", type=parse_human_size, help="Preallocate file space to this size when supported")

    targets = p.add_argument_group("Targets")
    targets.add_argument("--filelist", help="Path to a file containing list of files to pump, one per line (relative or absolute)")
    targets.add_argument("--recursive", action="store_true", help="Recurse into subdirectories when the positional path is a directory")

    ux = p.add_argument_group("UX")
    ux.add_argument("--progress", action="store_true", help="Show simple progress to stderr")
    ux.add_argument("--progress-interval", type=float, default=1.0, help="Progress update interval in seconds")
    ux.add_argument("--newline-mode", choices=["none", "word", "char"], default=None, help="Insert newline after each word token or each character (text modes)")
    ux.add_argument("--newline-style", choices=["lf", "cr", "crlf"], default="lf", help="Newline style to use when inserting newlines")

    info = p.add_argument_group("Info")
    info.add_argument("-V", "--version", action="store_true", help="Show version and exit")
    info.add_argument("--release-link", action="store_true", help="Show link to latest rolling release and exit")
    info.add_argument("--check-updates", action="store_true", help="Check for a newer rolling release and exit")
    info.add_argument("-H", "--help-long", action="help", help="Show help and exit")

    cfg = p.add_argument_group("Config")
    cfg.add_argument("--config", help="Path to a TOML/JSON/YAML config file with CLI defaults")

    logs = p.add_argument_group("Logging")
    logs.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Logging level")
    logs.add_argument("--log-file", help="Path to log file (append)")

    return p


def resolve_times(times, times_range, max_times):
    """Resolve the effective repetition count.

    \param times Fixed number of repetitions or None.
    \param times_range Range string "MIN,MAX" for random selection or None.
    \param max_times Guardrail maximum allowed repetitions.
    \return The resolved integer repetitions or None.
    \throws SystemExit if guardrail is exceeded or range invalid.
    """
    def _parse_int_expr(expr: str) -> int:
        s = str(expr).strip().lower().replace("_", "")
        # Power notation using caret: a^b
        if "^" in s:
            try:
                base, exp = s.split("^", 1)
                return int(float(base)) ** int(float(exp))
            except Exception:
                raise argparse.ArgumentTypeError(f"Invalid power expression: {expr}")
        # Scientific notation like 1e6
        if "e" in s:
            try:
                return int(float(s))
            except Exception:
                raise argparse.ArgumentTypeError(f"Invalid scientific notation: {expr}")
        try:
            return int(s)
        except Exception:
            raise argparse.ArgumentTypeError(f"Invalid integer: {expr}")

    if times_range:
        try:
            mn, mx = times_range.split(",", 1)
            mn_i, mx_i = _parse_int_expr(mn), _parse_int_expr(mx)
        except ValueError:
            raise argparse.ArgumentTypeError("--times-range must be MIN,MAX")
        if mn_i < 0 or mx_i < mn_i:
            raise argparse.ArgumentTypeError("Invalid --times-range bounds")
        n = random.randint(mn_i, mx_i)
    else:
        n = times
    if n is not None and n > max_times:
        raise SystemExit(f"Refusing to write {n} times (over --max-times {max_times})")
    return n
