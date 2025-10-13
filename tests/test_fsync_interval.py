from pathlib import Path
from writetofillet.cli import main


def test_fsync_interval_write(tmp_path: Path):
    out = tmp_path / "fsync.txt"
    # Write 8KiB with fsync every 1KiB; should complete and produce exact size
    rc = main(["--write-mode", "normal-write", "--word", "X", "--size", "8KiB", "--fsync-enable", "--fsync-interval", "1KiB", str(out)])
    assert rc == 0
    assert out.stat().st_size == 8192
