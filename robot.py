import yfinance as yf
import pandas as pd
import pandas_ta as ta
from xgboost import XGBClassifier
import requests
import time

# =======================================================
# تنظیمات ربات تلگرام (حتما مقادیر خودت را بگذار)
BOT_TOKEN = '8977258072:AAFmvZMAIszyIhABqsoC20SMMkSAOod01VY'
CHAT_ID = '90858617'
# =======================================================

# لیست بازارهای جذاب (طلا، نقره، نفت، نزدک، یورو/دلار)
symbols = {
    "Gold (XAU)": "GC=F",
    "Silver (XAG)": "SI=F",
    "Oil (WTI)": "CL=F",
    "NASDAQ": "^NDX",
    "EUR/USD": "EURUSD=X"
}

print("در حال اسکن بازارهای جهانی با هوش مصنوعی...\n")
results = []

for name, symbol in symbols.items():
    try:
        df = yf.download(symbol, period="5y", interval="1d", auto_adjust=True, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df.ta.rsi(length=14, append=True)
        df.ta.macd(append=True)
        df.ta.sma(length=50, append=True)
        df.ta.ema(length=20, append=True)
        df.ta.bbands(length=20, append=True)
        df['Target'] = (df['Close'].shift(-1) > df['Close']).astype(int)
        df.dropna(inplace=True)
        
        base_cols = ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume', 'Target']
        features = [col for col in df.columns if col not in base_cols]
        
        model = XGBClassifier(n_estimators=100, max_depth=3, random_state=42)
        model.fit(df[features], df['Target'])
        
        prob = model.predict_proba(df[features].iloc[-1:])[0]
        current_price = df['Close'].iloc[-1]
        
        # تنظیم تعداد ارقام اعشار بر اساس نوع بازار
        if current_price > 1000:
            price_str = f"${current_price:.2f}"
        elif current_price > 10:
            price_str = f"${current_price:.3f}"
        else:
            price_str = f"{current_price:.5f}"
        
        if prob[1] > 0.60:
            signal = "🟢 خرید (Long)"
        elif prob[0] > 0.60:
            signal = "🔴 فروش (Short)"
        else:
            signal = "⚪️ صبر کن"
            
        results.append(f"🔹 {name}\n   قیمت: {price_str}\n   سیگنال: {signal}\n")
        time.sleep(1)
        
    except Exception as e:
        print(f"خطا در {name}: {e}")

# ارسال پیام به تلگرام
message_text = "📡 سیگنال‌های هوش مصنوعی (طلا، نقره، نفت، نزدک)\n\n" + "\n".join(results) + "\n⚠️ این سیگنال‌ها تحلیل الگوریتمی هستند."

print("\nدر حال ارسال پیام به تلگرام...")
url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
payload = {'chat_id': CHAT_ID, 'text': message_text}
response = requests.post(url, data=payload)

if response.status_code == 200:
    print("✅ پیام با موفقیت به تلگرام ارسال شد!")
else:
    print(f"❌ خطا: {response.text}")
