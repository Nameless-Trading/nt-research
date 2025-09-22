import polars as pl
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np

def generate_calibration(df: pl.DataFrame, n_bins: int, min_elapsed_time: int) -> pl.DataFrame:
    breaks = np.linspace(0, 100, n_bins + 1)
    labels = [str(i * (100 / n_bins)) for i in range(n_bins + 2)]

    df_clean = (
        df
        .select(
            "end_period_ts",
            "ticker",
            pl.col('end_period_ts').sub(pl.col('game_start_time_utc')).dt.total_minutes().alias('elapsed_time'),
            "yes_ask_close",
            pl.col('result').replace({'no': '0', 'yes': '1'}).cast(pl.Float64)
        )
        .filter(
            pl.col('elapsed_time').ge(min_elapsed_time),
        )
        .sort('ticker', 'end_period_ts')
        .group_by('ticker')
        .agg(
            pl.col('elapsed_time').first().alias('trade_time'),
            pl.col('yes_ask_close').first().alias('trade_price'),
            pl.col('result').mean(),
        )
        .with_columns(
            pl.col('trade_price').cut(breaks=breaks, labels=labels).cast(pl.String()).cast(pl.Float64).cast(pl.Int32).alias('bin')
        )
        .group_by('bin')
        .agg(
            pl.len().alias('count'),
            pl.col('trade_price').mean(),
            pl.col('result').mul(100).mean()
        )
        .sort('bin')
    )

    return df_clean

if __name__ == '__main__':

    df = pl.read_parquet("data/2025-09-21_history.parquet")

    min_elapsed_time_list = np.linspace(30, 180, 6)
    price_interval = [90, 100]
    # min_elapsed_time_list = list(range(1, 181, 30))

    calibration_list = []
    for min_elapsed_time in min_elapsed_time_list:
        calibration_list.append(
            generate_calibration(
                df=df, 
                n_bins=100, 
                min_elapsed_time=min_elapsed_time
            )
            .with_columns(
                pl.lit(min_elapsed_time).alias('min_elapsed_time')
            )
        )

    results: pl.DataFrame = pl.concat(calibration_list)

    results_tails = (
        results
        .filter(
            pl.col('bin').is_between(*price_interval)
        )
        .group_by('min_elapsed_time')
        .agg(
            pl.col('trade_price').mul('count').sum().truediv(pl.col('count').sum()),
            pl.col('result').mul('count').sum().truediv(pl.col('count').sum()),
            pl.col('count').sum()
        )
        .sort('min_elapsed_time', 'trade_price')
    )

    print(results_tails)

    plt.figure(figsize=(10, 6))

    plt.title(f"Contracts in {price_interval}")
    plt.xlabel('Elapsed Time')
    plt.ylabel('Mean Result/Price')

    sns.lineplot(results_tails, x='min_elapsed_time', y='trade_price', label='Mean Price')
    sns.lineplot(results_tails, x='min_elapsed_time', y='result', label='Mean Result')

    plt.savefig("nt_research/research/merger_arbitrage/results/calibration.png", dpi=300)

    plt.show()