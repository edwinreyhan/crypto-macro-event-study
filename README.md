# crypto-macro-event-study

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

## License

MIT
