import polars as pl
import datetime as dt
import seaborn as sns
import matplotlib.pyplot as plt
import os
from great_tables import GT


def get_trades(trade_time: int):
    df = pl.read_parquet("data/2025-10-05_history.parquet")
    print(df.select('ticker').unique())

    breaks = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 99]

    return (
        df.select(
            "end_period_ts",
            "ticker",
            "yes_ask_close",
            "game_start_time_utc",
            "result",
        )
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
            pl.col("yes_ask_close").first(),
            pl.col("result").mean(),
        )
        .filter(
            pl.col('yes_ask_close').is_between(1, 99)
        )
        .with_columns(pl.col("yes_ask_close").cut(breaks).cast(pl.String).alias("bin"))
        .sort("ticker")
    )


def get_aggregate_trades(trades: pl.DataFrame) -> pl.DataFrame:
    return (
        trades.group_by("bin")
        .agg(
            pl.col("elapsed_time").mean().alias("trade_time_mean"),
            pl.col("yes_ask_close").mean().alias("price_mean"),
            pl.col("result").mean().alias("result_mean"),
            pl.col("result").std().alias("result_stdev"),
            pl.len().alias("count"),
        )
        .sort("price_mean")
    )


def create_calibration_table(aggregate_trades: pl.DataFrame, title: str | None = None, file_name: str | None = None) -> pl.DataFrame:
    table = (
        aggregate_trades.with_columns(pl.col("result_mean", "result_stdev").mul(100))
        .with_columns(pl.col("result_mean").sub("price_mean").alias("delta"))
        .with_columns(
            (
                pl.col("result_mean").sub("price_mean")
                / (pl.col("result_stdev") / pl.col("count").sqrt())
            ).alias("tstat")
        )
    )

    if file_name is not None:
        gt = (
            GT(table)
            .tab_header(title=title)
            .fmt_number(columns=["trade_time_mean", "price_mean", "result_mean", "result_stdev", "delta", "tstat"], decimals=2)
            .cols_label(
                bin="Price Group",
                trade_time_mean="Trade Time Mean",
                price_mean="Price Mean",
                result_mean="Result Mean",
                result_stdev="Result St. Dev.",
                count="Count",
                delta="Delta",
                tstat="T-stat"
            )
            .opt_stylize(style=5, color='gray')
        )
        gt.save(file_name)
    else:
        print(table)


def create_calibration_chart(
    aggregate_trades: pl.DataFrame, title: str, file_name: str | None = None
) -> None:
    plt.figure(figsize=(10, 6))

    # Result bars
    sns.barplot(aggregate_trades, x="bin", y="result_mean", color="dimgray")

    # Perfect calibration reference line
    x_vals = [(x * 10 + 5) / 100 for x in range(10)]

    plt.plot(
        range(len(x_vals)),
        x_vals,
        color="red",
        linewidth=2,
        label="Perfect Calibration",
        linestyle="--",
        marker="o",
        markersize=4,
    )

    # Format
    plt.title(title)
    plt.ylabel("Percentage Won")
    plt.xlabel("Price Group")
    plt.legend(loc="upper left")
    plt.tight_layout()

    # Save/display
    if file_name is not None:
        plt.savefig(file_name, dpi=300)
    else:
        plt.show()


if __name__ == "__main__":
    # Parameters
    trade_time = -30

    # Save directory
    experiment_folder = os.path.splitext(os.path.basename(__file__))[0]
    folder = f"nt_research/research/underdog_risk_premium/results/{experiment_folder}"
    os.makedirs(folder, exist_ok=True)

    # Get trades
    trades = get_trades(trade_time=trade_time)

    # Get aggregate trades
    aggregate_trades = get_aggregate_trades(trades)

    # Save results
    calibration_table = create_calibration_table(
        aggregate_trades, 
        title=f"Contract Calibration (t={trade_time})",
        file_name=f"{folder}/calibration_table_t={trade_time}.png"
    )

    create_calibration_chart(
        aggregate_trades,
        title=f"Contract Calibration (t={trade_time})",
        file_name=f"{folder}/calibration_chart_t={trade_time}.png",
    )
