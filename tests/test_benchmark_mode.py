from writetofillet.cli import main


def test_benchmark_runs_quickly(tmp_path, monkeypatch):
    # Use a tiny bench size to keep runtime low in CI
    rc = main(["--benchmark", "--bench-size", "512KiB"])
    assert rc == 0

