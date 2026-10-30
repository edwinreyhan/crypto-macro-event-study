import csv
import zipfile

import pytest

from crypto_events.symbols import (
    base_asset,
    is_stablecoin,
    pick_symbols,
    quote_volume_from_zip,
    write_picks,
)


def test_base_asset():
    assert base_asset("BTCUSDT") == "BTC"
    with pytest.raises(ValueError):
        base_asset("BTCEUR")


def test_stablecoins_are_detected():
    assert is_stablecoin("USDCUSDT")
    assert is_stablecoin("FDUSDUSDT")
    assert not is_stablecoin("BTCUSDT")


def test_quote_volume_sums_the_8th_column(tmp_path):
    rows = [
        "1735689600000000,1,2,0.5,1.5,10,1735775999999999,1000.5,7,5,500,0",
        "1735776000000000,1,2,0.5,1.5,10,1735862399999999,2000.25,7,5,500,0",
    ]
    path = tmp_path / "X-1d-2025-01.zip"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("X-1d-2025-01.csv", "\n".join(rows) + "\n")
    assert quote_volume_from_zip(path) == pytest.approx(3000.75)


# Fake market: which months exist per symbol, and yearly volume.
MONTHS = {
    "BTCUSDT": {"2020-01", "2026-09"},
    "ETHUSDT": {"2020-01", "2026-09"},
    "XRPUSDT": {"2020-01", "2026-09"},
    "SOLUSDT": {"2026-09"},  # listed after 2020-01
    "MATICUSDT": {"2020-01"},  # delisted since
    "USDCUSDT": {"2020-01", "2026-09"},  # stablecoin
}
VOLUME = {"BTCUSDT": 300.0, "ETHUSDT": 200.0, "XRPUSDT": 100.0, "USDCUSDT": 999.0}


def pick(top_n=20):
    return pick_symbols(
        MONTHS,
        has_month=lambda s, m: m in MONTHS[s],
        yearly_volume=lambda s: VOLUME[s],
        first_month="2020-01",
        last_month="2026-09",
        top_n=top_n,
    )


def test_filters_and_ranking():
    picks = pick()
    assert [p.symbol for p in picks] == ["BTCUSDT", "ETHUSDT", "XRPUSDT"]
    assert [p.rank for p in picks] == [1, 2, 3]


def test_top_n_cuts_the_list():
    assert [p.symbol for p in pick(top_n=2)] == ["BTCUSDT", "ETHUSDT"]


def test_write_picks(tmp_path):
    out = tmp_path / "symbols.csv"
    write_picks(pick(), out, volume_year=2025)
    rows = list(csv.DictReader(out.open()))
    assert rows[0] == {
        "rank": "1",
        "symbol": "BTCUSDT",
        "base_asset": "BTC",
        "quote_volume_2025_usdt": "300",
    }
