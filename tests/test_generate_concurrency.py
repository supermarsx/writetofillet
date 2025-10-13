from pathlib import Path
from writetofillet.cli import main


def run(args):
    assert main(args) == 0


def test_generate_pipeline_random_hex(tmp_path: Path):
    out = tmp_path / "gen.hex"
    run([
        "--write-mode", "binary-write",
        "--pump-mode", "randhex",
        "--size", "12KiB",
        "--concurrency", "generate",
        "--gen-workers", "2",
        str(out),
    ])
    data = out.read_text(encoding="ascii")
    assert len(data) == 12 * 1024
    assert set(data) <= set("0123456789abcdef")

