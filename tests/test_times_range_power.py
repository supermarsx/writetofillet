from writetofillet.cli import main


def run(args):
    assert main(args) == 0


def test_times_range_scientific(tmp_path):
    out = tmp_path / "out.bin"
    # Choose between 1000 and 2000 using scientific notation
    run(["--write-mode", "binary-write", "--times-range", "1e3,2e3", str(out)])
    # Can't assert exact length due to randomness; ensure file exists and non-zero size
    assert out.exists() and out.stat().st_size > 0


def test_times_range_power(tmp_path):
    out = tmp_path / "out2.bin"
    # Choose between 2^10 and 2^11 writes
    run(["--write-mode", "binary-write", "--times-range", "2^10,2^11", "--chunk", "1KiB", str(out)])
    # Size should be between 1MiB and 2MiB approximately
    size = out.stat().st_size
    assert 1_024_000 <= size <= 2_100_000

