import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from IPython.display import display
import numpy as np

def get_last_two_fridays():
    """取得上週五和本週五的日期（以美股一週為基準，時區可自訂）"""
    today = datetime.now(ZoneInfo("Asia/Shanghai"))
    # 計算今天是星期幾（0=週一, 4=週五, 6=週日）
    weekday = today.weekday()
    
    # 找出本週的週五
    # (週五是 4)
    days_until_friday = 4 - weekday
    if days_until_friday < 0:
        # 今天是週六、週日或已過週五 → 回推到這週五
        this_friday = today + timedelta(days=days_until_friday)
    else:
        # 還沒到週五，直接往後加
        this_friday = today + timedelta(days=days_until_friday)
    
    # 上週五直接往前推 7 天
    last_friday = this_friday - timedelta(days=7)
    last_monday = last_friday - timedelta(days=last_friday.weekday())  # 上週一
    
    return last_friday.date(), this_friday.date(), last_monday.date()

def safe_float(arr):
    """抽出array唯一元素轉float，或原本就是float就直接回傳"""
    if isinstance(arr, (list, np.ndarray)):
        if len(arr) > 0:
            return float(arr[0])
        else:
            return None
    elif hasattr(arr, "item"):  # np scalar
        return float(arr.item())
    else:
        return float(arr)

def print_adjusted_returns(df, adjusted_total_return):
    symbol_parts = []
    for idx, row in df.iterrows():
        name = row['symbol']
        pct = row['change_pct']
        pred = row['prediction']
        if pd.isna(pct) or pred not in ['bullish', 'bearish']:
            continue  # 忽略缺資料或沒指定預測方向
        adj_pct = pct if pred == 'bullish' else -pct
        sign = '+' if adj_pct >= 0 else '-'
        # 絕對值顯示
        symbol_parts.append(f"{name} {sign}{abs(adj_pct):.1f}%")
    # 合併顯示
    total_sign = '+' if adjusted_total_return >= 0 else '-'
    print(f"最終結果：")
    print("（" + "、".join(symbol_parts) + f"）：{total_sign}{abs(adjusted_total_return):.1f}%")
    return

def calc_weekly_return(symbols, predictions):
    # start_date, end_date = get_last_two_fridays()
    end_date, _, start_date = get_last_two_fridays()
    results = []
    for symbol in symbols:
        try:
            df = yf.download(symbol, start=start_date, end=end_date + timedelta(days=1), interval='1d', progress=False, auto_adjust=False)
            df = df.loc[df.index.dayofweek < 5]  # 過濾週末
            df_fridays = df[(df.index.date == start_date) | (df.index.date == end_date)]
            if len(df_fridays) < 2:
                results.append({
                    'symbol': symbol,
                    'open': None,
                    'close': None,
                    'change_pct': None,
                    'msg': '兩個週五其中之一缺資料',
                    'prediction': predictions.get(symbol, 'none'),
                    'prediction_result': 'N/A'
                })
                continue

            last_friday_close_arr = df_fridays.loc[df_fridays.index.date == start_date, 'Close'].values
            this_friday_close_arr = df_fridays.loc[df_fridays.index.date == end_date, 'Close'].values
            last_friday_close = safe_float(last_friday_close_arr[0])
            this_friday_close = safe_float(this_friday_close_arr[0])
            change_pct = (this_friday_close - last_friday_close) / last_friday_close * 100

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
                'open': last_friday_close,
                'close': this_friday_close,
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
    df_show.columns = ['股票代碼', '上週五收盤價', '本週五收盤價', '漲跌幅(%)', '備註', '預測', '預測結果']
    
    # 防呆: 如果資料是None，不要 round
    for col in ['上週五收盤價', '本週五收盤價', '漲跌幅(%)']:
        df_show[col] = pd.to_numeric(df_show[col], errors='coerce').round(3 if col=='漲跌幅(%)' else 2)
    
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
        
        if isinstance(adjusted_total_return, np.ndarray):
            if adjusted_total_return.size == 1:
                adjusted_total_return = float(adjusted_total_return[0])
            else:
                adjusted_total_return = float(adjusted_total_return.sum())
        print(f"調整後總報酬率（根據預測方向）：{adjusted_total_return:.2f}%")

    if df['change_pct'].isnull().any():
        print("\n有標的資料缺漏（如非美股、停牌、代碼錯誤），詳見『備註』欄。")
        
    print_adjusted_returns(df, adjusted_total_return)

# 使用者輸入的預測
predictions = {
    'META': 'bullish',
    'NI': 'bullish',
    'PRIM': 'bullish',
    'GNW': 'bullish',
    'XYZ': 'bullish'
}

syms = ['META', 'NI', 'PRIM', 'GNW', 'XYZ']  # 預設股票代碼
show_result(syms, predictions)