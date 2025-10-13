from pathlib import Path
from writetofillet.cli import main


def test_disk_guard_margin_blocks(tmp_path: Path):
    out = tmp_path / "block.bin"
    # Set an absurdly high margin to ensure guard triggers regardless of actual free space
    rc = main(["--write-mode", "binary-write", "--size", "1KiB", "--disk-guard-margin", "100000TB", str(out)])
    assert rc != 0


def test_disk_guard_disable_allows(tmp_path: Path):
    out = tmp_path / "allow.bin"
    rc = main(["--write-mode", "binary-write", "--size", "1KiB", "--disk-guard-margin", "100000TB", "--disable-disk-guard", str(out)])
    assert rc == 0
    assert out.stat().st_size == 1024

