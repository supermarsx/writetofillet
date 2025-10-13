"""
\file _pump.py
\brief Pumping strategies: direct streaming, RAM buffering, threaded, pipeline.
"""

import multiprocessing
import os
import sys
import threading
import time
from collections.abc import Iterable
from pathlib import Path

from ._sizeutil import fmt_bytes, fmt_eta


def _enable_sparse_if_supported(f):
    try:
        import os

        if os.name != "nt":
            return
        import ctypes
        import msvcrt

        FSCTL_SET_SPARSE = 0x900C4
        handle = msvcrt.get_osfhandle(f.fileno())
        # BOOL DeviceIoControl(HANDLE, DWORD, LPVOID, DWORD, LPVOID, DWORD, LPDWORD, LPOVERLAPPED)
        DeviceIoControl = ctypes.windll.kernel32.DeviceIoControl
        DWORD = ctypes.c_ulong
        lpBytesReturned = DWORD(0)
        res = DeviceIoControl(
            handle,
            DWORD(FSCTL_SET_SPARSE),
            None,
            DWORD(0),
            None,
            DWORD(0),
            ctypes.byref(lpBytesReturned),
            None,
        )
        # Ignore result; on failure, continue without sparse attribute
    except Exception:
        pass


def _write_or_seek(f, chunk: bytes, *, sparse: bool):
    if sparse and (not chunk or not any(chunk)):
        # All zeros: create a hole by seeking past without writing
        f.seek(len(chunk), 1)
    else:
        f.write(chunk)


def pump_to_file(
    path: Path,
    data_iter: Iterable[bytes],
    *,
    append: bool,
    size_limit: int | None,
    times: int | None,
    rate_bps: int | None,
    progress: bool,
    progress_interval: float,
    fsync_interval: int | None = None,
    sparse: bool = False,
    cpu_limit: float | None = None,
    ram_limit: int | None = None,
    compress: str = "none",
    hash_algo: str | None = None,
    verify: bool = False,
    io_retries: int = 0,
    error_budget: int = 0,
    start_offset: int | None = None,
):
    """Write to a file sequentially from a byte iterator.

    \param path Destination file path.
    \param data_iter Infinite iterator of byte chunks.
    \param append Append (True) or overwrite (False).
    \param size_limit Target total bytes (for size-bound mode).
    \param times Number of iterations (for count-bound mode).
    \param rate_bps Optional rate limit in bytes/sec.
    \param progress Whether to show progress.
    \param progress_interval Seconds between progress updates.
    \param fsync_interval Optional interval in bytes for periodic fsync.
    \param sparse Attempt sparse-hole writes for zero chunks when True.
    \param cpu_limit Optional CPU percent limit (best effort).
    \param ram_limit Optional RSS limit in bytes (best effort).
    """
    mode = "ab" if append else "wb"
    written = 0
    start = time.monotonic()
    pt0 = time.process_time()
    ncpu = max(1, multiprocessing.cpu_count())
    last_report = start
    synced = 0
    # stdout handling
    use_stdout = str(path) == "-"
    hasher = None
    if hash_algo:
        import hashlib

        hasher = getattr(hashlib, hash_algo)()
    if use_stdout:
        f = sys.stdout.buffer
        close_f = False
    else:
        import gzip

        rawf = open(path, mode)
        if start_offset is not None and not append:
            try:
                rawf.seek(start_offset)
            except Exception:
                pass
        f = gzip.GzipFile(fileobj=rawf, mode="wb") if compress == "gzip" else rawf
        close_f = True
    try:
        if sparse:
            _enable_sparse_if_supported(f)
        if times is not None:
            for _ in range(times):
                chunk = next(data_iter)
                # hash first
                if hasher:
                    hasher.update(chunk)
                # write with retries
                attempt = 0
                while True:
                    try:
                        _write_or_seek(f, chunk, sparse=sparse)
                        break
                    except Exception:
                        if attempt < io_retries and error_budget >= 0:
                            attempt += 1
                            error_budget -= 1
                            time.sleep(0.01)
                            continue
                        raise
                written += len(chunk)
                if fsync_interval:
                    synced += len(chunk)
                    if synced >= fsync_interval:
                        f.flush()
                        try:
                            os.fsync(f.fileno())
                        except Exception:
                            pass
                        synced = 0
                if rate_bps:
                    while True:
                        elapsed = time.monotonic() - start
                        allowed = rate_bps * max(elapsed, 0)
                        if written <= allowed or rate_bps <= 0:
                            break
                        time.sleep(min(0.1, (written - allowed) / rate_bps))
                if cpu_limit:
                    elapsed = max(1e-6, time.monotonic() - start)
                    cpu_pct = ((time.process_time() - pt0) / elapsed) * (100.0 / ncpu)
                    while cpu_pct > cpu_limit:
                        time.sleep(0.005)
                        elapsed = max(1e-6, time.monotonic() - start)
                        cpu_pct = ((time.process_time() - pt0) / elapsed) * (100.0 / ncpu)
                if ram_limit:
                    try:
                        import psutil

                        rss = psutil.Process().memory_info().rss
                        if rss > ram_limit:
                            print(
                                f"[error] RAM limit exceeded: {rss} > {ram_limit}", file=sys.stderr
                            )
                            raise SystemExit(4)
                    except ImportError:
                        pass
                if progress and (time.monotonic() - last_report >= progress_interval):
                    elapsed = max(time.monotonic() - start, 1e-6)
                    rate = written / elapsed
                    msg = f"Progress: {fmt_bytes(written)}"
                    if size_limit:
                        pct = min(100.0, (written / size_limit) * 100.0)
                        rem = max(size_limit - written, 0)
                        eta = rem / rate if rate > 0 else float("inf")
                        msg += f" ({pct:.1f}%) @ {fmt_bytes(int(rate))}/s ETA {fmt_eta(eta)}"
                    else:
                        msg += f" @ {fmt_bytes(int(rate))}/s"
                    print("\r" + msg, end="", file=sys.stderr)
                    last_report = time.monotonic()
                if size_limit is not None and written >= size_limit:
                    break
        else:
            target = size_limit
            if target is None:
                raise SystemExit("Provide --times/--times-range or --size/--max-bytes")
            while written < target:
                chunk = next(data_iter)
                remain = target - written
                if len(chunk) > remain:
                    chunk = chunk[:remain]
                if hasher:
                    hasher.update(chunk)
                attempt = 0
                while True:
                    try:
                        _write_or_seek(f, chunk, sparse=sparse)
                        break
                    except Exception:
                        if attempt < io_retries and error_budget >= 0:
                            attempt += 1
                            error_budget -= 1
                            time.sleep(0.01)
                            continue
                        raise
                written += len(chunk)
                if fsync_interval:
                    synced += len(chunk)
                    if synced >= fsync_interval:
                        f.flush()
                        try:
                            os.fsync(f.fileno())
                        except Exception:
                            pass
                        synced = 0
                if rate_bps:
                    while True:
                        elapsed = time.monotonic() - start
                        allowed = rate_bps * max(elapsed, 0)
                        if written <= allowed or rate_bps <= 0:
                            break
                        time.sleep(min(0.1, (written - allowed) / rate_bps))
                if cpu_limit:
                    elapsed = max(1e-6, time.monotonic() - start)
                    cpu_pct = ((time.process_time() - pt0) / elapsed) * (100.0 / ncpu)
                    while cpu_pct > cpu_limit:
                        time.sleep(0.005)
                        elapsed = max(1e-6, time.monotonic() - start)
                        cpu_pct = ((time.process_time() - pt0) / elapsed) * (100.0 / ncpu)
                if ram_limit:
                    try:
                        import psutil

                        rss = psutil.Process().memory_info().rss
                        if rss > ram_limit:
                            print(
                                f"[error] RAM limit exceeded: {rss} > {ram_limit}", file=sys.stderr
                            )
                            raise SystemExit(4)
                    except ImportError:
                        pass
                if progress and (time.monotonic() - last_report >= progress_interval):
                    elapsed = max(time.monotonic() - start, 1e-6)
                    rate = written / elapsed
                    pct = min(100.0, (written / target) * 100.0)
                    rem = max(target - written, 0)
                    eta = rem / rate if rate > 0 else float("inf")
                    msg = f"\rProgress: {fmt_bytes(written)} ({pct:.1f}%) @ {fmt_bytes(int(rate))}/s ETA {fmt_eta(eta)}"
                    print(msg, end="", file=sys.stderr)
                    last_report = time.monotonic()
    finally:
        if progress:
            print(file=sys.stderr)
        if close_f:
            try:
                f.close()
            except Exception:
                pass
        # Verification step (file only, non-stdout, non-gzip)
        if verify and not use_stdout and compress != "gzip" and hasher is not None:
            try:
                import hashlib

                hv = getattr(hashlib, hash_algo)()
                with open(path, "rb") as rf:
                    for blk in iter(lambda: rf.read(1024 * 1024), b""):
                        hv.update(blk)
                if hv.hexdigest() != hasher.hexdigest():
                    print("[error] Hash verification failed", file=sys.stderr)
                    raise SystemExit(5)
            except Exception:
                pass


def buffer_and_dump(
    path: Path,
    data_iter: Iterable[bytes],
    *,
    append: bool,
    size_limit: int | None,
    times: int | None,
    rate_bps: int | None,
    progress: bool,
    progress_interval: float,
    ram_max: int,
    fsync_interval: int | None = None,
    sparse: bool = False,
    cpu_limit: float | None = None,
    ram_limit: int | None = None,
):
    """Accumulate into RAM, then dump to disk in a single write.

    Guarded by \p ram_max to avoid excessive memory usage. Supports
    optional rate, CPU, and RAM limiting (best effort). Sparse handling
    is not applied during RAM aggregation.
    """
    buf = bytearray()
    written = 0
    start = time.monotonic()
    last_report = start

    def add_chunk(chunk: bytes):
        nonlocal written
        if len(buf) + len(chunk) > ram_max:
            raise SystemExit(
                f"RAM buffer would exceed --ram-max {fmt_bytes(ram_max)}; use --buffer-mode stream or increase --ram-max"
            )
        buf.extend(chunk)
        written += len(chunk)
        if rate_bps:
            while True:
                elapsed = time.monotonic() - start
                allowed = rate_bps * max(elapsed, 0)
                if written <= allowed or rate_bps <= 0:
                    break
                time.sleep(min(0.1, (written - allowed) / rate_bps))
        if cpu_limit:
            elapsed = max(1e-6, time.monotonic() - start)
            cpu_pct = ((time.process_time()) / elapsed) * (
                100.0 / max(1, multiprocessing.cpu_count())
            )
            while cpu_pct > cpu_limit:
                time.sleep(0.005)
                elapsed = max(1e-6, time.monotonic() - start)
                cpu_pct = ((time.process_time()) / elapsed) * (
                    100.0 / max(1, multiprocessing.cpu_count())
                )
        if ram_limit:
            try:
                import psutil

                rss = psutil.Process().memory_info().rss
                if rss > ram_limit:
                    print(f"[error] RAM limit exceeded: {rss} > {ram_limit}", file=sys.stderr)
                    raise SystemExit(4)
            except ImportError:
                pass

    if times is not None:
        for _ in range(times):
            chunk = next(data_iter)
            add_chunk(chunk)
            if size_limit is not None and written >= size_limit:
                break
            if progress and (time.monotonic() - last_report >= progress_interval):
                elapsed = max(time.monotonic() - start, 1e-6)
                rate = written / elapsed
                msg = f"\rProgress (RAM): {fmt_bytes(written)} @ {fmt_bytes(int(rate))}/s"
                print(msg, end="", file=sys.stderr)
                last_report = time.monotonic()
    else:
        target = size_limit
        if target is None:
            raise SystemExit("Provide --times/--times-range or --size/--max-bytes")
        while written < target:
            chunk = next(data_iter)
            remain = target - written
            if len(chunk) > remain:
                chunk = chunk[:remain]
            add_chunk(chunk)
            if progress and (time.monotonic() - last_report >= progress_interval):
                elapsed = max(time.monotonic() - start, 1e-6)
                rate = written / elapsed
                pct = min(100.0, (written / target) * 100.0)
                rem = max(target - written, 0)
                eta = rem / rate if rate > 0 else float("inf")
                msg = f"\rProgress (RAM): {fmt_bytes(written)} ({pct:.1f}%) @ {fmt_bytes(int(rate))}/s ETA {fmt_eta(eta)}"
                print(msg, end="", file=sys.stderr)
                last_report = time.monotonic()
    if progress:
        print(file=sys.stderr)
    mode = "ab" if append else "wb"
    with open(path, mode) as f:
        if sparse:
            _enable_sparse_if_supported(f)
        # In RAM mode, we cannot efficiently detect zero runs without scanning; write as is
        f.write(buf)
        # Optional single fsync after dump (interval not meaningful for RAM mode)
        if fsync_interval:
            f.flush()
            try:
                os.fsync(f.fileno())
            except Exception:
                pass


def threaded_pump(
    path: Path,
    data_iter: Iterable[bytes],
    *,
    append: bool,
    size_limit: int | None,
    times: int | None,
    workers: int,
    rate_bps: int | None,
    progress: bool,
    progress_interval: float,
    fsync_interval: int | None = None,
    sparse: bool = False,
    cpu_limit: float | None = None,
    ram_limit: int | None = None,
):
    """Run multiple writer threads against a shared file handle.

    Uses coarse-grained locking; suitable for high-throughput scenarios.
    Supports optional periodic fsync, sparse holes, and throttles.
    """
    lock = threading.Lock()
    mode = "ab" if append else "wb"
    target = size_limit
    state = {"written": 0, "remaining_writes": times, "done": False}
    start = time.monotonic()
    per_thread_rate = None
    if rate_bps and workers > 0:
        per_thread_rate = max(1, rate_bps // workers)

    def worker():
        nonlocal target
        with open(path, mode) as f:
            if sparse:
                _enable_sparse_if_supported(f)
            synced = 0
            while True:
                with lock:
                    if state["remaining_writes"] is not None:
                        if state["remaining_writes"] <= 0:
                            return
                        state["remaining_writes"] -= 1
                    if target is not None and state["written"] >= target:
                        return
                chunk = next(data_iter)
                if target is not None:
                    with lock:
                        remain = target - state["written"]
                    if remain <= 0:
                        return
                    if len(chunk) > remain:
                        chunk = chunk[:remain]
                if per_thread_rate:
                    time.sleep(max(0.0, len(chunk) / float(per_thread_rate)))
                with lock:
                    _write_or_seek(f, chunk, sparse=sparse)
                    state["written"] += len(chunk)
                    if fsync_interval:
                        synced += len(chunk)
                        if synced >= fsync_interval:
                            f.flush()
                            try:
                                os.fsync(f.fileno())
                            except Exception:
                                pass
                            synced = 0
                # Post-write throttles/limits (rough)
                if rate_bps:
                    elapsed = time.monotonic() - start
                    allowed = rate_bps * max(elapsed, 0)
                    with lock:
                        cur = state["written"]
                    while cur > allowed and rate_bps > 0:
                        time.sleep(0.005)
                        elapsed = time.monotonic() - start
                        allowed = rate_bps * max(elapsed, 0)
                        with lock:
                            cur = state["written"]
                if cpu_limit:
                    elapsed = max(1e-6, time.monotonic() - start)
                    cpu_pct = ((time.process_time()) / elapsed) * (
                        100.0 / max(1, multiprocessing.cpu_count())
                    )
                    while cpu_pct > cpu_limit:
                        time.sleep(0.005)
                        elapsed = max(1e-6, time.monotonic() - start)
                        cpu_pct = ((time.process_time()) / elapsed) * (
                            100.0 / max(1, multiprocessing.cpu_count())
                        )
                if ram_limit:
                    try:
                        import psutil

                        rss = psutil.Process().memory_info().rss
                        if rss > ram_limit:
                            print(
                                f"[error] RAM limit exceeded: {rss} > {ram_limit}", file=sys.stderr
                            )
                            raise SystemExit(4)
                    except ImportError:
                        pass

    threads = [threading.Thread(target=worker, daemon=True) for _ in range(max(1, workers))]

    def monitor():
        if not progress:
            return
        while True:
            time.sleep(progress_interval)
            with lock:
                w = state["written"]
                done = state.get("done", False)
            elapsed = max(time.monotonic() - start, 1e-6)
            rate = w / elapsed
            if target:
                pct = min(100.0, (w / target) * 100.0)
                rem = max(target - w, 0)
                eta = rem / rate if rate > 0 else float("inf")
                msg = f"\rProgress: {fmt_bytes(w)} ({pct:.1f}%) @ {fmt_bytes(int(rate))}/s ETA {fmt_eta(eta)}"
            else:
                msg = f"\rProgress: {fmt_bytes(w)} @ {fmt_bytes(int(rate))}/s"
            print(msg, end="", file=sys.stderr)
            if done:
                print(file=sys.stderr)
                return

    mon = threading.Thread(target=monitor, daemon=True)
    if progress:
        mon.start()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    with lock:
        state["done"] = True


def pipeline_generate(
    path: Path,
    data_iter: Iterable[bytes],
    *,
    append: bool,
    size_limit: int | None,
    times: int | None,
    rate_bps: int | None,
    progress: bool,
    progress_interval: float,
    gen_workers: int,
    chunk_size: int,
    fsync_interval: int | None = None,
    sparse: bool = False,
    cpu_limit: float | None = None,
    ram_limit: int | None = None,
):
    """Fan-out producers (generators) feeding a single writer via a queue.

    \param gen_workers Number of generator threads.
    \param chunk_size Approximate generator chunk size (for queue sizing).
    \param fsync_interval Optional interval in bytes for periodic fsync.
    \param sparse Attempt sparse-hole writes for zero chunks when True.
    \param cpu_limit Optional CPU percent limit (best effort).
    \param ram_limit Optional RSS limit in bytes (best effort).
    """
    import queue

    q: queue.Queue[bytes | None] = queue.Queue(maxsize=max(8, 1024 * 1024 // max(1, chunk_size)))
    lock = threading.Lock()
    state = {
        "written": 0,
        "produced": 0,
        "remaining_writes": times,
        "target": size_limit,
        "done": False,
    }
    start = time.monotonic()

    def producer():
        while True:
            with lock:
                if state["remaining_writes"] is not None and state["remaining_writes"] <= 0:
                    break
                if state["target"] is not None and state["produced"] >= state["target"]:
                    break
                if state["remaining_writes"] is not None:
                    state["remaining_writes"] -= 1
            chunk = next(data_iter)
            with lock:
                if state["target"] is not None:
                    remain = state["target"] - state["produced"]
                    if remain <= 0:
                        break
                    if len(chunk) > remain:
                        chunk = chunk[:remain]
                state["produced"] += len(chunk)
            q.put(chunk)

    def writer():
        mode = "ab" if append else "wb"
        last_report = start
        with open(path, mode) as f:
            if sparse:
                _enable_sparse_if_supported(f)
            synced = 0
            while True:
                item = q.get()
                if item is None:
                    break
                _write_or_seek(f, item, sparse=sparse)
                with lock:
                    state["written"] += len(item)
                if rate_bps:
                    while True:
                        elapsed = time.monotonic() - start
                        allowed = rate_bps * max(elapsed, 0)
                        if state["written"] <= allowed or rate_bps <= 0:
                            break
                        time.sleep(min(0.1, (state["written"] - allowed) / rate_bps))
                if fsync_interval:
                    synced += len(item)
                    if synced >= fsync_interval:
                        f.flush()
                        try:
                            os.fsync(f.fileno())
                        except Exception:
                            pass
                        synced = 0
                # Throttle and limits
                if rate_bps:
                    elapsed = time.monotonic() - start
                    allowed = rate_bps * max(elapsed, 0)
                    with lock:
                        cur = state["written"]
                    while cur > allowed and rate_bps > 0:
                        time.sleep(0.005)
                        elapsed = time.monotonic() - start
                        allowed = rate_bps * max(elapsed, 0)
                        with lock:
                            cur = state["written"]
                if cpu_limit:
                    elapsed = max(1e-6, time.monotonic() - start)
                    cpu_pct = ((time.process_time()) / elapsed) * (
                        100.0 / max(1, multiprocessing.cpu_count())
                    )
                    while cpu_pct > cpu_limit:
                        time.sleep(0.005)
                        elapsed = max(1e-6, time.monotonic() - start)
                        cpu_pct = ((time.process_time()) / elapsed) * (
                            100.0 / max(1, multiprocessing.cpu_count())
                        )
                if ram_limit:
                    try:
                        import psutil

                        rss = psutil.Process().memory_info().rss
                        if rss > ram_limit:
                            print(
                                f"[error] RAM limit exceeded: {rss} > {ram_limit}", file=sys.stderr
                            )
                            raise SystemExit(4)
                    except ImportError:
                        pass

                if progress and (time.monotonic() - last_report >= progress_interval):
                    elapsed = max(time.monotonic() - start, 1e-6)
                    rate = state["written"] / elapsed
                    if state["target"]:
                        pct = min(100.0, (state["written"] / state["target"]) * 100.0)
                        rem = max(state["target"] - state["written"], 0)
                        eta = rem / rate if rate > 0 else float("inf")
                        msg = f"\rProgress: {fmt_bytes(state['written'])} ({pct:.1f}%) @ {fmt_bytes(int(rate))}/s ETA {fmt_eta(eta)}"
                    else:
                        msg = (
                            f"\rProgress: {fmt_bytes(state['written'])} @ {fmt_bytes(int(rate))}/s"
                        )
                    print(msg, end="", file=sys.stderr)
                    last_report = time.monotonic()
        if progress:
            print(file=sys.stderr)

    producers = [threading.Thread(target=producer, daemon=True) for _ in range(max(1, gen_workers))]
    for t in producers:
        t.start()
    w = threading.Thread(target=writer, daemon=True)
    w.start()
    for t in producers:
        t.join()
    q.put(None)
    w.join()
