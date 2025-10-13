from pathlib import Path

import pytest

from writetofillet.cli import main


def run(args):
    assert main(args) == 0


def test_ram_buffer_small_dump(tmp_path: Path):
    out = tmp_path / "ram.bin"
    run(["--pump-mode", "bin0", "--size", "8KiB", "--buffer-mode", "ram", str(out)])
    assert out.stat().st_size == 8192


def test_ram_guard_fallback_stream(tmp_path: Path, capsys):
    out = tmp_path / "fallback.bin"
    # Request larger than ram-max; expect success via streaming
    run(["--pump-mode", "bin1", "--size", "64KiB", "--ram-max", "1KiB", str(out)])
    assert out.stat().st_size == 65536
    # Verify info message about fallback printed to stderr
    captured = capsys.readouterr()
    assert "Falling back to streaming" in captured.err


def test_dict_random_requires_ram(tmp_path: Path):
    words = tmp_path / "words.txt"
    words.write_text("a\nb\n", encoding="utf-8")
    out = tmp_path / "out.txt"
    with pytest.raises(SystemExit):
        main(["--dict", str(words), "--dict-order", "random", "--times", "1", str(out)])
