from pathlib import Path
from writetofillet.cli import main


def run(args):
    assert main(args) == 0


def test_dict_presorted_with_ram_orders_tokens(tmp_path: Path):
    words = tmp_path / "words.txt"
    words.write_text("charlie\nalpha\nbravo\n", encoding="utf-8")
    out = tmp_path / "out.txt"
    run([
        "--dict", str(words),
        "--dict-order", "presorted",
        "--dict-ram",
        "--times", "3",
        "--newline",
        str(out),
    ])
    # Presorted should be alphabetical: alpha, bravo, charlie
    assert out.read_text(encoding="utf-8") == "alpha\nbravo\ncharlie\n"


def test_dict_random_with_ram_and_seed_outputs_valid_tokens(tmp_path: Path):
    words = tmp_path / "words.txt"
    words.write_text("x\ny\nz\n", encoding="utf-8")
    out = tmp_path / "out.txt"
    run([
        "--dict", str(words),
        "--dict-order", "random",
        "--dict-ram",
        "--times", "5",
        "--seed", "42",
        str(out),
    ])
    content = out.read_text(encoding="utf-8")
    tokens = content.split("\n")
    if tokens[-1] == "":
        tokens = tokens[:-1]
    assert len(tokens) == 5
    assert set(tokens).issubset({"x", "y", "z"})

