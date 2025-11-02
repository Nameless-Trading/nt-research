import polars as pl
import numpy as np

def get_trades(
    min_elapsed_time: int,
    max_elapsed_time: int,
    time_interval: int,
    time_bin: str | None = None,
    price_bin: str | None = None,
):
    df = pl.read_parquet("data/2025-11-02_history.parquet")

    price_breaks = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 99]
    time_breaks = np.arange(
        min_elapsed_time, max_elapsed_time + time_interval, time_interval
    )

    df = (
        df.select(
            "end_period_ts",
            "ticker",
            "yes_ask_close",
            "game_start_time_utc",
            "result",
        )
        # Compute elapsed time and result
        .with_columns(
            pl.col("end_period_ts")
            .sub(pl.col("game_start_time_utc"))
            .dt.total_minutes()
            .alias("elapsed_time"),
            pl.col("result").replace({"yes": "1", "no": "0"}).cast(pl.Int32),
        )
        # Filter to elasped_time window
        .filter(
            pl.col("elapsed_time").is_between(
                min_elapsed_time, max_elapsed_time, closed="right"
            )
        )
        # Get price bin and time bin
        .with_columns(
            pl.col("yes_ask_close")
            .cut(price_breaks)
            .cast(pl.String)
            .alias("price_bin"),
            pl.col("elapsed_time").cut(time_breaks).cast(pl.String).alias("time_bin"),
        )
        # Get ticker values for each bin
        .sort("ticker", "end_period_ts")
        .group_by("ticker", "price_bin", "time_bin")
        .agg(
            pl.col("elapsed_time").first(),
            pl.col("yes_ask_close").first(),
            pl.col("result").first(),
        )
        # Remove trades where price is 0 or 100
        .filter(pl.col("yes_ask_close").is_between(1, 99))
        .sort("ticker")
    )

    if time_bin is not None:
        df = df.filter(pl.col("time_bin").eq(time_bin))

    if price_bin is not None:
        df = df.filter(pl.col("price_bin").eq(price_bin))

    return df.sort("ticker", "time_bin", "price_bin")