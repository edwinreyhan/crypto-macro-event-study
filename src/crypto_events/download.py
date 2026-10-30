"""Download Binance spot kline (candle) files from data.binance.vision.

Files are saved unchanged under ``data/raw`` and checked against Binance's SHA-256 checksum.
Already-downloaded files are skipped, so re-running a download is safe.
"""

from __future__ import annotations

import argparse
import hashlib
import urllib.request
from collections.abc import Callable
from datetime import date
from pathlib import Path

BASE_URL = "https://data.binance.vision/data/spot"
DEFAULT_ROOT = Path("data/raw")

Fetch = Callable[[str], bytes]


class ChecksumError(Exception):
    """The downloaded file does not match Binance's published checksum."""


def daily_file_name(symbol: str, day: date, interval: str = "1m") -> str:
    return f"{symbol}-{interval}-{day.isoformat()}.zip"


def monthly_file_name(symbol: str, year: int, month: int, interval: str = "1m") -> str:
    return f"{symbol}-{interval}-{year:04d}-{month:02d}.zip"


def kline_url(symbol: str, file_name: str, period: str, interval: str = "1m") -> str:
    """URL of one kline zip; ``period`` is ``"daily"`` or ``"monthly"``."""
    if period not in ("daily", "monthly"):
        raise ValueError(f"period must be 'daily' or 'monthly', got {period!r}")
    return f"{BASE_URL}/{period}/klines/{symbol}/{interval}/{file_name}"


def local_path(root: Path, symbol: str, file_name: str, interval: str = "1m") -> Path:
    return root / "klines" / f"interval={interval}" / f"symbol={symbol}" / file_name


def parse_checksum(text: str) -> str:
    """Return the hex digest from a ``.CHECKSUM`` file (``"<sha256>  <file name>"``)."""
    parts = text.split()
    if not parts or len(parts[0]) != 64:
        raise ValueError(f"not a SHA-256 checksum line: {text!r}")
    return parts[0].lower()


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def http_get(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read()


def download_file(url: str, dest: Path, fetch: Fetch = http_get) -> bool:
    """Download ``url`` to ``dest`` and verify its checksum.

    Returns True if a file was downloaded, False if a verified copy already existed.
    A file that fails the checksum is never left at ``dest``.
    """
    expected = parse_checksum(fetch(url + ".CHECKSUM").decode())
    if dest.exists() and sha256_of(dest) == expected:
        return False

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    tmp.write_bytes(fetch(url))
    actual = sha256_of(tmp)
    if actual != expected:
        tmp.unlink()
        raise ChecksumError(f"{url}: expected {expected}, got {actual}")
    tmp.replace(dest)  # rename only after the checksum passed
    return True


def download_daily(
    symbol: str, day: date, root: Path = DEFAULT_ROOT, fetch: Fetch = http_get
) -> Path:
    name = daily_file_name(symbol, day)
    dest = local_path(root, symbol, name)
    download_file(kline_url(symbol, name, "daily"), dest, fetch)
    return dest


def download_monthly(
    symbol: str,
    year: int,
    month: int,
    root: Path = DEFAULT_ROOT,
    fetch: Fetch = http_get,
    interval: str = "1m",
) -> Path:
    name = monthly_file_name(symbol, year, month, interval)
    dest = local_path(root, symbol, name, interval)
    download_file(kline_url(symbol, name, "monthly", interval), dest, fetch)
    return dest


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Download Binance spot 1m kline files.")
    parser.add_argument("symbol", help="e.g. BTCUSDT")
    when = parser.add_mutually_exclusive_group(required=True)
    when.add_argument("--day", type=date.fromisoformat, help="YYYY-MM-DD (daily file)")
    when.add_argument("--month", help="YYYY-MM (monthly file)")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args(argv)

    if args.day:
        path = download_daily(args.symbol, args.day, args.root)
    else:
        year, month = (int(x) for x in args.month.split("-"))
        path = download_monthly(args.symbol, year, month, args.root)
    print(path)


if __name__ == "__main__":
    main()
