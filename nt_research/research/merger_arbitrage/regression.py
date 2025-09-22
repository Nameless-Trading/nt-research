import polars as pl
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
import statsmodels.formula.api as smf

def generate_trades(df: pl.DataFrame, min_elapsed_time: int) -> pl.DataFrame:
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
            pl.when(pl.col('result').eq(1))
            .then(
                pl.lit(100).sub('trade_price')
            )
            .otherwise(
                pl.col('trade_price').mul(-1)
            )
            .alias('pnl')
        )
        .group_by('trade_price')
        .agg(
            pl.col('pnl').mean().alias('pnl_mean')
        )
        .sort('trade_price')
    )

    return df_clean

if __name__ == '__main__':

    df = pl.read_parquet("data/2025-09-21_history.parquet")

    min_elapsed_time = 30
    price_interval = [90, 100]

    results = (
        generate_trades(
            df=df, 
            min_elapsed_time=min_elapsed_time, 
        )
        .filter(
            pl.col('trade_price').is_between(*price_interval)
        )
        .with_columns(
            pl.lit(min_elapsed_time).alias('min_elapsed_time'),
            pl.lit(price_interval).alias('price_interval'),
        )
    )
    
    print(results)

    formula = "pnl_mean ~ trade_price"

    model = smf.ols(formula, results).fit()
    print(model.summary())

    B_0 = model.params['Intercept']
    B_1 = model.params['trade_price']

    x = results['trade_price'].to_numpy()
    y = B_0 + B_1 * x

    sns.scatterplot(results, x='trade_price', y='pnl_mean')
    plt.plot(x, y, color='red')

    plt.show()
