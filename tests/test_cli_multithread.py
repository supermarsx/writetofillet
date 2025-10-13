from pathlib import Path

from writetofillet.cli import main


def run(args):
    assert main(args) == 0


def test_multithread_size_exact(tmp_path: Path):
    out = tmp_path / "mt.bin"
    run(["--pump-mode", "randbin", "--size", "64KiB", "--workers", "4", str(out)])
    assert out.stat().st_size == 65536
