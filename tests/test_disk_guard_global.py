from pathlib import Path

from writetofillet.cli import main


def test_global_guard_blocks_multiple_targets(tmp_path: Path):
    # Create two targets in a directory
    d = tmp_path / "dir"
    d.mkdir()
    (d / "a.bin").write_bytes(b"")
    (d / "b.bin").write_bytes(b"")
    # Massive margin to trigger failure upfront
    rc = main(
        [
            "--write-mode",
            "binary-write",
            "--size",
            "1KiB",
            "--disk-guard-margin",
            "100000TB",
            str(d),
        ]
    )
    assert rc != 0


def test_global_guard_disabled_allows(tmp_path: Path):
    d = tmp_path / "dir2"
    d.mkdir()
    a = d / "a.bin"
    b = d / "b.bin"
    a.write_bytes(b"")
    b.write_bytes(b"")
    rc = main(
        [
            "--write-mode",
            "binary-write",
            "--size",
            "1KiB",
            "--disk-guard-margin",
            "100000TB",
            "--disable-disk-guard",
            str(d),
        ]
    )
    assert rc == 0
    assert a.stat().st_size == 1024
    assert b.stat().st_size == 1024
