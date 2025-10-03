import polars as pl
import datetime as dt
import seaborn as sns
import matplotlib.pyplot as plt
import os
import numpy as np


def get_trades(min_elapsed_time: int, max_elapsed_time, time_interval: int):
    df = pl.read_parquet("data/2025-09-30_history.parquet")

    price_breaks = np.arange(0, 100, 10)
    time_breaks = np.arange(min_elapsed_time + time_interval, max_elapsed_time, time_interval)

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
        .sort("ticker", "end_period_ts")
        .filter(pl.col("elapsed_time").is_between(min_elapsed_time, max_elapsed_time))
        .with_columns(
            pl.col("yes_ask_close")
            .cut(price_breaks)
            .cast(pl.String)
            .alias("price_bin"),
            pl.col("elapsed_time").cut(time_breaks).cast(pl.String).alias("time_bin"),
        )
        .sort("ticker")
    )


def get_aggregate_trades(trades: pl.DataFrame) -> pl.DataFrame:
    return (
        trades.group_by("price_bin", "time_bin")
        .agg(
            pl.col("elapsed_time").mean().alias("trade_time_mean"),
            pl.col("yes_ask_close").mean().alias("price_mean"),
            pl.col("result").mean().mul(100).alias("result_mean"),
            pl.col("result").std().mul(100).alias("result_stdev"),
            pl.len().alias("count"),
        )
        .with_columns(
            (
                (pl.col("result_mean") - pl.col("price_mean"))
                / (pl.col("result_stdev") / pl.col("count").sqrt())
            )
            # .clip(lower_bound=-10, upper_bound=10)
            .alias("tstat")
        )
        .sort("trade_time_mean", "price_mean")
    )


def create_calibration_over_time_chart(
    aggregate_trades: pl.DataFrame,
    title: str,
    price_bin: str | None = None,
    file_name: str | None = None,
) -> None:
    if price_bin is not None:
        aggregate_trades = aggregate_trades.filter(
            pl.col("price_bin").eq("(90, inf]")
        ).sort("trade_time_mean")

    plt.figure(figsize=(10, 6))

    # Lines
    if price_bin is not None:
        aggregate_trades = (
            aggregate_trades
            .unpivot(index=['time_bin', 'price_bin'], on=['price_mean', 'result_mean', 'tstat']) 
            .sort(
                pl.col("time_bin").str.extract(r"\((-?\d+)", 1).cast(pl.Int64),
                'variable'
            )
        )

        tstat = (
            aggregate_trades
            .filter(
                pl.col('variable').eq('tstat')
            )
            .sort(
                pl.col("time_bin").str.extract(r"\((-?\d+)", 1).cast(pl.Int64),
            )            
            ['value'].to_list()
        )

        sns.barplot(
            aggregate_trades, x="time_bin", y="value", hue='variable', palette='gray'
        )

        match price_bin:
            case "(90, inf]":
                plt.ylim(90, 100)

            case _:
                raise ValueError(f"Unsupported price bin: {price_bin}")

    else:
        sns.lineplot(
            aggregate_trades,
            x="trade_time_mean",
            y="result_mean",
            hue="price_bin",
            palette="coolwarm",
        )

    # Format
    plt.title(title)
    plt.ylabel(None)
    plt.xlabel("Mean Elapsed Time")

    if price_bin is None:
        plt.legend(title="Price Bin", bbox_to_anchor=(1, 1), loc="upper left")
        plt.tight_layout()

    # Save/display
    if file_name is not None:
        plt.savefig(file_name, dpi=300)
    else:
        plt.show()

def create_count_over_time_chart(
    aggregate_trades: pl.DataFrame,
    title: str,
    price_bin: str,
    file_name: str | None = None,  
) -> None:
    totals = (
        aggregate_trades
        .group_by("time_bin")
        .agg(pl.col("count").sum(), pl.col("trade_time_mean").mean())
        .sort("trade_time_mean")
    )
        
    aggregate_trades = (
        aggregate_trades
        .filter(
            pl.col('price_bin').eq(price_bin)
        )
    )

    plt.figure(figsize=(10, 6))

    sns.lineplot(aggregate_trades, x='trade_time_mean', y='count', label=f'{price_bin} Count')
    sns.lineplot(totals, x='trade_time_mean', y='count', label='Total')

    plt.title(title)
    plt.ylabel("Count")
    plt.xlabel("Mean Elapsed Time")

    # Save/display
    if file_name is not None:
        plt.savefig(file_name, dpi=300)
    else:
        plt.show()

def create_tstat_chart(
    aggregate_trades: pl.DataFrame,
    title: str,
    price_bin: str | None = None,
    file_name: str | None = None,  
) -> None:
    if price_bin is not None:
        aggregate_trades = (
            aggregate_trades
            .filter(
                pl.col('price_bin').eq(price_bin)
            )
        )

    plt.figure(figsize=(10, 6))

    # Lines
    if price_bin is not None:
        sns.lineplot(
            aggregate_trades, x="trade_time_mean", y="tstat"
        )

    else:
        sns.lineplot(
            aggregate_trades,
            x="trade_time_mean",
            y="tstat",
            hue="price_bin",
            palette="coolwarm",
        )

    plt.title(title)
    plt.ylabel("T-Stat")
    plt.xlabel("Mean Elapsed Time")
    plt.figtext(0.5, 0.01, "T-stats are clipped on [-10, 10]", ha="center", fontsize=9, style="italic")

    if price_bin is None:
        plt.legend(title="Price Bin", bbox_to_anchor=(1, 1), loc="upper left")
        plt.tight_layout()

    # Save/display
    if file_name is not None:
        plt.savefig(file_name, dpi=300)
    else:
        plt.show()

if __name__ == "__main__":
    # Params
    min_elapsed_time = -180
    max_elapsed_time = 180
    time_interval = 60

    # Save directory
    experiment_folder = os.path.splitext(os.path.basename(__file__))[0]
    folder = f"nt_research/research/merger_arbitrage/results/{experiment_folder}"
    os.makedirs(folder, exist_ok=True)

    # Get trades
    trades = get_trades(
        min_elapsed_time=min_elapsed_time,
        max_elapsed_time=max_elapsed_time,
        time_interval=time_interval
    )

    # Get aggregate trades
    aggregate_trades = get_aggregate_trades(trades)

    # # Create all bins result
    # create_calibration_over_time_chart(
    #     aggregate_trades,
    #     title="Calibration Over Time Across Price Bins",
    #     file_name=f"{folder}/calibration-over-time-across-bins.png",
    # )

    print(aggregate_trades)

    # Create all bins result
    create_calibration_over_time_chart(
        aggregate_trades,
        price_bin="(90, inf]",
        title="(90, inf] Bin Calibration Over Time",
        # file_name=f"{folder}/calibration-over-time-top-bin.png",
    )

    # # Create counts chart
    # create_count_over_time_chart(
    #     aggregate_trades,
    #     price_bin="(90, inf]",
    #     title="(90, inf] Bin Count Over Time",
    #     file_name=f"{folder}/count-over-time-top-bin.png",
    # )

    # # Create tstat chart
    # create_tstat_chart(
    #     aggregate_trades,
    #     title="T-stat Count Over Time Across Price Bins",
    #     file_name=f"{folder}/tstat-over-time.png",
    # )

    # # Create tstat chart top bin
    # create_tstat_chart(
    #     aggregate_trades,
    #     price_bin="(90, inf]",
    #     title="(90, inf] T-stat Count Over Time",
    #     file_name=f"{folder}/tstat-over-time-top-bin.png",
    # )