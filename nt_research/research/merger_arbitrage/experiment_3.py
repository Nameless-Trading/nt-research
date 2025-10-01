import polars as pl
import datetime as dt
import seaborn as sns
import matplotlib.pyplot as plt
import os


def get_trades(trade_time: int):
    df = pl.read_parquet("data/2025-09-30_history.parquet")

    breaks = [x * 10 for x in range(10)]

    return (
        df
        .with_columns(
            pl.col("end_period_ts")
            .sub(pl.col("game_start_time_utc"))
            .dt.total_minutes()
            .alias("elapsed_time"),
            pl.col("result").replace({"yes": "1", "no": "0"}).cast(pl.Int32),
        )
        .filter(
            pl.col("elapsed_time").ge(trade_time),  # after trade_time minutes
        )
        .sort("ticker", "end_period_ts")
        .group_by("ticker")
        .agg(
            pl.col("elapsed_time").first(),
            pl.mean_horizontal('yes_bid_close', 'yes_ask_close').first().alias('price'),
            pl.col("result").mean(),
        )
        .with_columns(pl.col("price").cut(breaks).cast(pl.String).alias("bin"))
        .sort("ticker")
    )


def get_profits(trades: pl.DataFrame) -> pl.DataFrame:
    return (
        trades.filter(pl.col("bin").eq("(90, inf]"))
        .with_columns(
            pl.when(pl.col("result").eq(1))
            .then(pl.lit(100).sub("price"))
            .otherwise(pl.col("price").mul(-1))
            .alias("profit")
        )
        .with_columns(
            pl.col("profit").truediv("price").mul(100).alias("return"),
            pl.col("result")
            .cast(pl.String)
            .replace({"1.0": "Won", "0.0": "Lost"})
            .alias("trades_type"),
        )
    )


def create_performance_table(
    profits: pl.DataFrame, file_name: str | None = None
) -> pl.DataFrame:
    totals = profits.with_columns(pl.lit("Total").alias("trades_type"))

    profits_merge: pl.DataFrame = pl.concat([profits, totals])

    table = (
        profits_merge.group_by("trades_type")
        .agg(
            pl.col('elapsed_time').mean(),
            pl.len().alias("count"),
            pl.col("profit").sum(),
            pl.col("price").sum().alias("price"),
            pl.col("return").mean().alias("return_mean"),
            pl.col("return").std().alias("return_stdev"),
        )
        .with_columns(pl.col("return_mean").truediv("return_stdev").alias("sharpe"))
        .sort(by=pl.col("trades_type").replace({"Won": "a", "Lost": "b", "Total": "c"}))
    )

    if file_name is not None:
        with open(file_name, "w") as f:
            f.write(str(table))
    else:
        print(table)


if __name__ == "__main__":
    # Parameters
    trade_time = -30

    # Save directory
    experiment_folder = os.path.splitext(os.path.basename(__file__))[0]
    folder = f"nt_research/research/merger_arbitrage/results/{experiment_folder}"
    os.makedirs(folder, exist_ok=True)

    # Get trades
    trades = get_trades(trade_time=trade_time)

    # Get profits
    profits = get_profits(trades)

    # Get results
    results = create_performance_table(
        profits, 
        # file_name=f"{folder}/performance_table_t={trade_time}.txt"
    )
