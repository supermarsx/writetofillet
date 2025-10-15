r"""
\file _bench.py
\brief Simple local benchmark to explore throughput vs. chunk/workers/concurrency.

This module writes temporary data to measure effective throughput under
different chunk sizes, thread counts, and concurrency models. It returns
structured results and a best recommendation.
"""

import os
import tempfile
import time
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from ._pump import pipeline_generate, pump_to_file, threaded_pump


def _iter_randbin(chunk: int) -> Iterable[bytes]:
    r"""Yield infinite random binary chunks of the given size.

    \param chunk Chunk size in bytes.
    \return Infinite iterator of bytes.
    """

    def gen():
        while True:
            yield os.urandom(chunk)

    return gen()


def _cpu_percent(elapsed: float, t_start: float, t_end: float) -> float:
    r"""Compute an approximate CPU utilization percent for the process.

    \param elapsed Wall time in seconds.
    \param t_start Process time at start.
    \param t_end Process time at end.
    \return Approximate percent normalized by CPU count (0-100).
    """
    # Python process_time is CPU time in seconds
    if elapsed <= 0:
        return 0.0
    import multiprocessing

    proctime = t_end - t_start
    cpus = max(1, multiprocessing.cpu_count())
    return min(100.0, max(0.0, (proctime / elapsed) * (100.0 / cpus)))


def _rss_bytes() -> int | None:
    """Return current process RSS in bytes, if available.

    Uses psutil when present; otherwise returns None.
    """
    try:
        import psutil

        return psutil.Process().memory_info().rss
    except Exception:
        return None


@dataclass
class BenchResult:
    chunk: int
    workers: int
    concurrency: str
    throughput_bps: float
    cpu_percent: float
    rss_bytes: int | None


def run_benchmark(
    bench_size: int,
    logger,
    *,
    candidate_chunks: list[int] | None = None,
    candidate_workers: list[int] | None = None,
    include_generate: bool = True,
) -> tuple[list[BenchResult], BenchResult]:
    r"""Run the benchmark suite and return all results and the best.

    \param bench_size Target bytes to write per scenario.
    \param logger Logger for summary output.
    \param candidate_chunks Candidate chunk sizes to test.
    \param candidate_workers Candidate thread counts to test.
    \param include_generate Whether to include generate-concurrency tests.
    \return Tuple of (all results, best result).
    """
    if candidate_chunks is None:
        candidate_chunks = [32 * 1024, 64 * 1024, 256 * 1024, 1024 * 1024]
    if candidate_workers is None:
        # Cap workers by CPU count
        import multiprocessing

        ncpu = max(1, multiprocessing.cpu_count())
        candidate_workers = [w for w in [1, 2, 4, 8] if w <= ncpu]

    results: list[BenchResult] = []
    with tempfile.TemporaryDirectory() as td:
        dpath = Path(td)
        for chunk in candidate_chunks:
            for workers in candidate_workers:
                for concurrency in ["write", "generate"] if include_generate else ["write"]:
                    # Prepare iterator and target
                    it = _iter_randbin(chunk)
                    target = dpath / f"bench-{concurrency}-{workers}-{chunk}.bin"
                    # Measure
                    rss0 = _rss_bytes()
                    pt0 = time.process_time()
                    t0 = time.monotonic()
                    if concurrency == "write":
                        if workers > 1:
                            threaded_pump(
                                target,
                                it,
                                append=False,
                                size_limit=bench_size,
                                times=None,
                                workers=workers,
                                rate_bps=None,
                                progress=False,
                                progress_interval=1.0,
                            )
                        else:
                            pump_to_file(
                                target,
                                it,
                                append=False,
                                size_limit=bench_size,
                                times=None,
                                rate_bps=None,
                                progress=False,
                                progress_interval=1.0,
                            )
                    else:
                        # generate concurrency
                        pipeline_generate(
                            target,
                            it,
                            append=False,
                            size_limit=bench_size,
                            times=None,
                            rate_bps=None,
                            progress=False,
                            progress_interval=1.0,
                            gen_workers=workers,
                            chunk_size=chunk,
                        )
                    t1 = time.monotonic()
                    pt1 = time.process_time()
                    rss1 = _rss_bytes()
                    elapsed = max(1e-6, t1 - t0)
                    thr = bench_size / elapsed
                    cpu = _cpu_percent(elapsed, pt0, pt1)
                    rss = rss1 if (rss0 is None or rss1 is None) else max(0, rss1 - rss0)
                    results.append(
                        BenchResult(
                            chunk=chunk,
                            workers=workers,
                            concurrency=concurrency,
                            throughput_bps=thr,
                            cpu_percent=cpu,
                            rss_bytes=rss,
                        )
                    )
                    try:
                        target.unlink(missing_ok=True)
                    except Exception:
                        pass

    # Pick best: max throughput, tie-break by lower CPU then lower RSS
    def key(br: BenchResult):
        return (br.throughput_bps, -br.cpu_percent, -(br.rss_bytes or 0))

    best = max(results, key=key)
    logger.info(
        "benchmark best: chunk=%s workers=%s concurrency=%s thr=%.2f MiB/s cpu=%.1f%% rss=%s",
        best.chunk,
        best.workers,
        best.concurrency,
        best.throughput_bps / (1024 * 1024),
        best.cpu_percent,
        ("n/a" if best.rss_bytes is None else f"{best.rss_bytes/ (1024*1024):.1f} MiB"),
    )
    return results, best
