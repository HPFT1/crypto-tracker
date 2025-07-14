# app.py
import streamlit as st
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import datetime
import os
import logging

plt.rcParams['font.family'] = 'Arial Unicode MS'
logging.basicConfig(filename="log.txt", level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")

@st.cache_data(ttl=3600)
def get_top_coins(limit=50):
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {"vs_currency": "usd", "order": "market_cap_desc", "per_page": limit, "page": 1}
        res = requests.get(url, params=params, timeout=10)
        return res.json()
    except Exception as e:
        logging.error(f"get_top_coins error: {e}")
        return []

def get_price_history(coin_id='bitcoin', days=7, vs_currency='usd'):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        params = {'vs_currency': vs_currency, 'days': days, 'interval': 'daily'}
        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        df = pd.DataFrame(data['prices'], columns=['時間戳', '價格'])
        df['時間戳'] = pd.to_datetime(df['時間戳'], unit='ms')
        return df
    except Exception as e:
        logging.error(f"get_price_history error: {e}")
        return None

def calculate_macd_rsi(df):
    df = df.copy()
    df['EMA12'] = df['價格'].ewm(span=12, adjust=False).mean()
    df['EMA26'] = df['價格'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    delta = df['價格'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

def draw_price_chart(df, coin_name, days):
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(df['時間戳'], df['價格'], marker='o')
    ax.set_title(f'{coin_name} 價格走勢圖（{days}天）')
    ax.set_xlabel('日期')
    ax.set_ylabel('價格 (USD)')
    ax.grid(True)
    st.pyplot(fig)

def draw_candlestick_chart(df, coin_name):
    df = df.copy()
    df['Open'] = df['價格']
    df['High'] = df['價格']
    df['Low'] = df['價格']
    df['Close'] = df['價格']
    fig = go.Figure(data=[go.Candlestick(x=df['時間戳'],
                                         open=df['Open'],
                                         high=df['High'],
                                         low=df['Low'],
                                         close=df['Close'])])
    fig.update_layout(title=f'{coin_name} K 線圖', xaxis_title='時間', yaxis_title='價格 (USD)', xaxis_rangeslider_visible=False)
    st.plotly_chart(fig)

def save_history(coin_id, coin_name, df):
    record = {
        "幣種": coin_name,
        "ID": coin_id,
        "查詢時間": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "最新價格": df['價格'].iloc[-1],
        "5日均價": df['價格'].rolling(5).mean().iloc[-1],
        "推薦動作": "買進" if df['價格'].iloc[-1] < df['價格'].rolling(5).mean().iloc[-1] else "賣出"
    }
    file_path = "history.csv"
    df_history = pd.DataFrame([record])
    if os.path.exists(file_path):
        df_old = pd.read_csv(file_path)
        df_all = pd.concat([df_old, df_history], ignore_index=True)
    else:
        df_all = df_history
    df_all.to_csv(file_path, index=False)

def show_history_table():
    if os.path.exists("history.csv"):
        df = pd.read_csv("history.csv")
        st.subheader("📋 查詢紀錄")
        st.dataframe(df)

def export_history(format="csv"):
    if not os.path.exists("history.csv"):
        st.error("❌ 沒有查詢紀錄")
        return
    df = pd.read_csv("history.csv")
    if format == "excel":
        path = "history_export.xlsx"
        df.to_excel(path, index=False)
    else:
        path = "history_export.csv"
        df.to_csv(path, index=False)
    with open(path, "rb") as f:
        st.download_button(f"📥 下載 {format.upper()} 檔", f, file_name=path)

# =================== Streamlit 介面 ===================
st.set_page_config(page_title="幣圈走勢分析工具", layout="wide")
st.title("📈 幣圈走勢圖工具（強化版）")

# 幣種資料
coin_list = get_top_coins()
if not coin_list:
    st.error("❌ 無法取得幣種清單")
    st.stop()

# 幣種搜尋（關鍵字）
keyword = st.text_input("🔍 搜尋幣種（輸入關鍵字）").lower()
filtered = [coin for coin in coin_list if keyword in coin["name"].lower() or keyword in coin["symbol"].lower()] if keyword else coin_list
options = [f"{c['name']} ({c['symbol'].upper()})" for c in filtered]
selected = st.selectbox("請選擇幣種", options)

# 取得幣種 ID
coin_id, coin_name = "", ""
for coin in filtered:
    if f"{coin['name']} ({coin['symbol'].upper()})" == selected:
        coin_id = coin["id"]
        coin_name = coin["name"]
        break

# 查詢設定
days = st.slider("📅 查詢天數", 1, 31, 7)
trigger_high = st.number_input("🚨 高於此價格提醒", value=0.0)
trigger_low = st.number_input("🚨 低於此價格提醒", value=0.0)
use_macd = st.checkbox("📉 顯示 MACD")
use_rsi = st.checkbox("📈 顯示 RSI")
use_candle = st.checkbox("🕯️ 顯示 K 線圖")

if st.button("查詢"):
    with st.spinner("📡 查詢中..."):
        df = get_price_history(coin_id, days)
        if df is not None and not df.empty:
            df = calculate_macd_rsi(df)
            latest_price = df['價格'].iloc[-1]
            ma5 = df['價格'].rolling(5).mean().iloc[-1]
            action = "✅ 建議買進" if latest_price < ma5 else "💰 建議賣出"

            st.markdown(f"### 💰 最新價格：{latest_price:.2f} USD")
            st.markdown(f"📊 5日平均：{ma5:.2f} USD")
            st.markdown(f"📣 {action}")

            if trigger_high > 0 and latest_price > trigger_high:
                st.warning(f"⚠️ 價格高於 {trigger_high} USD！")
            if trigger_low > 0 and latest_price < trigger_low:
                st.warning(f"⚠️ 價格低於 {trigger_low} USD！")

            if use_candle:
                draw_candlestick_chart(df, coin_name)
            else:
                draw_price_chart(df, coin_name, days)

            if use_macd:
                st.line_chart(df[['MACD', 'Signal']])
            if use_rsi:
                st.line_chart(df[['RSI']])

            save_history(coin_id, coin_name, df)
        else:
            st.error("❌ 查詢失敗，請稍後再試")

# 歷史查詢與匯出
show_history_table()
st.markdown("---")
col1, col2 = st.columns(2)
with col1:
    if st.button("📤 匯出 CSV"):
        export_history("csv")
with col2:
    if st.button("📤 匯出 Excel"):
        export_history("excel")
