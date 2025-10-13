"""
\file _dictutil.py
\brief Dictionary loading and iteration helpers (RAM or streaming).
"""

import random
from collections.abc import Iterable
from pathlib import Path


def iter_dict_words(path: Path, order: str, encoding: str, in_memory: bool) -> Iterable[str]:
    """Yield words from a wordlist according to the requested order.

    \param path Path to the dictionary file.
    \param order One of sequential, reverse, presorted, random.
    \param encoding Text encoding for reading.
    \param in_memory If True, load the entire list into RAM; otherwise stream.
    \return Infinite generator of tokens.
    \throws SystemExit when a non-sequential order is requested without RAM.
    """
    if in_memory:
        with open(path, encoding=encoding, errors="replace") as f:
            words = [w.strip() for w in f if w.strip()]
        if order == "sequential":
            while True:
                for w in words:
                    yield w
        elif order == "reverse":
            while True:
                for w in reversed(words):
                    yield w
        elif order == "presorted":
            words_sorted = sorted(words)
            while True:
                for w in words_sorted:
                    yield w
        elif order == "random":
            while True:
                yield random.choice(words)
        else:
            raise ValueError(f"Unknown dictionary order: {order}")
    else:
        if order != "sequential":
            raise SystemExit("--dict-order requires --dict-ram for non-sequential orders")

        def stream_seq():
            while True:
                with open(path, encoding=encoding, errors="replace") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            yield line

        return stream_seq()
