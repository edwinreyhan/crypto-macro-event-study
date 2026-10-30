"""Read Binance 1m kline (candle) CSVs with Spark.

The files have **no header** and 12 columns. ``open_time`` is in milliseconds (13 digits) up to
2024-12-31 and in microseconds (16 digits) from 2025-01-01, so both units are handled.
"""

from __future__ import annotations

from collections.abc import Sequence

from pyspark.sql import Column, DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, LongType, StructField, StructType

KLINE_SCHEMA = StructType(
    [
        StructField("open_time", LongType(), nullable=False),
        StructField("open", DoubleType(), nullable=False),
        StructField("high", DoubleType(), nullable=False),
        StructField("low", DoubleType(), nullable=False),
        StructField("close", DoubleType(), nullable=False),
        StructField("volume", DoubleType(), nullable=False),
        StructField("close_time", LongType(), nullable=False),
        StructField("quote_asset_volume", DoubleType(), nullable=False),
        StructField("number_of_trades", LongType(), nullable=False),
        StructField("taker_buy_base_asset_volume", DoubleType(), nullable=False),
        StructField("taker_buy_quote_asset_volume", DoubleType(), nullable=False),
        StructField("ignore", DoubleType(), nullable=True),
    ]
)

# Any epoch value at or above this is microseconds: 10**14 µs is 1973, 10**14 ms is year 5138.
MICROS_THRESHOLD = 10**14


def epoch_to_utc(col: Column) -> Column:
    """Binance epoch number (ms or µs) → Spark timestamp (UTC session time zone)."""
    return F.when(col >= MICROS_THRESHOLD, F.timestamp_micros(col)).otherwise(
        F.timestamp_millis(col)
    )


def read_klines(spark: SparkSession, paths: Sequence[str], symbol: str) -> DataFrame:
    """Read kline CSV/CSV.GZ files for one symbol. Bad rows raise an error (``FAILFAST``)."""
    raw = spark.read.csv(list(paths), schema=KLINE_SCHEMA, header=False, mode="FAILFAST")
    return raw.select(
        F.lit(symbol).alias("symbol"),
        epoch_to_utc(F.col("open_time")).alias("open_time_utc"),
        "open",
        "high",
        "low",
        "close",
        "volume",
        "quote_asset_volume",
        "number_of_trades",
    )
