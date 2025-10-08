import polars as pl
import seaborn as sns
import matplotlib.pyplot as plt

if __name__ == '__main__':
    df = pl.read_parquet('data/2025-10-08_history_daily.parquet')
    
    df = (
        df
        .with_columns(
            pl.col('end_period_ts').dt.convert_time_zone('America/Denver').dt.date().alias('date'),
            pl.col('game_start_time_utc').dt.convert_time_zone('America/Denver').dt.date().alias('game_day'),
            pl.col('result').replace({'yes': '1', 'no': '0'}).cast(pl.Int8)
        )
        .select(
            'date',
            'ticker',
            'game_day',
            'yes_ask_open',
            'yes_ask_high',
            'yes_ask_low',
            'yes_ask_close',
            pl.col('yes_ask_close').alias('price'),
            'result'
        )
        .filter(
            pl.col('date').eq(pl.col('game_day')),
            pl.col('price').is_between(90, 99)
        )
        .sort('ticker', 'date')
        .with_columns(
            pl.when(pl.col('result').eq(1))
            .then(pl.lit(100).sub(pl.col('price')))
            .otherwise(pl.col('price').mul(-1))
            .alias('profit')
        )
        .with_columns(
            pl.col('profit').truediv('price').alias('return')
        )
        .group_by('date')
        .agg(
            pl.col('return').mean()
        )
        .sort('date')
        .with_columns(
            pl.col('return').add(1).cum_prod().sub(1).alias('cumulative_return')
        )
        .with_columns(
            pl.col('cumulative_return').cum_max().alias('max')
        )
        .with_columns(
            pl.col('cumulative_return').truediv(pl.col('max')).sub(1).mul(-1).alias('drawdown')
        )
        .with_columns(
            pl.col('cumulative_return').mul(100)
        )
    )

    print(df)

    # plt.figure(figsize=(10, 6))

    # sns.lineplot(df, x='date', y='cumulative_return')

    # plt.xlabel(None)
    # plt.ylabel('Cumulative Return (%)')

    # plt.show()


    # plt.figure(figsize=(10, 6))

    # sns.lineplot(df, x='date', y='drawdown')

    # plt.xlabel(None)
    # plt.ylabel('Max Drawdown (%)')

    # plt.show()

    returns = df['return'].to_numpy()
    sharpe = returns.mean() / returns.std()

    max_drawdown = df['drawdown'].max()
    calmar = returns.mean() / max_drawdown

    print("Sharpe:", sharpe)
    print("Calmar:", calmar)

