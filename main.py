import sys
import io
import yfinance as yf
import pandas as pd
from datetime import date

Ticker="QLD"
Start="2005-01-01"
End = date.today().strftime("%Y-%m-%d")

# 표준출력을 result.txt로 저장하기 위한 설정
sys.stdout = io.TextIOWrapper(open("result.txt", "w", encoding="utf-8"), write_through=True)

# 아래에 기존 코드 그대로 붙여넣기
# (당신이 올린 코드 전체를 아래에 이어서 넣으면 됩니다)
!pip install yfinance
import yfinance as yf
import pandas as pd
from datetime import date # Import the date object

Ticker="QLD"
Start="2005-01-01"
End = date.today().strftime("%Y-%m-%d") # Set the end date to today's date


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
        return None
    smas = {
        'SMA5': row['SMA5'],
        'SMA20': row['SMA20'],
        'SMA200': row['SMA200']
    }
    sorted_state = tuple(k for k, v in sorted(smas.items(), key=lambda item: item[1], reverse=True))
    return sorted_state


def run_sma_backtest(ticker, start_date, end_date, strategy_map_config=None): # Add end_date parameter

    data = yf.download(ticker, start=start_date, end=end_date, auto_adjust=True) # Pass end_date to yf.download

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.droplevel(1)

    data['SMA5'] = data['Close'].rolling(window=5).mean()
    data['SMA20'] = data['Close'].rolling(window=20).mean()
    data['SMA200'] = data['Close'].rolling(window=200).mean()

    data['State'] = data.apply(get_sma_state, axis=1)
    data.dropna(inplace=True)

    weekly_prices = data['Close'].resample('W').last()
    weekly_signals = data['State'].resample('W').last()
    weekly_returns = weekly_prices.pct_change()

    backtest_df = pd.DataFrame({
        'signal': weekly_signals.shift(1),
        'qqq_return': weekly_returns
    }).dropna()

    if strategy_map_config is None:
        all_states = backtest_df['signal'].unique()
        strategy_map = {state: 1.0 for state in all_states}
        print("[알림] 전략 맵이 제공되지 않아 Buy-and-Hold (100% 보유)로 테스트합니다.\n")
    else:
        strategy_map = {}
        for k_str, allocation in strategy_map_config.items():
            key_tuple = tuple(k_str.split(' > '))
            strategy_map[key_tuple] = allocation

        all_states_in_data = set(backtest_df['signal'].unique())
        all_states_in_map = set(strategy_map.keys())

        missing_states = all_states_in_data - all_states_in_map
        if missing_states:
            print(f"[경고] 전략 맵에 누락된 상태가 있습니다: {missing_states}")
            print("누락된 상태는 현금(0%)으로 처리됩니다.")
            for state in missing_states:
                strategy_map[state] = 0.0  # 누락 시 현금 보유

    print("--- 적용된 전략 맵  ---")
    for state_tuple, alloc in strategy_map.items():
        state_str = ' > '.join(state_tuple)
        print(f"  {state_str:<25}: {alloc * 100:.0f}%")
    print("-" * 40)

    backtest_df['allocation'] = backtest_df['signal'].map(strategy_map)
    backtest_df['strategy_return'] = backtest_df['allocation'] * backtest_df['qqq_return']
    backtest_df['cumulative_strategy'] = (1 + backtest_df['strategy_return']).cumprod()

    backtest_df['b_and_h_return'] = backtest_df['qqq_return']  # 100% 보유
    backtest_df['cumulative_b_and_h'] = (1 + backtest_df['b_and_h_return']).cumprod()

    print("\n[백테스트 결과 요약]\n")

    # 전략 성과
    strat_cagr = calculate_cagr(backtest_df['cumulative_strategy'])
    strat_mdd = calculate_mdd(backtest_df['cumulative_strategy'])

    # B&H 성과
    bnh_cagr = calculate_cagr(backtest_df['cumulative_b_and_h'])
    bnh_mdd = calculate_mdd(backtest_df['cumulative_b_and_h'])

    print("## SMA 리밸런싱 전략 ##")
    print("Start_date:",Start, "Ticker: ",Ticker)
    print(f"   -> CAGR: {strat_cagr * 100:.2f}%")
    print(f"   -> MDD: {strat_mdd * 100:.2f}%")

    print("\n## Buy-and-Hold ##")
    print(f"   -> CAGR: {bnh_cagr * 100:.2f}%")
    print(f"   -> MDD: {bnh_mdd * 100:.2f}%")

    print("-" * 40)

    # 현재 상태 확인
    current_state = data.iloc[-1]['State']
    if current_state:
        current_state_str = ' > '.join(current_state)
        current_alloc = strategy_map.get(current_state, 0.0)  # 맵에 없으면 0
        print("\n[현재 상태 및 권장 비중]")
        print(f"현재 SMA 상태 ({data.index[-1].strftime('%Y-%m-%d')} 기준):")
        print(f"-> {current_state_str}")
        print(f"-> 정의된 전략에 따른 현재 비중: {current_alloc * 100:.0f}%")


# --- 스크립트 실행 ---
if __name__ == "__main__":


    my_strategy = {
        # 정배열 (강세)
        "SMA5 > SMA20 > SMA200": .7,
        "SMA20 > SMA5 > SMA200": 1,

        # 혼조세 (200일선이 중간)
        "SMA5 > SMA200 > SMA20": 0.5,
        "SMA20 > SMA200 > SMA5": 0,

        # 역배열 (약세)
        "SMA200 > SMA5 > SMA20": 0.2,
        "SMA200 > SMA20 > SMA5": 0.1
    }

    run_sma_backtest(
        ticker=Ticker,
        start_date=Start,
        end_date=End, # Pass the End variable
        strategy_map_config=my_strategy
    )
