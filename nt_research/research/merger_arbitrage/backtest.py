import polars as pl
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
import statsmodels.formula.api as smf


df = pl.read_parquet("data/2025-09-21_history.parquet")

min_elapsed_time = 60
price_interval = [90, 99]

trades = (
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
    .with_columns(
        pl.col('return').mul(100).alias('scaled_pnl')
    )
    .sort('ticker')
)

print(trades)

results = (
    trades
    .select(
        pl.len().alias('n_trades'),
        pl.col('scaled_pnl').sum().alias('total_pnl'),
        pl.col('return').mean().alias('return_mean'),
        pl.col('return').std().alias('return_std')
    )
    .with_columns(
        pl.col('return_mean').truediv('return_std').alias('sharpe')
    )
)

print(results)


