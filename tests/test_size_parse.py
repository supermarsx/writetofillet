from writetofillet._sizeutil import parse_human_size


def test_parse_sizes():
    assert parse_human_size("1KiB") == 1024
    assert parse_human_size("2KB") == 2000
    assert parse_human_size("1MB") == 1_000_000
    assert parse_human_size("1MiB") == 1_048_576
    assert parse_human_size("10B") == 10
    assert parse_human_size("10bytes") == 10
    assert parse_human_size("1TB") == 1_000_000_000_000
