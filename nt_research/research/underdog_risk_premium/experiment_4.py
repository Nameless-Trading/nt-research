import polars as pl
import seaborn as sns
import matplotlib.pyplot as plt
import os


def get_strategy_returns(df: pl.DataFrame, price_min: int, price_max: int) -> pl.DataFrame:
    return (
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
            pl.col('price').is_between(price_min, price_max)
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
            pl.col('cumulative_return').sub(pl.col('max')).alias('drawdown')
        )
        .with_columns(
            pl.col('drawdown').mul(100).alias('max_drawdown'),
            pl.col('cumulative_return').mul(100)
        )
    )


def create_cumulative_return_chart(
    results: pl.DataFrame,
    title: str,
    file_name: str | None = None
) -> None:
    plt.figure(figsize=(12, 7))

    sns.lineplot(
        results,
        x='date',
        y='cumulative_return',
        color='black'
    )

    # Add grid
    plt.grid(True)

    # Add zero line
    plt.axhline(y=0, color='gray', linestyle='-')

    # Format
    plt.xlabel(None)
    plt.ylabel('Cumulative Return (%)')
    plt.title(title)

    plt.tight_layout()

    if file_name is not None:
        plt.savefig(file_name, dpi=300, bbox_inches='tight')
    else:
        plt.show()


def create_drawdown_chart(
    results: pl.DataFrame,
    title: str,
    file_name: str | None = None
) -> None:
    plt.figure(figsize=(12, 7))

    ax = sns.lineplot(
        results,
        x='date',
        y='max_drawdown',
        color='red'
    )

    ax.fill_between(
        results['date'],
        results['max_drawdown'],
        0,
        alpha=0.3,
        color='red'
    )

    # Add grid
    plt.grid(True)

    # Add zero line
    # plt.axhline(y=0, color='gray', linestyle='-')

    # Format
    plt.xlabel(None)
    plt.ylabel('Drawdown (%)')
    plt.title(title)

    plt.tight_layout()

    if file_name is not None:
        plt.savefig(file_name, dpi=300, bbox_inches='tight')
    else:
        plt.show()


def calculate_performance_metrics(results: pl.DataFrame) -> dict:
    returns = results['return'].to_numpy()

    # Annualized Sharpe ratio (assuming 16 trading weeks)
    sharpe = (returns.mean() * 16**0.5) / returns.std()

    max_drawdown = results['drawdown'].min()  # Most negative value
    # Annualized return for Calmar ratio
    calmar = (returns.mean() * 16) / abs(max_drawdown)

    return {
        'sharpe': sharpe,
        'calmar': calmar,
        'max_drawdown': max_drawdown
    }


if __name__ == "__main__":
    # Parameters
    price_min = 90
    price_max = 99

    # Save directory
    experiment_folder = os.path.splitext(os.path.basename(__file__))[0]
    folder = f"nt_research/research/underdog_risk_premium/results/{experiment_folder}"
    os.makedirs(folder, exist_ok=True)

    # Load data
    df = pl.read_parquet('data/2025-10-08_history_daily.parquet')

    # Get strategy returns
    results = get_strategy_returns(df, price_min, price_max)

    print(results)

    # Create charts
    create_cumulative_return_chart(
        results,
        title=f"Cumulative Return (Price: {price_min}-{price_max})",
        file_name=f"{folder}/cumulative_return.png"
    )

    create_drawdown_chart(
        results,
        title=f"Drawdown (Price: {price_min}-{price_max})",
        file_name=f"{folder}/drawdown.png"
    )

    # Calculate and print performance metrics
    metrics = calculate_performance_metrics(results)
    print(f"Sharpe: {metrics['sharpe']:.4f}")
    print(f"Calmar: {metrics['calmar']:.4f}")
    print(f"Max Drawdown: {metrics['max_drawdown']:.4f}")
