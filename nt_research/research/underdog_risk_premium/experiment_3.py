import polars as pl
import os
from great_tables import GT
import nt_research.research.underdog_risk_premium.data_utils as du


def get_profits(trades: pl.DataFrame) -> pl.DataFrame:
    return (
        trades
        .with_columns(
            pl.when(pl.col("result").eq(1))
            .then(pl.lit(100).sub("yes_ask_close"))
            .otherwise(pl.col("yes_ask_close").mul(-1))
            .alias("profit")
        )
        .with_columns(
            pl.col("profit").truediv("yes_ask_close").alias("return"),
            pl.col("result")
            .cast(pl.String)
            .replace({"1": "Won", "0": "Lost"})
            .alias("trades_type"),
        )
    )


def get_lost_trades(trades: pl.DataFrame) -> pl.DataFrame:
    return trades.filter(pl.col("result").eq(0)).sort(
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
            pl.col("yes_ask_close").sum().alias("price"),
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
    min_elapsed_time = -180
    max_elapsed_time = 180
    time_interval = 60

    trade_time = -60
    time_bin = f"({trade_time}, {trade_time + time_interval}]"
    price_bin = "(90, 99]"

    # Save directory
    experiment_folder = os.path.splitext(os.path.basename(__file__))[0]
    folder = f"nt_research/research/underdog_risk_premium/results/{experiment_folder}"
    os.makedirs(folder, exist_ok=True)

    # Get trades
    trades = du.get_trades(
        time_bin=time_bin,
        min_elapsed_time=min_elapsed_time,
        max_elapsed_time=max_elapsed_time,
        time_interval=time_interval,
        price_bin=price_bin
    )

    # Get profits
    profits = get_profits(trades)

    # Get results
    results = create_performance_table(
        profits, file_name=f"{folder}/performance_table_t={trade_time}.png"
    )

    # Lost trades
    lost_trades = get_lost_trades(trades)
    print(lost_trades)
