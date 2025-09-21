import polars as pl

df = pl.read_parquet('data/2025-09-21_candlesticks.parquet')

print(df)