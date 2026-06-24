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

# تابع تحلیل هر ارز در یک تایم فریم خاص
def analyze(symbol, period, interval):
    df = yf.download(symbol, period=period, interval=interval, auto_adjust=True, progress=False)
    if df.empty: return None, None, None, "No Data"
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    df.ta.rsi(length=14, append=True)
    df.ta.macd(append=True)
    df.ta.ema(length=20, append=True)
    df.ta.atr(length=14, append=True)
    df['Target'] = (df['Close'].shift(-1) > df['Close']).astype(int)
    df.dropna(inplace=True)
    
    if len(df) < 50: return None, None, None, "No Data"
        
    base_cols = ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume', 'Target']
    features = [col for col in df.columns if col not in base_cols]
    
    model = XGBClassifier(n_estimators=100, max_depth=3, random_state=42)
    model.fit(df[features], df['Target'])
    
    prob = model.predict_proba(df[features].iloc[-1:])[0]
    price = df['Close'].iloc[-1]
    atr = df['ATRr_14'].iloc[-1]
    
    if prob[1] > 0.60: return price, atr, "🟢 خرید", "Buy"
    elif prob[0] > 0.60: return price, atr, "🔴 فروش", "Sell"
    else: return price, atr, "⚪️ صبر", "Wait"

print("Scanning Multi-Timeframe...\n")
results = []

for name, symbol in symbols.items():
    try:
        # ۱. تحلیل تایم فریم روزانه (روند کلی)
        price_d, _, signal_d, action_d = analyze(symbol, "2y", "1d")
        time.sleep(2) # وقفه برای جلوگیری از بن شدن
        
        # ۲. تحلیل تایم فریم ۴ ساعته (نقطه ورود)
        price_4h, atr_4h, signal_4h, action_4h = analyze(symbol, "60d", "1h") # یاهو 4h را راحت نمی‌دهد، 1h جایگزین می‌شود
        
        if price_d is None or price_4h is None:
            results.append(f"🔹 {name}\n   ⚠️ داده‌ای در دسترس نیست.")
            continue
            
        if price_4h > 1000: p_str = f"${price_4h:.2f}"
        elif price_4h > 10: p_str = f"${price_4h:.3f}"
        else: p_str = f"{price_4h:.5f}"
        
        text = f"🔹 {name}\n   قیمت: {p_str}\n   روند روزانه: {signal_d}\n   روند ساعتی: {signal_4h}\n"
        
        # ۳. ترکیب سیگنال‌ها
        if action_d == "Buy" and action_4h == "Buy":
            tp = price_4h + (atr_4h * 2)
            sl = price_4h - (atr_4h * 1)
            text += f"   ✅ سیگنال نهایی: خرید قوی (تایید دوگانه)\n   🎯 TP: ${tp:.2f} | 🛑 SL: ${sl:.2f}"
        elif action_d == "Sell" and action_4h == "Sell":
            tp = price_4h - (atr_4h * 2)
            sl = price_4h + (atr_4h * 1)
            text += f"   ✅ سیگنال نهایی: فروش قوی (تایید دوگانه)\n   🎯 TP: ${tp:.2f} | 🛑 SL: ${sl:.2f}"
        else:
            text += f"   ⚠️ سیگنال نهایی: تضاد وجود دارد (معامله نکنید)"
            
        results.append(text)
        
    except Exception as e:
        print(f"Error on {name}: {e}")

if not results:
    results.append("خطای سرور یاهو فایننس. لطفا بعدا تلاش کنید.")

message_text = "📡 سیگنال‌های هوش مصنوعی (استراتژی ترکیبی 1D + 1H)\n\n" + "\n\n".join(results) + "\n\n⚠️ مدیریت سرمایه فراموش نشود."

print("\nSending to Telegram...")
url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
payload = {'chat_id': CHAT_ID, 'text': message_text}
response = requests.post(url, data=payload)

if response.status_code == 200:
    print("✅ Sent!")
else:
    print(f"❌ Error: {response.text}")
