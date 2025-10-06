import polars as pl
from nt_research.kalshi import kalshi_client
from tqdm import tqdm
import datetime as dt


def get_settled_markets_dataset():
    today = dt.date.today()
    series_ticker = "KXNCAAFGAME"

    markets = kalshi_client.get_markets(
        series_ticker=series_ticker, status="settled"
    ).select(
        pl.col("series_ticker"),
        pl.col("ticker"),
        pl.col("expected_expiration_time")
        .str.strptime(pl.Datetime, "%Y-%m-%dT%H:%M:%SZ")
        .dt.replace_time_zone("UTC")
        .dt.offset_by("-3h")
        .alias("game_start_time_utc"),
        pl.col("result"),
    )

    print(markets)

    candlesticks_list = []
    for market in tqdm(markets.to_dicts(), "Downloading historical data."):
        start_ts = market["game_start_time_utc"] - dt.timedelta(hours=12)
        end_ts = market["game_start_time_utc"] + dt.timedelta(hours=12)

        candlesticks_ = kalshi_client.get_market_candlesticks(
            series_ticker=market["series_ticker"],
            ticker=market["ticker"],
            start_ts=start_ts,
            end_ts=end_ts,
            period_interval=1,
        )

        candlesticks_list.append(candlesticks_)

    candlesticks: pl.DataFrame = pl.concat(candlesticks_list)

    markets.write_parquet(f"data/{today}_markets.parquet")
    candlesticks.write_parquet(f"data/{today}_candlesticks.parquet")

    df_candle_sticks = candlesticks.with_columns(
        pl.from_epoch("end_period_ts").dt.convert_time_zone("UTC")
    )

    df_markets = markets.select("ticker", "game_start_time_utc", "result")

    df_history = df_candle_sticks.join(df_markets, on="ticker", how="left").sort(
        "ticker", "end_period_ts"
    )

    print(df_history)

    df_history.write_parquet(f"data/{today}_history.parquet")


if __name__ == "__main__":
    get_settled_markets_dataset()
