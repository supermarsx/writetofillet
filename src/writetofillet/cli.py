"""
\file cli.py
\brief CLI entrypoint orchestrating parsing, threading, and pumping.

This module wires together argument parsing, data generation, buffering
strategies, and writing. It prints a startup banner, configures logging,
supports update checks, and then runs the main execution in its own thread.
"""

import logging
import random
import sys
import threading
from collections.abc import Iterable
from pathlib import Path

from ._args import build_argparser, resolve_times
from ._bench import run_benchmark
from ._genutil import make_token_iter
from ._pump import buffer_and_dump, pipeline_generate, pump_to_file, threaded_pump
from ._sizeutil import fmt_bytes
from ._updates import check_updates


def main(argv: Iterable[str] | None = None) -> int:
    """Run the writetofillet CLI.

    \param argv Optional list of arguments (defaults to sys.argv[1:]).
    \return Process exit code (0 on success).
    """
    from writetofillet import REPO_URL, __version__

    raw_argv = list(argv) if argv is not None else None
    # Pre-scan for --config
    config_path = None
    if raw_argv:
        for i, tok in enumerate(raw_argv):
            if tok == "--config" and i + 1 < len(raw_argv):
                config_path = raw_argv[i + 1]
                break
    parser = build_argparser()
    # Apply config defaults if provided
    if config_path:
        cfg = {}
        from pathlib import Path as _P

        p = _P(config_path)
        try:
            if p.suffix.lower() == ".json":
                import json

                cfg = json.loads(p.read_text(encoding="utf-8"))
            elif p.suffix.lower() == ".toml":
                try:
                    import tomllib
                except Exception:
                    import tomli as tomllib  # type: ignore
                cfg = tomllib.loads(p.read_text(encoding="utf-8"))
            elif p.suffix.lower() in (".yaml", ".yml"):
                import yaml  # type: ignore

                cfg = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except Exception as e:
            print(f"[warn] Failed to load config {config_path}: {e}", file=sys.stderr)
            cfg = {}
        if isinstance(cfg, dict):
            # Flatten top-level only; ignore unknown keys
            try:
                parser.set_defaults(**cfg)
            except Exception:
                pass
    args = parser.parse_args(raw_argv)

    # Banner (stderr): always show
    print(f"writetofillet v{__version__} — {REPO_URL}", file=sys.stderr)

    logging.basicConfig(
        level=getattr(logging, args.log_level), format="%(asctime)s %(levelname)s %(message)s"
    )
    logger = logging.getLogger("writetofillet")
    if args.log_file:
        fh = logging.FileHandler(args.log_file)
        fh.setLevel(getattr(logging, args.log_level))
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(fh)

    if getattr(args, "version", False):
        print(__version__)
        print(f"Latest rolling release: {REPO_URL}/releases/latest")
        return 0
    if getattr(args, "release_link", False):
        print(f"{REPO_URL}/releases/latest")
        return 0
    if getattr(args, "check_updates", False):
        return check_updates(REPO_URL, logger)

    if getattr(args, "benchmark", False):
        print(
            "[info] Running local benchmark; this writes temporary files and deletes them.",
            file=sys.stderr,
        )
        results, best = run_benchmark(int(args.bench_size), logger)
        # Print summary table
        print("chunk,workers,concurrency,throughput_mibs,cpu_pct,rss_mib")
        for r in results:
            rss_mib = "" if r.rss_bytes is None else f"{r.rss_bytes/(1024*1024):.1f}"
            print(
                f"{r.chunk},{r.workers},{r.concurrency},{r.throughput_bps/(1024*1024):.2f},{r.cpu_percent:.1f},{rss_mib}"
            )
        print("\nRecommendation:")
        workers_flag = (
            f"--workers {best.workers}"
            if best.concurrency == "write"
            else f"--gen-workers {best.workers}"
        )
        print(f"--chunk {best.chunk} --concurrency {best.concurrency} {workers_flag}")
        return 0

    if args.seed is not None:
        random.seed(args.seed)

    # Normalize newline behavior: support legacy --newline and new --newline-mode
    if getattr(args, "newline_mode", None) is None:
        # Map legacy --newline (bool) to word scope
        if getattr(args, "newline", False):
            args.newline_mode = "word"
        else:
            args.newline_mode = "none"

    # Apply condensed write-mode (always present with default)
    wm = args.write_mode
    append = wm.endswith("append")
    default_pump = "randbin" if wm.startswith("binary") else "word"
    if args.pump_mode is None:
        args.pump_mode = default_pump

    n_times = resolve_times(args.times, args.times_range, args.max_times)
    size_limit = args.max_bytes or args.size

    # Expand targets: positional path (file or directory) + optional filelist
    def expand_path(p: Path) -> list[Path]:
        if p == Path("-"):
            return [p]
        if p.is_dir():
            if getattr(args, "recursive", False):
                files: list[Path] = []
                for child in p.rglob("*"):
                    if child.is_file():
                        files.append(child)
                return sorted(files)
            return sorted([c for c in p.iterdir() if c.is_file()])
        return [p]

    targets: list[Path] = []
    base_path = Path(args.path)
    if args.filelist:
        list_path = Path(args.filelist)
        base_dir = list_path.parent
        with open(list_path, encoding="utf-8", errors="replace") as fl:
            for line in fl:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                p = Path(line)
                if not p.is_absolute():
                    p = (base_dir / p).resolve()
                targets.extend(expand_path(p))
    else:
        targets.extend(expand_path(base_path))

    if not targets:
        print("No targets resolved to pump.", file=sys.stderr)
        return 2

    use_ram = args.buffer_mode == "ram"
    expected: int | None = None
    if size_limit is not None:
        expected = size_limit
    elif n_times is not None:
        if args.pump_mode == "word" and args.word and not args.dict_path and args.mode == "fixed":
            enc = args.encoding if args.encoding != "auto" else "utf-8"
            word_bytes = args.word.encode(enc, errors="replace")
            # Determine newline bytes and scope similar to generator
            style = getattr(args, "newline_style", "lf")
            nl_bytes = b"\n" if style == "lf" else (b"\r" if style == "cr" else b"\r\n")
            scope = getattr(args, "newline_mode", "none")
            if scope == "char":
                per = sum(len(ch.encode(enc, errors="replace") + nl_bytes) for ch in args.word)
            elif scope == "word":
                per = len(word_bytes + nl_bytes)
            else:
                per = len(word_bytes)
            expected = per * n_times
        elif args.pump_mode in {
            "bin1",
            "bin0",
            "randbin",
            "randutf8",
            "randascii",
            "randhex",
            "random",
        }:
            expected = n_times * int(args.chunk)

    if use_ram and expected is not None and expected > args.ram_max:
        info_msg = (
            f"[info] Falling back to streaming: expected {fmt_bytes(expected)} "
            f"exceeds --ram-max {fmt_bytes(args.ram_max)}"
        )
        print(info_msg, file=sys.stderr)
        use_ram = False
    if use_ram and args.workers > 1:
        print(
            "[info] --buffer-mode ram forces single-thread; ignoring --workers > 1", file=sys.stderr
        )
        args.workers = 1

    # Global disk-guard upfront check: sum expected per device and compare to free + margin
    if not args.disable_disk_guard and expected is not None:
        try:
            import os
            import shutil

            groups = {}
            for tgt in targets:
                parent = Path(tgt).parent
                dev = os.stat(parent).st_dev
                g = groups.setdefault(dev, {"paths": set(), "need": 0, "free": None})
                g["paths"].add(str(parent))
                g["need"] += expected
            for dev, g in groups.items():
                # Use the first path to query free space
                any_path = next(iter(g["paths"]))
                free = shutil.disk_usage(any_path).free
                required = g["need"] + int(getattr(args, "disk_guard_margin", 0) or 0)
                if required > free:
                    err = (
                        f"[error] Global space check failed for device {dev} ({any_path}): "
                        f"need {fmt_bytes(required)} (incl. margin) to process targets, "
                        f"use --disable-disk-guard or lower --disk-guard-margin to bypass."
                    )
                    print(err, file=sys.stderr)
                    return 3
        except Exception:
            # If we can't compute, continue and rely on per-target checks
            pass

    def run_logic():
        if args.disable_disk_guard:
            print(
                "[warn] Disk-space guard disabled; writes may fail or fill disk.", file=sys.stderr
            )
        # Compression or hashing forces single writer
        if args.compress != "none" and args.workers > 1:
            print("[info] Forcing single-writer due to compression", file=sys.stderr)
            args.workers = 1
        for tgt in targets:
            tgt_parent = Path(tgt).parent if str(tgt) != "-" else Path(".")
            tgt_parent.mkdir(parents=True, exist_ok=True)
            # Disk free space guardrail (per target) when expected is known
            if not args.disable_disk_guard and expected is not None and str(tgt) != "-":
                try:
                    import shutil

                    free = shutil.disk_usage(str(tgt_parent)).free
                except Exception:
                    free = None
                required = expected + int(getattr(args, "disk_guard_margin", 0) or 0)
                if free is not None and required > free:
                    err = (
                        f"[error] Not enough free space at {tgt_parent}: need space, "
                        f"use --disable-disk-guard or lower --disk-guard-margin to bypass."
                    )
                    print(err, file=sys.stderr)
                    return 3
            logger.info(
                "target=%s start: mode=%s, append=%s, size=%s, times=%s",
                tgt,
                args.pump_mode,
                append,
                size_limit,
                n_times,
            )
            # New iterator per target
            data_iter = make_token_iter(args)
            # Pre-size ops
            if str(tgt) != "-" and getattr(args, "truncate", None):
                with open(tgt, "ab") as _tf:
                    _tf.truncate(int(args.truncate))
            if str(tgt) != "-" and getattr(args, "fallocate", None):
                try:
                    fd = os.open(str(tgt), os.O_RDWR | os.O_CREAT)
                    try:
                        os.posix_fallocate(fd, 0, int(args.fallocate))  # type: ignore[attr-defined]
                    except Exception:
                        os.ftruncate(fd, int(args.fallocate))
                    finally:
                        os.close(fd)
                except Exception:
                    pass
            eff_fsync = args.fsync_interval if getattr(args, "fsync_enable", False) else None
            if use_ram:
                buffer_and_dump(
                    tgt,
                    data_iter,
                    append=append,
                    size_limit=size_limit,
                    times=n_times,
                    rate_bps=args.rate,
                    progress=args.progress,
                    progress_interval=args.progress_interval,
                    ram_max=args.ram_max,
                    fsync_interval=eff_fsync,
                    sparse=args.sparse,
                    cpu_limit=args.cpu_limit,
                    ram_limit=args.ram_limit,
                )
            else:
                if args.concurrency == "write":
                    if args.workers > 1:
                        threaded_pump(
                            tgt,
                            data_iter,
                            append=append,
                            size_limit=size_limit,
                            times=n_times,
                            workers=args.workers,
                            rate_bps=args.rate,
                            progress=args.progress,
                            progress_interval=args.progress_interval,
                            fsync_interval=eff_fsync,
                            sparse=args.sparse,
                            cpu_limit=args.cpu_limit,
                            ram_limit=args.ram_limit,
                        )
                    else:
                        algo = getattr(args, "hash", None)
                        start_off = int(args.offset) if getattr(args, "offset", None) else None
                        pump_to_file(
                            tgt,
                            data_iter,
                            append=append or bool(getattr(args, "resume", False)),
                            size_limit=size_limit,
                            times=n_times,
                            rate_bps=args.rate,
                            progress=args.progress,
                            progress_interval=args.progress_interval,
                            fsync_interval=eff_fsync,
                            sparse=args.sparse,
                            cpu_limit=args.cpu_limit,
                            ram_limit=args.ram_limit,
                            compress=args.compress,
                            hash_algo=algo,
                            verify=getattr(args, "verify", False),
                            io_retries=getattr(args, "io_retries", 0),
                            error_budget=getattr(args, "error_budget", 0),
                            start_offset=start_off,
                        )
                else:
                    pipeline_generate(
                        tgt,
                        data_iter,
                        append=append,
                        size_limit=size_limit,
                        times=n_times,
                        rate_bps=args.rate,
                        progress=args.progress,
                        progress_interval=args.progress_interval,
                        gen_workers=args.gen_workers,
                        chunk_size=int(args.chunk),
                        fsync_interval=eff_fsync,
                        sparse=args.sparse,
                        cpu_limit=args.cpu_limit,
                        ram_limit=args.ram_limit,
                    )
            logger.info("target=%s done", tgt)

    main_thread = threading.Thread(target=run_logic, name="writetofillet-main")
    main_thread.start()
    main_thread.join()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
