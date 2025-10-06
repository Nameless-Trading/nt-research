import polars as pl
import os
from great_tables import GT


def get_trades(trade_time: int):
    df = pl.read_parquet("data/2025-10-05_history.parquet")

    breaks = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 99]

    return (
        df.with_columns(
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
            pl.col("yes_ask_close").first().alias("price"),
            pl.col("result").mean(),
        )
        .filter(pl.col("price").is_between(1, 99))
        .with_columns(pl.col("price").cut(breaks).cast(pl.String).alias("bin"))
        .sort("ticker")
    )


def get_profits(trades: pl.DataFrame, price_bin: str) -> pl.DataFrame:
    return (
        trades.filter(pl.col("bin").eq(price_bin))
        .with_columns(
            pl.when(pl.col("result").eq(1))
            .then(pl.lit(100).sub("price"))
            .otherwise(pl.col("price").mul(-1))
            .alias("profit")
        )
        .with_columns(
            pl.col("profit").truediv("price").alias("return"),
            pl.col("result")
            .cast(pl.String)
            .replace({"1.0": "Won", "0.0": "Lost"})
            .alias("trades_type"),
        )
    )


def get_lost_trades(trades: pl.DataFrame, price_bin: str) -> pl.DataFrame:
    return trades.filter(pl.col("result").eq(0), pl.col("bin").eq(price_bin)).sort(
        "ticker"
    )


def create_performance_table(
    profits: pl.DataFrame, title: str | None = None, file_name: str | None = None
) -> pl.DataFrame:
    totals = profits.with_columns(pl.lit("Total").alias("trades_type"))

    profits_merge: pl.DataFrame = pl.concat([profits, totals])

    table = (
        profits_merge.group_by("trades_type")
        .agg(
            pl.col("elapsed_time").mean(),
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
        gt = (
            GT(table)
            .tab_header(title=title)
            .fmt_number(
                columns=["elapsed_time", "count", "profit", "price", "sharpe"],
                decimals=2,
            )
            .fmt_percent(columns=["return_mean", "return_stdev"])
            .cols_label(
                trades_type="Trades",
                elapsed_time="Elapsed Time",
                count="Count",
                profit="Profit",
                price="Price",
                return_mean="Return Mean",
                return_stdev="Return Std. Dev.",
                sharpe="Sharpe",
            )
            .opt_stylize(style=5, color="gray")
        )
        gt.save(file_name)
    else:
        print(table)


if __name__ == "__main__":
    # Parameters
    trade_time = -60

    # Save directory
    experiment_folder = os.path.splitext(os.path.basename(__file__))[0]
    folder = f"nt_research/research/underdog_risk_premium/results/{experiment_folder}"
    os.makedirs(folder, exist_ok=True)

    # Get trades
    trades = get_trades(trade_time=trade_time)

    # Get profits
    profits = get_profits(trades, price_bin="(90, 99]")

    # Get results
    results = create_performance_table(
        profits, file_name=f"{folder}/performance_table_t={trade_time}.png"
    )

    # Lost trades
    lost_trades = get_lost_trades(trades, price_bin="(90, 99]")
    print(lost_trades)
