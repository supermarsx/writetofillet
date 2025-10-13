from pathlib import Path
from writetofillet.cli import main


def run(args):
    assert main(args) == 0


def test_dict_list_ram_presorted(tmp_path: Path):
    d1 = tmp_path / "d1.txt"
    d2 = tmp_path / "d2.txt"
    d1.write_text("b\na\n", encoding="utf-8")
    d2.write_text("c\n", encoding="utf-8")
    lst = tmp_path / "dicts.txt"
    lst.write_text("d1.txt\n" + str(d2) + "\n", encoding="utf-8")
    out = tmp_path / "out.txt"
    run([
        "--dict-list", str(lst),
        "--dict-order", "presorted",
        "--dict-ram",
        "--times", "3",
        "--newline-mode", "word",
        str(out),
    ])
    # presorted combined: a, b, c
    assert out.read_text(encoding="utf-8") == "a\nb\nc\n"


def test_dict_list_stream_sequential(tmp_path: Path):
    d1 = tmp_path / "s1.txt"
    d2 = tmp_path / "s2.txt"
    d1.write_text("x\ny\n", encoding="utf-8")
    d2.write_text("z\n", encoding="utf-8")
    lst = tmp_path / "dicts2.txt"
    lst.write_text("s1.txt\n" + str(d2) + "\n", encoding="utf-8")
    out = tmp_path / "out2.txt"
    run([
        "--dict-list", str(lst),
        "--dict-order", "sequential",
        "--times", "3",
        "--newline-mode", "word",
        str(out),
    ])
    assert out.read_text(encoding="utf-8") == "x\ny\nz\n"

