from datetime import datetime


def test_spark_counts_rows(spark):
    df = spark.createDataFrame([("BTCUSDT", 1.0), ("ETHUSDT", 2.0)], ["symbol", "close"])
    assert df.count() == 2


def test_session_time_zone_is_utc(spark):
    assert spark.conf.get("spark.sql.session.timeZone") == "UTC"
    row = spark.sql("SELECT TIMESTAMP '2025-01-29 19:00:00' AS ts").first()
    assert row.ts == datetime(2025, 1, 29, 19, 0)
