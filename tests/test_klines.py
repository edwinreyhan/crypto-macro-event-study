import gzip
import zipfile
from datetime import datetime

import pytest

from crypto_events.extract import extract_to_gzip, staging_path
from crypto_events.klines import read_klines

# Real first rows of BTCUSDT 1m files (T1): 2024-12-31 is in ms (13 digits), 2026-10-29 in µs (16).
ROW_MS = (
    "1735603200000,92792.05000000,92832.25000000,92782.12000000,92782.13000000,"
    "6.45789000,1735603259999,599298.29174060,1660,4.36611000,405183.17952120,0"
)
ROW_US = (
    "1793232000000000,81343.51000000,81366.01000000,81343.51000000,81366.00000000,"
    "1.90814000,1793232059999999,155242.64395820,995,1.75930000,143132.44898180,0"
)


def write_gz(path, *rows):
    with gzip.open(path, "wt") as f:
        f.write("\n".join(rows) + "\n")
    return str(path)


def test_extract_zip_to_gzip(tmp_path):
    zip_path = tmp_path / "raw" / "BTCUSDT-1m-2024-12-31.zip"
    zip_path.parent.mkdir()
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("BTCUSDT-1m-2024-12-31.csv", ROW_MS + "\n")
    dest = extract_to_gzip(zip_path, tmp_path / "staging" / "BTCUSDT-1m-2024-12-31.csv.gz")
    assert gzip.open(dest, "rt").read() == ROW_MS + "\n"
    assert not dest.with_name(dest.name + ".part").exists()


def test_staging_path_mirrors_raw_layout(tmp_path):
    raw = tmp_path / "raw"
    zip_path = raw / "klines" / "interval=1m" / "symbol=BTCUSDT" / "BTCUSDT-1m-2024-12-31.zip"
    got = staging_path(zip_path, raw, tmp_path / "staging")
    assert got == (
        tmp_path / "staging/klines/interval=1m/symbol=BTCUSDT/BTCUSDT-1m-2024-12-31.csv.gz"
    )


def test_milliseconds_and_microseconds_both_become_utc(spark, tmp_path):
    paths = [write_gz(tmp_path / "ms.csv.gz", ROW_MS), write_gz(tmp_path / "us.csv.gz", ROW_US)]
    rows = read_klines(spark, paths, "BTCUSDT").orderBy("open_time_utc").collect()
    assert [r.open_time_utc for r in rows] == [
        datetime(2024, 12, 31, 0, 0),  # 1735603200000 ms
        datetime(2026, 10, 29, 0, 0),  # 1793232000000000 µs
    ]
    assert rows[0].symbol == "BTCUSDT"
    assert rows[0].close == pytest.approx(92782.13)
    assert rows[1].number_of_trades == 995


def test_output_columns(spark, tmp_path):
    df = read_klines(spark, [write_gz(tmp_path / "ms.csv.gz", ROW_MS)], "BTCUSDT")
    assert df.columns == [
        "symbol",
        "open_time_utc",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "quote_asset_volume",
        "number_of_trades",
    ]


def test_text_in_a_number_column_fails(spark, tmp_path):
    bad = ROW_MS.replace("92792.05000000", "not-a-price")
    df = read_klines(spark, [write_gz(tmp_path / "bad.csv.gz", bad)], "BTCUSDT")
    with pytest.raises(Exception, match="(?i)malformed|FAILFAST"):
        df.collect()


def test_reading_a_zip_by_mistake_fails(spark, tmp_path):
    # T10: without FAILFAST, Spark returned 510 rows of compressed bytes from a zip, with no error.
    zip_path = tmp_path / "BTCUSDT-1m-2024-12-31.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("BTCUSDT-1m-2024-12-31.csv", (ROW_MS + "\n") * 500)
    df = read_klines(spark, [str(zip_path)], "BTCUSDT")
    with pytest.raises(Exception, match="(?i)malformed|FAILFAST"):
        df.collect()
