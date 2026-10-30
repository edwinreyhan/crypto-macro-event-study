"""Pick the coins to study: the most traded USDT pairs that have data since 2020.

Rules (requirement FR1):
1. Start from a list of long-listed USDT pairs (``CANDIDATES``).
2. Drop stablecoins (their price barely moves, so an event study says nothing).
3. Keep pairs with data in the first month (2020-01) **and** a recent month (still trading).
4. Rank by total quote volume (USDT traded) in a fixed year, keep the top N.

Volumes come from Binance's small daily-candle files (``1d``), not the large minute files.
"""

from __future__ import annotations

import argparse
import csv
import io
import urllib.error
import zipfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from crypto_events.download import DEFAULT_ROOT, download_monthly

QUOTE = "USDT"
STABLECOINS = {"USDC", "BUSD", "TUSD", "USDP", "PAX", "DAI", "FDUSD", "USDS", "EUR", "AEUR"}

# Long-listed USDT pairs, plus a few stablecoins and later listings so the filters are visible.
CANDIDATES = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "LINKUSDT", "LTCUSDT",
    "BCHUSDT", "TRXUSDT", "ETCUSDT", "XLMUSDT", "EOSUSDT", "ATOMUSDT", "XTZUSDT", "VETUSDT",
    "NEOUSDT", "IOTAUSDT", "ALGOUSDT", "ZECUSDT", "DASHUSDT", "XMRUSDT", "ONTUSDT", "QTUMUSDT",
    "BATUSDT", "ZILUSDT", "ICXUSDT", "KAVAUSDT", "MATICUSDT", "FTMUSDT", "HBARUSDT", "RVNUSDT",
    "ENJUSDT", "CHZUSDT", "THETAUSDT", "ONEUSDT", "IOSTUSDT", "WAVESUSDT", "OMGUSDT", "BANDUSDT",
    "SOLUSDT", "DOTUSDT", "AVAXUSDT",  # listed later in 2020 -> no 2020-01 data
    "USDCUSDT", "TUSDUSDT", "BUSDUSDT",  # stablecoins
]  # fmt: skip


@dataclass(frozen=True)
class Pick:
    rank: int
    symbol: str
    base_asset: str
    quote_volume: float


def base_asset(symbol: str) -> str:
    if not symbol.endswith(QUOTE):
        raise ValueError(f"{symbol} is not a {QUOTE} pair")
    return symbol[: -len(QUOTE)]


def is_stablecoin(symbol: str) -> bool:
    return base_asset(symbol) in STABLECOINS


def quote_volume_from_zip(path: Path) -> float:
    """Sum the quote asset volume (8th column, USDT traded) of every candle in a kline zip."""
    total = 0.0
    with zipfile.ZipFile(path) as zf:
        for name in zf.namelist():
            with zf.open(name) as f:
                for row in csv.reader(io.TextIOWrapper(f, encoding="utf-8")):
                    if row and row[0].isdigit():  # skip a header row if one ever appears
                        total += float(row[7])
    return total


def pick_symbols(
    candidates: Iterable[str],
    has_month: Callable[[str, str], bool],
    yearly_volume: Callable[[str], float],
    first_month: str,
    last_month: str,
    top_n: int = 20,
) -> list[Pick]:
    """Apply the module rules. ``has_month(symbol, "YYYY-MM")`` says whether data exists."""
    kept = [
        s
        for s in candidates
        if not is_stablecoin(s) and has_month(s, first_month) and has_month(s, last_month)
    ]
    volumes = {s: yearly_volume(s) for s in kept}
    ranked = sorted(kept, key=lambda s: volumes[s], reverse=True)[:top_n]
    return [Pick(i, s, base_asset(s), volumes[s]) for i, s in enumerate(ranked, start=1)]


def write_picks(picks: list[Pick], path: Path, volume_year: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["rank", "symbol", "base_asset", f"quote_volume_{volume_year}_usdt"])
        for p in picks:
            w.writerow([p.rank, p.symbol, p.base_asset, round(p.quote_volume)])


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Pick the top-N USDT pairs by yearly volume.")
    parser.add_argument("--first-month", default="2020-01")
    parser.add_argument("--last-month", required=True, help="a recent full month, YYYY-MM")
    parser.add_argument("--volume-year", type=int, default=2025)
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--out", type=Path, default=Path("seeds/symbols.csv"))
    args = parser.parse_args(argv)

    def monthly_1d(symbol: str, month: str) -> Path:
        year, mon = (int(x) for x in month.split("-"))
        return download_monthly(symbol, year, mon, args.root, interval="1d")

    def has_month(symbol: str, month: str) -> bool:
        try:
            monthly_1d(symbol, month)
            return True
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False
            raise

    def yearly_volume(symbol: str) -> float:
        months = [f"{args.volume_year}-{m:02d}" for m in range(1, 13)]
        return sum(quote_volume_from_zip(monthly_1d(symbol, m)) for m in months)

    picks = pick_symbols(
        CANDIDATES, has_month, yearly_volume, args.first_month, args.last_month, args.top
    )
    write_picks(picks, args.out, args.volume_year)
    for p in picks:
        print(f"{p.rank:>2} {p.symbol:<10} {p.quote_volume:>20,.0f}")


if __name__ == "__main__":
    main()
