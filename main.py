import yfinance as yf
import pandas as pd

Ticker="QLD"
Start="2005-01-01"


def calculate_cagr(series):
    start_val = series.iloc[0]
    end_val = series.iloc[-1]
    years = (series.index[-1] - series.index[0]).days / 365.25
    if years == 0: return 0
    cagr = (end_val / start_val) ** (1 / years) - 1
    return cagr


def calculate_mdd(series):
    cumulative_max = series.cummax()
    drawdown = (series - cumulative_max) / cumulative_max
    mdd = drawdown.min()
    return mdd


def get_sma_state(row):
    if pd.isna(row['SMA5']) or pd.isna(row['SMA20']) or pd.isna(row['SMA200']):
        return

