from pathlib import Path

from writetofillet.cli import main


def run(args):
    assert main(args) == 0


def test_target_directory(tmp_path: Path):
    d = tmp_path / "folder"
    d.mkdir()
    f1 = d / "a.txt"
    f2 = d / "b.txt"
    f1.write_text("", encoding="utf-8")
    f2.write_text("", encoding="utf-8")
    run(["--write-mode", "normal-append", "--word", "Z", "--times", "3", str(d)])
    assert f1.read_text(encoding="utf-8") == "ZZZ"
    assert f2.read_text(encoding="utf-8") == "ZZZ"


def test_filelist_paths(tmp_path: Path):
    f1 = tmp_path / "x.txt"
    f2 = tmp_path / "y.bin"
    f1.parent.mkdir(parents=True, exist_ok=True)
    f1.write_text("", encoding="utf-8")
    f2.write_bytes(b"")
    filelist = tmp_path / "list.txt"
    filelist.write_text(f"x.txt\n{f2}\n", encoding="utf-8")
    # Pass tmp_path as positional path; targets come from filelist
    run(
        [
            "--write-mode",
            "binary-append",
            "--times",
            "2",
            "--chunk",
            "1KiB",
            "--filelist",
            str(filelist),
            str(tmp_path),
        ]
    )
    assert f1.stat().st_size == 2048
    assert f2.stat().st_size == 2048
