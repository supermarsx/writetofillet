from pathlib import Path
from writetofillet.cli import main


def run(args):
    assert main(args) == 0


def test_normal_write_overwrites(tmp_path: Path):
    out = tmp_path / "out.txt"
    run(["--write-mode", "normal-append", "--word", "A", "--times", "3", str(out)])
    run(["--write-mode", "normal-write", "--word", "B", "--times", "1", str(out)])
    assert out.read_text(encoding="utf-8") == "B"

