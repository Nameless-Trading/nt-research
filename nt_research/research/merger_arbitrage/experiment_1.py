import polars as pl
import datetime as dt
import seaborn as sns
import matplotlib.pyplot as plt
import os


def get_trades(trade_time: int):
    df = pl.read_parquet("data/2025-09-30_history.parquet")

    breaks = [x * 10 for x in range(10)]

    # Buy after game starts
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


def create_calibration_table(aggregate_trades: pl.DataFrame, file_name: str | None = None) -> pl.DataFrame:
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
        with open(file_name, "w") as f:
            f.write(str(table))

    return table


def create_calibration_chart(
    aggregate_trades: pl.DataFrame, title: str, file_name: str | None = None
) -> None:
    plt.figure(figsize=(10, 6))

    # Result bars
    sns.barplot(aggregate_trades, x="bin", y="result_mean")

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
    folder = f"nt_research/research/merger_arbitrage/results/{experiment_folder}"
    os.makedirs(folder, exist_ok=True)

    # Get trades
    trades = get_trades(trade_time=trade_time)

    # Get aggregate trades
    aggregate_trades = get_aggregate_trades(trades)

    # Save results
    calibration_table = create_calibration_table(
        aggregate_trades, file_name=f"{folder}/calibration_table_t={trade_time}.txt"
    )

    create_calibration_chart(
        aggregate_trades,
        title=f"Contract Calibration (t={trade_time})",
        file_name=f"{folder}/calibration_chart_t={trade_time}.png",
    )
