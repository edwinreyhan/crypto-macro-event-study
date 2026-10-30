import hashlib
from datetime import date

import pytest

from crypto_events.download import (
    ChecksumError,
    daily_file_name,
    download_daily,
    download_file,
    kline_url,
    local_path,
    monthly_file_name,
    parse_checksum,
)

ZIP_BYTES = b"fake zip content"
GOOD_SHA = hashlib.sha256(ZIP_BYTES).hexdigest()


class FakeServer:
    """Stands in for data.binance.vision: maps URL -> bytes and records every request."""

    def __init__(self, files: dict[str, bytes]):
        self.files = files
        self.requests: list[str] = []

    def __call__(self, url: str) -> bytes:
        self.requests.append(url)
        return self.files[url]


def serve(url: str, content: bytes = ZIP_BYTES, sha: str = GOOD_SHA) -> FakeServer:
    return FakeServer({url: content, url + ".CHECKSUM": f"{sha}  file.zip\n".encode()})


def test_daily_url():
    name = daily_file_name("BTCUSDT", date(2026, 10, 29))
    assert kline_url("BTCUSDT", name, "daily") == (
        "https://data.binance.vision/data/spot/daily/klines/BTCUSDT/1m/BTCUSDT-1m-2026-10-29.zip"
    )


def test_monthly_url_pads_month():
    name = monthly_file_name("BTCUSDT", 2020, 1)
    assert kline_url("BTCUSDT", name, "monthly") == (
        "https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1m/BTCUSDT-1m-2020-01.zip"
    )


def test_unknown_period_is_rejected():
    with pytest.raises(ValueError):
        kline_url("BTCUSDT", "x.zip", "weekly")


def test_parse_checksum():
    line = f"{GOOD_SHA.upper()}  BTCUSDT-1m-2026-10-29.zip\n"
    assert parse_checksum(line) == GOOD_SHA


def test_parse_checksum_rejects_garbage():
    with pytest.raises(ValueError):
        parse_checksum("<html>Not found</html>")


def test_download_saves_verified_file(tmp_path):
    url = "https://example.test/a.zip"
    dest = tmp_path / "a.zip"
    assert download_file(url, dest, serve(url)) is True
    assert dest.read_bytes() == ZIP_BYTES


def test_checksum_mismatch_leaves_no_file(tmp_path):
    url = "https://example.test/a.zip"
    dest = tmp_path / "a.zip"
    with pytest.raises(ChecksumError):
        download_file(url, dest, serve(url, sha="0" * 64))
    assert list(tmp_path.iterdir()) == []  # neither the file nor a .part leftover


def test_existing_verified_file_is_skipped(tmp_path):
    url = "https://example.test/a.zip"
    dest = tmp_path / "a.zip"
    dest.write_bytes(ZIP_BYTES)
    server = serve(url)
    assert download_file(url, dest, server) is False
    assert server.requests == [url + ".CHECKSUM"]  # the zip itself was not downloaded again


def test_corrupt_existing_file_is_replaced(tmp_path):
    url = "https://example.test/a.zip"
    dest = tmp_path / "a.zip"
    dest.write_bytes(b"half a download")
    assert download_file(url, dest, serve(url)) is True
    assert dest.read_bytes() == ZIP_BYTES


def test_download_daily_uses_partitioned_path(tmp_path):
    day = date(2026, 10, 29)
    url = kline_url("BTCUSDT", daily_file_name("BTCUSDT", day), "daily")
    path = download_daily("BTCUSDT", day, root=tmp_path, fetch=serve(url))
    assert path == local_path(tmp_path, "BTCUSDT", "BTCUSDT-1m-2026-10-29.zip")
    assert path.relative_to(tmp_path).as_posix() == (
        "klines/interval=1m/symbol=BTCUSDT/BTCUSDT-1m-2026-10-29.zip"
    )
