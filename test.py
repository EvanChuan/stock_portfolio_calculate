import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from IPython.display import display
import ipywidgets as widgets

def get_last_full_week():
    """取得最近一個完整的美股交易週（週一到週五）"""
    today = datetime.now(ZoneInfo("Asia/Shanghai"))  # 明確指定中國時區
    weekday = today.weekday()
    # 若今天為週末，自動回推到週五
    if weekday >= 5:
        today = today - timedelta(days=weekday - 4)
    
    last_monday = today - timedelta(days=today.weekday())
    last_friday = last_monday + timedelta(days=4)
    return last_monday.date(), last_friday.date()

def calc_weekly_return(symbols, predictions):
    start_date, end_date = get_last_full_week()
    results = []
    for symbol in symbols:
        try:
            df = yf.download(symbol, start=start_date, end=end_date + timedelta(days=1), interval='1d', progress=False, auto_adjust=False)
            df = df.loc[df.index.dayofweek < 5]  # 過濾週末
            if len(df) < 2 or df.index[0].date() > start_date or df.index[-1].date() < end_date:
                results.append({
                    'symbol': symbol,
                    'open': None,
                    'close': None,
                    'change_pct': None,
                    'msg': '資料不足或非美股',
                    'prediction': predictions.get(symbol, 'none'),  # 預測，預設 'none'
                    'prediction_result': 'N/A'
                })
                continue

            monday_open = df.iloc[0]['Open'].iloc[0]  # 從 Series 取第一個值
            friday_close = df.iloc[-1]['Close'].iloc[0]  # 從 Series 取第一個值
            change_pct = (friday_close - monday_open) / monday_open * 100
            pred = predictions.get(symbol, 'none')
            pred_result = 'N/A'
            if pred == 'bullish' and change_pct > 0:
                pred_result = 'Correct'
            elif pred == 'bearish' and change_pct < 0:
                pred_result = 'Correct'
            elif pred in ['bullish', 'bearish']:
                pred_result = 'Wrong'
            results.append({
                'symbol': symbol,
                'open': monday_open,
                'close': friday_close,
                'change_pct': change_pct,
                'msg': '',
                'prediction': pred,
                'prediction_result': pred_result
            })
        except Exception as e:
            results.append({
                'symbol': symbol,
                'open': None,
                'close': None,
                'change_pct': None,
                'msg': f'下載資料失敗: {str(e)}',
                'prediction': predictions.get(symbol, 'none'),
                'prediction_result': 'N/A'
            })
            continue
        
    return results, start_date, end_date

def show_result(symbols, predictions):
    results, start_date, end_date = calc_weekly_return(symbols, predictions)
    
    if not results:
        print("無有效數據可顯示")
        return

    df = pd.DataFrame(results)
    df_show = df[['symbol', 'open', 'close', 'change_pct', 'msg', 'prediction', 'prediction_result']]
    df_show.columns = ['股票代碼', '週一開盤價', '週五收盤價', '漲跌幅(%)', '備註', '預測', '預測結果']
    df_show['週一開盤價'] = df_show['週一開盤價'].round(2)
    df_show['週五收盤價'] = df_show['週五收盤價'].round(2)
    df_show['漲跌幅(%)'] = df_show['漲跌幅(%)'].round(3)
    

    try:
        from IPython.display import display
        display(df_show)
    except ImportError:
        print(df_show)

    valid_returns = df['change_pct'].dropna()
    print(f"\n查詢區間：{start_date.strftime('%Y年%m月%d日')} ~ {end_date.strftime('%Y年%m月%d日')}")
    if valid_returns.empty:
        print("本次查詢沒有有效報酬率可加總")
    else:
        # 計算調整後的總報酬率
        adjusted_returns = []
        for index, row in df.iterrows():
            if pd.notna(row['change_pct']) and row['prediction'] in ['bullish', 'bearish']:
                if row['prediction'] == 'bearish':
                    adjusted_returns.append(row['change_pct'] * -1)
                else:  # bullish
                    adjusted_returns.append(row['change_pct'])
        adjusted_total_return = sum(adjusted_returns) if adjusted_returns else 0
        correct_pred_returns = df[df['prediction_result'] == 'Correct']['change_pct'].dropna().sum()  # 預測正確的報酬率總和
        
        print(f"調整後總報酬率（根據預測）：{adjusted_total_return:.2f}%")
        if pd.notna(correct_pred_returns) and correct_pred_returns != 0:
            print(f"預測正確的報酬率總和：{correct_pred_returns:.2f}%")

    if df['change_pct'].isnull().any():
        print("\n有標的資料缺漏（如非美股、停牌、代碼錯誤），詳見『備註』欄.")

# 使用者輸入的預測
predictions = {
    'AVAV': 'bullish',
    'PSX': 'bullish',
    'JPM': 'bullish',
    'PG': 'bearish',
    'TAP': 'bearish'
}

syms = ['AVAV', 'PSX', 'JPM', 'PG', 'TAP']  # 預設股票代碼
show_result(syms, predictions)