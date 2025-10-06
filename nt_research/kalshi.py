import os
from dotenv import load_dotenv
import datetime as dt
import requests
import polars as pl

load_dotenv(override=True)

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2/"


class KalshiClient:
    def __init__(self, api_key_id: str, private_key_pem: str) -> None:
        self.api_key_id = api_key_id
        self.private_key_pem = private_key_pem

    def get_markets(
        self,
        event_ticker: str | None = None,
        series_ticker: str | None = None,
        max_close_ts: dt.datetime | None = None,
        min_close_ts: dt.datetime | None = None,
        status: str | None = None,  # settled = closed, open = active
        tickers: list[str] | None = None,
    ) -> pl.DataFrame:
        endpoint = "markets/"

        params = {"limit": 1000}

        if event_ticker is not None:
            params["event_ticker"] = event_ticker
        if series_ticker is not None:
            params["series_ticker"] = series_ticker
        if max_close_ts is not None:
            params["max_close_ts"] = int(max_close_ts.timestamp())
        if min_close_ts is not None:
            params["min_close_ts"] = int(min_close_ts.timestamp())
        if status is not None:
            params["status"] = status
        if tickers is not None:
            params["tickers"] = tickers

        url = BASE_URL + endpoint

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
        except requests.RequestException as e:
            raise Exception(f"Failed to fetch markets: {e}")

        columns = [
            "ticker",
            "event_ticker",
            "title",
            "expected_expiration_time",
            "status",
            "yes_bid",
            "yes_ask",
            "no_bid",
            "no_ask",
            "volume",
            "result",
        ]

        df = pl.DataFrame(response.json()["markets"]).select(
            *columns, pl.lit(series_ticker).alias("series_ticker")
        )

        return df

    def get_market_candlesticks(
        self,
        series_ticker: str,
        ticker: str,
        start_ts: dt.datetime,
        end_ts: dt.datetime,
        period_interval: int,  # 1 = minutes
    ) -> pl.DataFrame:
        endpoint = f"series/{series_ticker}/markets/{ticker}/candlesticks"

        params = {
            "start_ts": int(start_ts.timestamp()),
            "end_ts": int(end_ts.timestamp()),
            "period_interval": period_interval,
        }

        url = BASE_URL + endpoint

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
        except requests.RequestException as e:
            raise Exception(f"Failed to fetch candlesticks: {e}")

        candlesticks = [
            {
                "end_period_ts": candlestick["end_period_ts"],
                "yes_bid_open": candlestick["yes_bid"]["open"],
                "yes_bid_low": candlestick["yes_bid"]["low"],
                "yes_bid_high": candlestick["yes_bid"]["high"],
                "yes_bid_close": candlestick["yes_bid"]["open"],
                "yes_ask_open": candlestick["yes_ask"]["open"],
                "yes_ask_low": candlestick["yes_ask"]["low"],
                "yes_ask_high": candlestick["yes_ask"]["high"],
                "yes_ask_close": candlestick["yes_ask"]["open"],
                "volume": candlestick["volume"],
                "open_interest": candlestick["open_interest"],
            }
            for candlestick in response.json()["candlesticks"]
        ]

        df = pl.DataFrame(candlesticks).with_columns(
            pl.lit(series_ticker).alias("series_ticker"), pl.lit(ticker).alias("ticker")
        )

        return df


def _create_kalshi_client():
    kalshi_api_key = os.getenv("KALSHI_API_KEY")
    private_key_path = os.getenv("KALSHI_PRIVATE_KEY_PATH", "kalshi-api-key.txt")

    if not kalshi_api_key:
        raise ValueError("KALSHI_API_KEY environment variable is required")

    try:
        with open(private_key_path, "r") as f:
            private_key = f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Private key file not found at: {private_key_path}")

    return KalshiClient(kalshi_api_key, private_key)


kalshi_client = _create_kalshi_client()
