import polars as pl
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np

def generate_performance(df: pl.DataFrame, min_elapsed_time: int, price_interval: list[int]) -> pl.DataFrame:
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
        .filter(
            pl.col('trade_price').is_between(*price_interval)
        )
        .with_columns(
            pl.when(pl.col('result').eq(1))
            .then(
                pl.lit(100).sub('trade_price')
            )
            .otherwise(
                pl.col('trade_price').mul(-1)
            )
            .alias('pnl')
        )
        .with_columns(
            pl.col('pnl').truediv('trade_price').alias('return')
        )
        .select(
            pl.col('return').mean().alias('return_mean'),
            pl.col('return').std().alias('return_std')
        )
        .with_columns(
            pl.col('return_mean').truediv('return_std').alias('return_sharpe')
        )
    )

    return df_clean

if __name__ == '__main__':

    df = pl.read_parquet("data/2025-09-21_history.parquet")

    min_elapsed_time_list = np.linspace(30, 180, 6)
    price_interval_list = [[i * 10, (i + 1) * 10] for i in range(10)]
    print(price_interval_list)

    results_list = []

    for min_elapsed_time in min_elapsed_time_list:
        for price_interval in price_interval_list:
            results_list.append(
                generate_performance(
                    df=df, 
                    min_elapsed_time=min_elapsed_time, 
                    price_interval=price_interval
                )
                .with_columns(
                    pl.lit(min_elapsed_time).alias('min_elapsed_time'),
                    pl.lit(str(price_interval)).alias('price_interval')
                )
            )
    
    results: pl.DataFrame = pl.concat(results_list)

    results_tails = (
        results
        .filter(
            pl.col('price_interval').is_in([
                '[0, 10]',
                '[90, 100]'
            ])
        )
    )

    print(results_tails)

    plt.figure(figsize=(10, 6))

    plt.axhline(y=0, color='red')

    sns.lineplot(results_tails, x='min_elapsed_time', y='return_sharpe', hue='price_interval')

    plt.title("Strategy Samples")
    plt.legend(title="Price Interval")
    plt.xlabel("Elapsed Time")
    plt.ylabel("Daily Sharpe Ratio")

    plt.savefig('nt_research/research/merger_arbitrage/results/performance.png', dpi=300)

    plt.show()
