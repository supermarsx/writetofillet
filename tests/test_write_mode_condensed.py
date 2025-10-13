from pathlib import Path
from writetofillet.cli import main


def run(args):
    assert main(args) == 0


def test_write_mode_binary_append(tmp_path: Path):
    out = tmp_path / "out.bin"
    run(["--write-mode", "binary-append", "--size", "4KiB", str(out)])
    assert out.stat().st_size == 4096


def test_write_mode_normal_write(tmp_path: Path):
    out = tmp_path / "out.txt"
    run(["--word", "A", "--times", "2", str(out)])
    # Now overwrite using condensed mode
    run(["--write-mode", "normal-write", "--word", "B", "--times", "1", str(out)])
    assert out.read_bytes() == b"B"

