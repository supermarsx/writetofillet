from pathlib import Path
from writetofillet.cli import main


def run(args):
    # Run CLI main with provided args list
    assert main(args) == 0


def test_word_times_overwrite(tmp_path: Path):
    out = tmp_path / "out.txt"
    run(["--word", "X", "--times", "5", str(out)])
    data = out.read_bytes()
    assert data == b"X" * 5

    # Overwrite
    run(["--word", "Y", "--times", "3", str(out)])
    assert out.read_bytes() == b"Y" * 3


def test_word_append_and_newline(tmp_path: Path):
    out = tmp_path / "out.txt"
    run(["--word", "A", "--times", "2", str(out)])
    run(["--word", "B", "--times", "2", "--newline", str(out)])
    # First two 'A's then two lines of 'B' with newlines
    assert out.read_bytes() == b"AA" + b"B\nB\n"
