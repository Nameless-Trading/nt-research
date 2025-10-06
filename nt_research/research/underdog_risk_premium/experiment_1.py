import polars as pl
import seaborn as sns
import matplotlib.pyplot as plt
import os
from great_tables import GT
import numpy as np
import nt_research.research.underdog_risk_premium.data_utils as du


def get_results(trades: pl.DataFrame) -> pl.DataFrame:
    return (
        trades
        # Get price bin level results
        .group_by("price_bin")
        .agg(
            pl.col("elapsed_time").mean().alias("trade_time_mean"),
            pl.col("yes_ask_close").mean().alias("price_mean"),
            pl.col("result").mean().alias("result_mean"),
            pl.col("result").std().alias("result_stdev"),
            pl.len().alias("count"),
        )
        .with_columns(pl.col("result_mean", "result_stdev").mul(100))
        .with_columns(pl.col("result_mean").sub("price_mean").alias("delta"))
        .with_columns(
            (
                pl.col("result_mean").sub("price_mean")
                / (pl.col("result_stdev") / pl.col("count").sqrt())
            ).alias("tstat")
        )
        .sort("price_mean")
    )


def create_calibration_table(
    results: pl.DataFrame,
    title: str | None = None,
    file_name: str | None = None,
) -> pl.DataFrame:
    if file_name is not None:
        gt = (
            GT(results)
            .tab_header(title=title)
            .fmt_number(
                columns=[
                    "trade_time_mean",
                    "price_mean",
                    "result_mean",
                    "result_stdev",
                    "delta",
                    "tstat",
                ],
                decimals=2,
            )
            .cols_label(
                price_bin="Price Group",
                trade_time_mean="Trade Time Mean",
                price_mean="Price Mean",
                result_mean="Result Mean",
                result_stdev="Result St. Dev.",
                count="Count",
                delta="Delta",
                tstat="T-stat",
            )
            .opt_stylize(style=5, color="gray")
        )
        gt.save(file_name)
    else:
        print(results)


def create_calibration_chart(
    results: pl.DataFrame, title: str, file_name: str | None = None
) -> None:
    plt.figure(figsize=(10, 6))

    # Result bars
    sns.barplot(results, x="price_bin", y="result_mean", color="dimgray")

    # Perfect calibration reference line
    x_vals = [(x * 10 + 5) for x in range(10)]

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
    min_elapsed_time = -180
    max_elapsed_time = 180
    time_interval = 60

    trade_time = -60
    time_bin = f"({trade_time}, {trade_time + time_interval}]"

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
    )

    # Get aggregate trades
    results = get_results(trades)

    # Save results
    calibration_table = create_calibration_table(
        results,
        title=f"Contract Calibration (t={trade_time})",
        file_name=f"{folder}/calibration_table_t={trade_time}.png",
    )

    create_calibration_chart(
        results,
        title=f"Contract Calibration (t={trade_time})",
        file_name=f"{folder}/calibration_chart_t={trade_time}.png",
    )
