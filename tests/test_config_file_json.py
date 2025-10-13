import json
from pathlib import Path
from writetofillet.cli import main


def test_config_json_applies_defaults(tmp_path: Path):
    cfg = {
        "write_mode": "normal-write",
        "word": "Q",
        "times": 2,
    }
    cpath = tmp_path / "cfg.json"
    cpath.write_text(json.dumps(cfg), encoding="utf-8")
    out = tmp_path / "out.txt"
    rc = main(["--config", str(cpath), str(out)])
    assert rc == 0
    assert out.read_text(encoding="utf-8") == "QQ"

