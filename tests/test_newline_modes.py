from pathlib import Path

from writetofillet.cli import main


def run(args):
    assert main(args) == 0


def test_newline_word_lf(tmp_path: Path):
    out = tmp_path / "out.txt"
    run(
        [
            "--write-mode",
            "normal-write",
            "--word",
            "AB",
            "--times",
            "2",
            "--newline-mode",
            "word",
            "--newline-style",
            "lf",
            str(out),
        ]
    )
    assert out.read_text(encoding="utf-8") == "AB\nAB\n"


def test_newline_char_crlf(tmp_path: Path):
    out = tmp_path / "out2.txt"
    run(
        [
            "--write-mode",
            "normal-write",
            "--word",
            "AB",
            "--times",
            "1",
            "--newline-mode",
            "char",
            "--newline-style",
            "crlf",
            str(out),
        ]
    )
    assert out.read_bytes() == b"A\r\nB\r\n"
