import yfinance as yf
import pandas as pd
import pandas_ta as ta
from xgboost import XGBClassifier
import requests
import time

# =======================================================
BOT_TOKEN = '8977258072:AAFmvZMAIszyIhABqsoC20SMMkSAOod01VY'
CHAT_ID = '90858617'
# =======================================================

symbols = {
    "Gold (XAU)": "GC=F",
    "Oil (WTI)": "CL=F",
    "EUR/USD": "EURUSD=X",
    "Bitcoin (BTC)": "BTC-USD",
    "Ethereum (ETH)": "ETH-USD"
}

print("Scanning markets (1H Timeframe)...\n")
results = []

for name, symbol in symbols.items():
    try:
        # تغییر مهم: گرفتن کندل‌های ۱ ساعته در ۶۰ روز گذشته
        df = yf.download(symbol, period="60d", interval="1h", auto_adjust=True, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df.ta.rsi(length=14, append=True)
        df.ta.macd(append=True)
        df.ta.ema(length=20, append=True)
        df.ta.atr(length=14, append=True) # اضافه شدن اندیکاتور نوسانات برای حد ضرر
        df['Target'] = (df['Close'].shift(-1) > df['Close']).astype(int)
        df.dropna(inplace=True)
        
        base_cols = ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume', 'Target']
        features = [col for col in df.columns if col not in base_cols]
        
        model = XGBClassifier(n_estimators=100, max_depth=3, random_state=42)
        model.fit(df[features], df['Target'])
        
        prob = model.predict_proba(df[features].iloc[-1:])[0]
        current_price = df['Close'].iloc[-1]
        current_atr = df['ATRr_14'].iloc[-1]
        
        # فرمت کردن قیمت برای نمایش
        if current_price > 1000:
            price_str = f"${current_price:.2f}"
        elif current_price > 10:
            price_str = f"${current_price:.3f}"
        else:
            price_str = f"{current_price:.5f}"
        
        # محاسبه حد سود و ضرر با نسبت ریسک به ریوارد 1 به 2
        if prob[1] > 0.60:
            signal = "🟢 خرید (Long)"
            tp = current_price + (current_atr * 2)
            sl = current_price - (current_atr * 1)
            details = f"   🎯 TP: ${tp:.2f} | 🛑 SL: ${sl:.2f}"
        elif prob[0] > 0.60:
            signal = "🔴 فروش (Short)"
            tp = current_price - (current_atr * 2)
            sl = current_price + (current_atr * 1)
            details = f"   🎯 TP: ${tp:.2f} | 🛑 SL: ${sl:.2f}"
        else:
            signal = "⚪️ صبر کن"
            details = ""
            
        results.append(f"🔹 {name}\n   قیمت: {price_str}\n   سیگنال: {signal}\n{details}\n")
        time.sleep(1)
        
    except Exception as e:
        print(f"Error on {name}: {e}")

message_text = "📡 سیگنال‌های هوش مصنوعی (تایم‌فریم ۱ ساعته)\n\n" + "\n".join(results) + "\n⚠️ مدیریت سرمایه فراموش نشود."

print("\nSending to Telegram...")
url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
payload = {'chat_id': CHAT_ID, 'text': message_text}
response = requests.post(url, data=payload)

if response.status_code == 200:
    print("✅ Sent!")
else:
    print(f"❌ Error: {response.text}")
