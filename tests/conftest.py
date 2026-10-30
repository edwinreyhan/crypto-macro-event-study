import os
import time

import pytest
from pyspark.sql import SparkSession

# All timestamps in this project are UTC. PySpark converts timestamps to the *Python process's*
# local time zone when collecting rows, so pin the process to UTC before Spark starts.
# Without this, 19:00 UTC comes back as 02:00 the next day on a laptop in Jakarta.
os.environ["TZ"] = "UTC"
if hasattr(time, "tzset"):  # not available on Windows
    time.tzset()


@pytest.fixture(scope="session")
def spark():
    """One small local SparkSession shared by all tests (starting Spark takes seconds)."""
    session = (
        SparkSession.builder.master("local[2]")
        .appName("crypto-events-tests")
        # Few partitions: test data is tiny, the default 200 only adds overhead.
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.driver.extraJavaOptions", "-Duser.timezone=UTC")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )
    yield session
    session.stop()
