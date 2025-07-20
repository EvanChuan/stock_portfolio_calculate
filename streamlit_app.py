import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import numpy as np

st.set_page_config(page_title="股票多標的週報酬分析器", layout="wide")
st.title("📈 股票多標的週報酬與預測分析器")

def get_last_two_fridays():
    today = datetime.now(ZoneInfo("Asia/Shanghai"))
    weekday = today.weekday()
    days_until_friday = 4 - weekday
    if days_until_friday < 0:
        this_friday = today + timedelta(days=days_until_friday)
    else:
        this_friday = today + timedelta(days=days_until_friday)
    last_monday = today - timedelta(days=today.weekday())
    return last_monday.date(), this_friday.date()

def calc_weekly_return(symbols, predictions):
    start_date, end_date = get_last_two_fridays()
    results = []
    for symbol in symbols:
        try:
            df = yf.download(
                symbol, 
                start=start_date, 
                end=end_date + timedelta(days=1), 
                interval='1d', 
                progress=False, 
                auto_adjust=False
            )
            df = df.loc[df.index.dayofweek < 5]  # 過濾週末

            # 只保留上週五與本週五
            df_fridays = df[(df.index.date == start_date) | (df.index.date == end_date)]
            last_monday_arr = df_fridays.loc[df_fridays.index.date == start_date, 'Open'].values
            this_friday_close_arr = df_fridays.loc[df_fridays.index.date == end_date, 'Close'].values

            last_monday_open = float(last_monday_arr[0]) if len(last_monday_arr) else None
            this_friday_close = float(this_friday_close_arr[0]) if len(this_friday_close_arr) else None

            if last_monday_open is None or this_friday_close is None:
                results.append({
                    'symbol': symbol,
                    'open': last_monday_open,
                    'close': this_friday_close,
                    'change_pct': None,
                    'msg': '兩個週五其中之一缺資料',
                    'prediction': predictions.get(symbol, 'none'),
                    'prediction_result': 'N/A'
                })
                continue

            change_pct = (this_friday_close - last_monday_open) / last_monday_open * 100

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
                'open': last_monday_open,
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
    return results, start_date, end_date

def print_adjusted_returns(df, adjusted_total_return):
    symbol_parts = []
    for idx, row in df.iterrows():
        name = row['symbol']
        pct = row['change_pct']
        pred = row['prediction']
        if pd.isna(pct) or pred not in ['bullish', 'bearish']:
            continue
        adj_pct = pct if pred == 'bullish' else -pct
        sign = '+' if adj_pct >= 0 else '-'
        symbol_parts.append(f"{name} {sign}{abs(adj_pct):.1f}%")
    total_sign = '+' if adjusted_total_return >= 0 else '-'
    return "（" + "、".join(symbol_parts) + f"）：{total_sign}{abs(adjusted_total_return):.1f}%"

# ==== Streamlit UI（每檔股票一個欄位） ====
st.write("請直接於下方每一行輸入股票代碼並選擇預測方向（空白的欄位將略過）")
st.write("因資料來源為yahoo finace，如果標的非美股交易所標的，請查詢以下資料來源的正確標的代碼，否則可能找不到資料。")
st.write("例如：台積電的美股代碼為 TSM，台灣交易所為 2330.TW;小米的港股代碼為 1810.HK，請注意不要輸入錯誤的代碼。")
st.markdown("[點我開啟 yahoo finace 查詢](https://finance.yahoo.com/markets/stocks/most-active/)")

num_stocks = 5  # 你可以讓用戶調整這個數量
stock_inputs = []
pred_directions = []

with st.form("multi_input_form"):
    cols = st.columns(num_stocks)
    for i in range(num_stocks):
        with cols[i]:
            code = st.text_input(f"標的{i+1}", key=f"code_{i}").strip().upper()
            pred = st.selectbox(f"預測方向{i+1}", options=["看漲", "看跌"], key=f"pred_{i}")
        stock_inputs.append(code)
        pred_directions.append(pred)
    submitted = st.form_submit_button("計算週報酬率")

if submitted:
    # 過濾空白
    symbols = [code for code in stock_inputs if code]
    preds = {code: "bullish" if pred_directions[i] == "看漲" else "bearish" 
             for i, code in enumerate(stock_inputs) if code}
    if not symbols:
        st.warning("請至少輸入一檔股票代碼！")
        st.stop()
    with st.spinner("正在查詢及計算，請稍候..."):
        results, start_date, end_date = calc_weekly_return(symbols, preds)
        df = pd.DataFrame(results)
    df_show = df.copy()
    df_show = df_show.rename(columns={
        'symbol': '股票代碼',
        'open': '週一開盤價',
        'close': '本週五收盤價',
        'change_pct': '漲跌幅(%)',
        'msg': '備註',
        'prediction': '預測',
        'prediction_result': '預測結果'
    })
    st.subheader(f"查詢區間：{start_date.strftime('%Y/%m/%d')} ~ {end_date.strftime('%Y/%m/%d')}")
    st.dataframe(df_show, use_container_width=True)

    valid_returns = df['change_pct'].dropna()
    adjusted_returns = []
    for idx, row in df.iterrows():
        if pd.notna(row['change_pct']) and row['prediction'] in ['bullish', 'bearish']:
            adj = row['change_pct'] if row['prediction'] == 'bullish' else -row['change_pct']
            adjusted_returns.append(adj)
    adjusted_total_return = float(np.sum(adjusted_returns)) if adjusted_returns else 0.0

    if adjusted_returns:
        st.success(print_adjusted_returns(df, adjusted_total_return))
        st.info(f"調整後總報酬率：{adjusted_total_return:.2f}%")
    else:
        st.warning("本次查詢沒有有效報酬率可加總")
