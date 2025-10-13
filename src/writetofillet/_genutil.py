"""
\file _genutil.py
\brief Data generation utilities for random and word-based modes.
"""

import codecs
import os
import random
import string
from collections.abc import Iterable
from pathlib import Path


def detect_encoding(path: Path) -> str:
    """Heuristically detect text encoding of a file.

    Tries UTF-8, falls back to Latin-1.

    \param path File path to probe.
    \return Encoding string like "utf-8".
    """
    try:
        with open(path, "rb") as f:
            raw = f.read(4096)
        try:
            raw.decode("utf-8")
            return "utf-8"
        except UnicodeDecodeError:
            return "latin-1"
    except FileNotFoundError:
        return "utf-8"


def gen_random_bytes(mode: str, chunk_size: int = 8192) -> bytes:
    """Generate a chunk of bytes for a given random mode.

    \param mode One of bin1, bin0, randbin, randutf8, randhex, random.
    \param chunk_size Desired approximate chunk size.
    \return Byte sequence of requested content.
    """
    if mode == "bin1":
        return b"\xff" * chunk_size
    if mode == "bin0":
        return b"\x00" * chunk_size
    if mode == "randbin":
        return os.urandom(chunk_size)
    if mode == "randutf8":
        s = "".join(random.choice(string.printable[:-6]) for _ in range(chunk_size))
        return s.encode("utf-8", "ignore")
    if mode == "randhex":
        s = os.urandom(max(1, chunk_size // 2)).hex()
        return s.encode("ascii")
    if mode == "random":
        return gen_random_bytes(
            random.choice(["bin1", "bin0", "randbin", "randutf8", "randhex"]), chunk_size
        )
    raise ValueError(f"Unknown mode: {mode}")


def make_token_iter(args) -> Iterable[bytes]:
    """Create an infinite iterator of encoded tokens.

    Honors word/dictionary modes or random binary/text modes based on args.

    \param args Parsed CLI arguments object.
    \return Generator yielding bytes payloads.
    """
    # Determine newline bytes and scope
    style = getattr(args, "newline_style", "lf")
    if style == "lf":
        nl_bytes = b"\n"
    elif style == "cr":
        nl_bytes = b"\r"
    else:
        nl_bytes = b"\r\n"
    scope = getattr(args, "newline_mode", "none")
    pump_mode = args.pump_mode or "word"
    if pump_mode == "word":
        enc = args.encoding
        # Resolve dictionary sources (single path + optional list of paths)
        dict_paths = []
        if getattr(args, "dict_path", None):
            dict_paths.append(Path(args.dict_path))
        if getattr(args, "dict_list", None):
            list_file = Path(args.dict_list)
            base_dir = list_file.parent
            with open(list_file, encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    p = Path(line)
                    if not p.is_absolute():
                        p = (base_dir / p).resolve()
                    dict_paths.append(p)
        if enc == "auto" and dict_paths:
            enc = detect_encoding(dict_paths[0])
        # Validate encoding
        try:
            codecs.lookup(enc)
        except Exception:
            raise SystemExit(f"Unknown encoding: {enc}")
        if dict_paths:
            if args.dict_ram:
                # Load all dict files into memory; support optional weights: "token weight"
                words: list[str] = []
                weights: list[float] = []
                for p in dict_paths:
                    with open(p, encoding=enc, errors="replace") as f:
                        for line in f:
                            s = line.strip()
                            if not s:
                                continue
                            parts = s.split()
                            if len(parts) >= 2 and parts[-1].replace(".", "", 1).isdigit():
                                try:
                                    w = float(parts[-1])
                                    token = " ".join(parts[:-1])
                                    words.append(token)
                                    weights.append(max(0.0, w))
                                    continue
                                except Exception:
                                    pass
                            words.append(s)
                if args.markov:
                    # Simple word-level N-gram model
                    n = max(2, int(getattr(args, "ngram", 2) or 2))
                    # Build transitions
                    transitions: dict[tuple[str, ...], list[str]] = {}
                    seq = words
                    if len(seq) >= n:
                        for i in range(len(seq) - n + 1):
                            key = tuple(seq[i : i + n - 1])
                            nxt = seq[i + n - 1]
                            transitions.setdefault(key, []).append(nxt)

                    def ram_markov():
                        import random as _r

                        if not transitions:
                            while True:
                                yield from seq
                        # start with random prefix
                        prefix = _r.choice(list(transitions.keys()))
                        while True:
                            choices = transitions.get(prefix)
                            if not choices:
                                prefix = _r.choice(list(transitions.keys()))
                                continue
                            nxt = _r.choice(choices)
                            yield nxt
                            prefix = (*prefix[1:], nxt)

                    token_source = ram_markov()
                elif args.dict_order == "reverse":
                    seq = list(reversed(words))

                    def ram_seq():
                        while True:
                            yield from seq

                    token_source = ram_seq()
                elif args.dict_order == "presorted":
                    seq = sorted(words)

                    def ram_sorted():
                        while True:
                            yield from seq

                    token_source = ram_sorted()
                elif args.dict_order == "random":

                    def ram_random():
                        while True:
                            if weights:
                                yield random.choices(words, weights=weights, k=1)[0]
                            else:
                                yield random.choice(words)

                    token_source = ram_random()
                else:

                    def ram_seq2():
                        while True:
                            yield from words

                    token_source = ram_seq2()
            else:
                # Without RAM: for a single dictionary, load once for non-sequential orders.
                if len(dict_paths) == 1 and args.dict_order in {"reverse", "presorted", "random"}:
                    p = dict_paths[0]
                    with open(p, encoding=enc, errors="replace") as f:
                        words = [w.strip() for w in f if w.strip()]
                    if args.dict_order == "reverse":
                        seq = list(reversed(words))

                        def single_rev():
                            while True:
                                yield from seq

                        token_source = single_rev()
                    elif args.dict_order == "presorted":
                        seq = sorted(words)

                        def single_sorted():
                            while True:
                                yield from seq

                        token_source = single_sorted()
                    else:  # random

                        def single_random():
                            while True:
                                yield random.choice(words)

                        token_source = single_random()
                else:
                    # Streaming over multiple dict files supports sequential order only
                    if args.dict_order != "sequential":
                        raise SystemExit(
                            "--dict-order requires --dict-ram for non-sequential orders (multi)"
                        )

                    def stream_multi_seq():
                        while True:
                            for p in dict_paths:
                                with open(p, encoding=enc, errors="replace") as f:
                                    for line in f:
                                        line = line.strip()
                                        if line:
                                            yield line

                    token_source = stream_multi_seq()
        else:
            if args.word is None:
                raise SystemExit("--word is required for pump-mode=word without --dict")

            if args.mode == "random":

                def word_stream():
                    base = args.word
                    while True:
                        yield base.lower() if random.random() < 0.5 else base.upper()

                token_source = word_stream()
            else:

                def word_stream_fixed():
                    while True:
                        yield args.word

                token_source = word_stream_fixed()

        def bytes_stream():
            for t in token_source:
                if scope == "char":
                    part = b"".join(ch.encode(enc, errors="replace") + nl_bytes for ch in t)
                    yield part
                elif scope == "word":
                    yield t.encode(enc, errors="replace") + nl_bytes
                else:
                    yield t.encode(enc, errors="replace")

        return bytes_stream()
    else:

        def bytes_stream():
            while True:
                yield gen_random_bytes(pump_mode, args.chunk)

        return bytes_stream()



