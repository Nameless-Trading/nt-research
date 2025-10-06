import polars as pl
import datetime as dt
import seaborn as sns
import matplotlib.pyplot as plt
import os
import numpy as np


def get_trades(min_elapsed_time: int, max_elapsed_time, time_interval: int):
    df = pl.read_parquet("data/2025-10-05_history.parquet")

    price_breaks = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 99]
    time_breaks = np.arange(min_elapsed_time, max_elapsed_time + time_interval, time_interval)

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
        .filter(pl.col("elapsed_time").is_between(min_elapsed_time, max_elapsed_time, closed='right'))
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
        .filter(
            pl.col('price_mean').is_between(1, 99)
        )
        .with_columns(
            (
                (pl.col("result_mean") - pl.col("price_mean"))
                / (pl.col("result_stdev") / pl.col("count").sqrt())
            )
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
            pl.col("price_bin").eq(price_bin)
        ).sort("trade_time_mean")

    _, ax = plt.subplots(figsize=(10, 6))

    # Lines
    if price_bin is not None:
        aggregate_trades_sorted = aggregate_trades.sort(
            pl.col("time_bin").str.extract(r"\((-?\d+)", 1).cast(pl.Int64)
        )

        tstat_values = aggregate_trades_sorted['tstat'].to_list()
        time_bins = aggregate_trades_sorted['time_bin'].to_list()

        aggregate_trades_unpivot = (
            aggregate_trades_sorted
            .unpivot(index=['time_bin', 'price_bin'], on=['price_mean', 'result_mean', 'tstat'])
            .filter(
                pl.col('variable').ne('tstat')
            )
            .sort(
                pl.col("time_bin").str.extract(r"\((-?\d+)", 1).cast(pl.Int64),
                'variable'
            )
        )

        sns.barplot(
            aggregate_trades_unpivot, x="time_bin", y="value", hue='variable', palette='gray', ax=ax
        )

        # Add bar values
        for container in ax.containers:
            ax.bar_label(container, fmt='%.2f')

        labels = [f"{tb}\n($\\bf{{{ts:.2f}}}$)" for tb, ts in zip(time_bins, tstat_values)]
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels)

        # Get handles and labels from the plot
        handles, _ = ax.get_legend_handles_labels()
        ax.legend(handles, ['Price Mean', 'Result Mean'])

        match price_bin:
            case "(90, 99]":
                ax.set_ylim(90, 100)

            case _:
                raise ValueError(f"Unsupported price bin: {price_bin}")

    else:
        sns.lineplot(
            aggregate_trades,
            x="trade_time_mean",
            y="result_mean",
            hue="price_bin",
            palette="coolwarm",
            ax=ax
        )

    # Format
    ax.set_title(title)
    ax.set_ylabel(None)
    ax.set_xlabel("Time Bin\n($\\bf{T\\text{-}stat}$)" if price_bin is not None else "Mean Elapsed Time")

    if price_bin is None:
        ax.legend(title="Price Bin", bbox_to_anchor=(1, 1), loc="upper left")

    plt.tight_layout()

    # Save/display
    if file_name is not None:
        plt.savefig(file_name, dpi=300, bbox_inches='tight')
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

def create_count_heatmap(trades: pl.DataFrame, file_name: str | None = None) -> None:
    counts = (
        trades
        .filter(
            pl.col('yes_ask_close').ne(100)
        )
        .group_by('price_bin', 'time_bin')
        .agg(pl.col('ticker').n_unique().alias('count'))
        .sort('price_bin', descending=True)
        .pivot(index='price_bin', on='time_bin', values='count')
        .select(
            'price_bin', '(-180, -120]', '(-120, -60]', '(-60, 0]', '(0, 60]', '(60, 120]', '(120, 180]'
        )
    )

    counts_data = counts.drop('price_bin')

    plt.figure(figsize=(10, 8))
    sns.heatmap(
        counts_data,
        annot=True,
        fmt='g',
        cmap='YlOrRd',
        xticklabels=counts_data.columns,
        yticklabels=counts['price_bin'].to_list(),
        cbar_kws={'label': 'Count'}
    )
    plt.xlabel('Time Bin')
    plt.ylabel('Price Bin')
    plt.title('Trade Count Heatmap')
    plt.tight_layout()

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
    folder = f"nt_research/research/underdog_risk_premium/results/{experiment_folder}"
    os.makedirs(folder, exist_ok=True)

    # Get trades
    trades = get_trades(
        min_elapsed_time=min_elapsed_time,
        max_elapsed_time=max_elapsed_time,
        time_interval=time_interval
    )

    # Get aggregate trades
    aggregate_trades = get_aggregate_trades(trades)

    # Create all bins result
    create_calibration_over_time_chart(
        aggregate_trades,
        title="Calibration Over Time Across Price Bins",
        file_name=f"{folder}/calibration-over-time-across-bins.png",
    )

    # Create all bins result
    create_calibration_over_time_chart(
        aggregate_trades,
        price_bin="(90, 99]",
        title="(90, 99] Bin Calibration Over Time",
        file_name=f"{folder}/calibration-over-time-top-bin.png",
    )

    # Create counts chart
    create_count_over_time_chart(
        aggregate_trades,
        price_bin="(90, 99]",
        title="(90, 99] Bin Count Over Time",
        file_name=f"{folder}/count-over-time-top-bin.png",
    )

    # Create tstat chart
    create_tstat_chart(
        aggregate_trades,
        title="T-stat Count Over Time Across Price Bins",
        file_name=f"{folder}/tstat-over-time.png",
    )

    # Create tstat chart top bin
    create_tstat_chart(
        aggregate_trades,
        price_bin="(90, 99]",
        title="(90, 99] T-stat Count Over Time",
        file_name=f"{folder}/tstat-over-time-top-bin.png",
    )

    # Create counts heatmap
    create_count_heatmap(
        trades,
        file_name=f"{folder}/counts-heatmap.png"
    )