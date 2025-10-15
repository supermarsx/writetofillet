r"""
\file _sizeutil.py
\brief Human size parsing and formatting utilities for throughput/ETA.
"""

import argparse


def parse_human_size(s):
    r"""Parse a human-friendly size string into bytes.

    Supports decimal (KB/MB/GB) and binary (KiB/MiB/GiB) units.

    \param s String like "64KiB", "10MB" or None.
    \return Integer number of bytes, or None if input is falsy.
    \throws argparse.ArgumentTypeError on invalid format.
    """
    if not s:
        return None
    s = str(s).strip().lower()
    units = {
        "b": 1,
        "byte": 1,
        "bytes": 1,
        "kb": 1000,
        "mb": 1000**2,
        "gb": 1000**3,
        "tb": 1000**4,
        "kib": 1024,
        "mib": 1024**2,
        "gib": 1024**3,
        "tib": 1024**4,
    }
    num = ""
    unit = ""
    for ch in s:
        if ch.isdigit() or ch == ".":
            num += ch
        else:
            unit += ch
    unit = unit or "b"
    try:
        value = float(num)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid size: {s}")
    if unit not in units:
        raise argparse.ArgumentTypeError(f"Invalid unit in size: {s}")
    return int(value * units[unit])


def fmt_bytes(n: int) -> str:
    r"""Format a byte count with binary units.

    \param n Byte count.
    \return String like "64.0 KiB".
    """
    for unit, step in (("B", 1), ("KiB", 1024), ("MiB", 1024**2), ("GiB", 1024**3)):
        if n < step * 1024 or unit == "GiB":
            return f"{n/step:.1f} {unit}"
    return f"{n} B"


def fmt_eta(seconds: float) -> str:
    r"""Format an ETA given seconds remaining.

    \param seconds Seconds to completion.
    \return HH:MM:SS or MM:SS string, or "--:--" if unknown.
    """
    if seconds <= 0 or seconds == float("inf"):
        return "--:--"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"
