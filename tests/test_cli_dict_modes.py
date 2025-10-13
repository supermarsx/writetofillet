from pathlib import Path

from writetofillet.cli import main


def run(args):
    assert main(args) == 0


def test_dict_sequential_and_reverse(tmp_path: Path):
    words = tmp_path / "words.txt"
    words.write_text("one\ntwo\nthree\n", encoding="utf-8")
    out1 = tmp_path / "seq.txt"
    out2 = tmp_path / "rev.txt"
    run(
        ["--dict", str(words), "--dict-order", "sequential", "--times", "3", "--newline", str(out1)]
    )
    run(["--dict", str(words), "--dict-order", "reverse", "--times", "3", "--newline", str(out2)])
    assert out1.read_text(encoding="utf-8") == "one\ntwo\nthree\n"
    assert out2.read_text(encoding="utf-8") == "three\ntwo\none\n"


def test_dict_random_with_seed(tmp_path: Path):
    words = tmp_path / "words.txt"
    words.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
    out = tmp_path / "rand.txt"
    # With seed, first pick is deterministic in our implementation
    run(["--dict", str(words), "--dict-order", "random", "--times", "1", "--seed", "123", str(out)])
    assert out.read_text(encoding="utf-8") in {"alpha", "beta", "gamma"}
