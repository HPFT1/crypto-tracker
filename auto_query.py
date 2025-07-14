import sys
import os
import pandas as pd

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app import get_top_coins, get_price_history, calculate_macd_rsi, save_history

target_coin_id = 'bitcoin'

print("✅ Hello, this is auto_query.py")
print("🚀 [Step 1] 啟動 auto_query.py")

try:
    print("🌐 正在連線至 CoinGecko API...")
    coin_list = get_top_coins()
    print(f"✅ CoinGecko 回傳資料筆數：{len(coin_list)}")

    coin_data = next((c for c in coin_list if c['id'] == target_coin_id), None)
    print(f"🔍 尋找 {target_coin_id}：{'找到 ✅' if coin_data else '❌ 沒找到'}")

    if coin_data:
        coin_id = coin_data['id']
        coin_name = coin_data['name']
        print(f"📈 [Step 6] 抓取 {coin_name} 歷史價格資料...")
        df = get_price_history(coin_id, days=7)
        if df is not None and not df.empty:
            print(f"📊 [Step 7] 成功取得資料，共 {len(df)} 筆")
            df = calculate_macd_rsi(df)
            save_history(coin_id, coin_name, df)
            print("💾 [Step 8] 已儲存歷史紀錄 ✅。")
        else:
            print(f"⚠️ 查不到 {coin_name} 的價格資料")
    else:
        print(f"❌ 幣種 {target_coin_id} 不在清單中")
except Exception as e:
    print(f"❌ 發生錯誤：{e}")