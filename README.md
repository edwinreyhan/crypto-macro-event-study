# crypto-macro-event-study

[![CI](https://github.com/edwinreyhan/crypto-macro-event-study/actions/workflows/ci.yml/badge.svg)](https://github.com/edwinreyhan/crypto-macro-event-study/actions/workflows/ci.yml)

How do crypto prices react, minute by minute, to US inflation (CPI) releases and Fed (FOMC) decisions?
This project runs an **event study** on years of 1-minute price data with **PySpark**, **Delta Lake**, and **AWS**,
with an extra section on Bank Indonesia rate decisions and prices in IDR.

> 🚧 **Work in progress.** First version planned for end of December 2026.

## Planned pipeline

| Layer | What |
| --- | --- |
| raw | Daily 1-minute candle files from Binance public data, stored unchanged |
| silver | Clean minute prices (UTC, deduplicated), USD → IDR rate |
| gold | Events table (CPI, FOMC, BI), event windows with abnormal and cumulative abnormal returns |

Runs locally (PySpark) on a sample, and on AWS (S3 + EMR Serverless, Terraform) for the full history.
Target cost: under $10/month.

## Development

Needs Python 3.11+ and Java 17+ (Spark runs on the JVM).

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest          # tests run in UTC, whatever your machine's time zone
ruff check .    # lint
```

## Download raw data

```bash
python -m crypto_events.download BTCUSDT --day 2026-10-29     # one daily file
python -m crypto_events.download BTCUSDT --month 2020-01      # one monthly file (for backfills)
```

Files go to `data/raw/klines/interval=1m/symbol=<SYMBOL>/`, unchanged, and are checked against
Binance's SHA-256 checksum. Files already downloaded and verified are skipped. `data/` is never committed.

## Events

[`seeds/events.csv`](seeds/events.csv): the macro events studied, one row each, with an official source link.

| Type | Time | Covered |
| --- | --- | --- |
| US CPI release (BLS) | 8:30 a.m. New York | 2024–2025 (23 releases; October 2025 was cancelled) |
| FOMC decision (Federal Reserve) | 2:00 p.m. New York | 2024–2025 (16 meetings) |

Each row keeps the local time and its time zone, plus the same moment in UTC; `crypto_events.events.load_events()`
checks that they match, so daylight-saving mistakes fail the tests.

## Symbols

[`seeds/symbols.csv`](seeds/symbols.csv): the 20 coins studied. Rebuild it with:

```bash
python -m crypto_events.symbols --last-month 2026-09
```

How they're picked: from a list of long-listed USDT pairs, drop stablecoins, keep pairs with data in 2020-01 **and**
in the last month (still trading), then rank by total USDT traded in 2025 (from Binance daily candles) and keep the top 20.

Known limits: the candidate list is hand-made (a coin missing from it can't be picked), and keeping only coins that
still trade today adds **survivorship bias** (coins that failed after 2020 are left out).

## License

MIT
