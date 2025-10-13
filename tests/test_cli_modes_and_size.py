from pathlib import Path

from writetofillet.cli import main


def run(args):
    assert main(args) == 0


def test_binary_fixed_modes_sizes(tmp_path: Path):
    out1 = tmp_path / "ff.bin"
    out0 = tmp_path / "zero.bin"
    size = "8KiB"
    run(["--pump-mode", "bin1", "--size", size, str(out1)])
    run(["--pump-mode", "bin0", "--size", size, str(out0)])
    b1 = out1.read_bytes()
    b0 = out0.read_bytes()
    assert len(b1) == 8192 and set(b1) == {0xFF}
    assert len(b0) == 8192 and set(b0) == {0x00}


def test_random_modes_sizes(tmp_path: Path):
    out_bin = tmp_path / "rand.bin"
    out_utf8 = tmp_path / "rand.txt"
    out_hex = tmp_path / "rand.hex"
    run(["--pump-mode", "randbin", "--size", "6KiB", str(out_bin)])
    run(["--pump-mode", "randutf8", "--size", "5KiB", str(out_utf8)])
    run(["--pump-mode", "randhex", "--size", "4KiB", str(out_hex)])
    assert out_bin.stat().st_size == 6144
    assert out_utf8.stat().st_size == 5120
    assert out_hex.stat().st_size == 4096
    # Basic content checks
    out_utf8.read_text(encoding="utf-8")  # should decode
    txt = out_hex.read_text(encoding="ascii")
    assert set(txt) <= set("0123456789abcdef")


def test_word_size_truncation(tmp_path: Path):
    out = tmp_path / "out.txt"
    # Word of length 3, request size 10; last chunk should be truncated
    run(["--word", "XYZ", "--size", "10B", str(out)])
    data = out.read_bytes()
    assert len(data) == 10
    assert data.startswith(b"XYZXYZXYZ")
