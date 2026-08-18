import os
import time
import requests
import json
from web3 import Web3
from datetime import datetime

# ======== قراءة المتغيرات من GitHub Secrets ========
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ======== إعدادات الشبكة ========
RPC_URL = "https://bsc-dataseed1.binance.org/"
w3 = Web3(Web3.HTTPProvider(RPC_URL))

# عناوين العقود الحقيقية على BSC
WBNB = "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"
USDT = "0x55d398326f99059fF775485246999027B3197955"
PANCAKE_ROUTER_V2 = "0x10ED43C718714eb63d5aA57B78B54704E256024E"

# ======== دالة إرسال تيليجرام ========
def send_telegram(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("[-] Telegram Token أو Chat ID غير موجودة في المتغيرات.")
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print(f"فشل إرسال رسالة تيليجرام: {e}")

# ======== دالة قراءة السعر من PancakeSwap V2 ========
def get_price_pancake():
    try:
        router_abi = [
            {
                "inputs": [
                    {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                    {"internalType": "address[]", "name": "path", "type": "address[]"}
                ],
                "name": "getAmountsOut",
                "outputs": [{"internalType": "uint256[]", "name": "", "type": "uint256[]"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]
        router = w3.eth.contract(address=PANCAKE_ROUTER_V2, abi=router_abi)
        amount_in = 10**18
        path = [WBNB, USDT]
        amounts = router.functions.getAmountsOut(amount_in, path).call()
        price = amounts[1] / 10**18
        return price
    except Exception as e:
        print(f"خطأ في جلب سعر Pancake: {e}")
        return None

# ======== دالة قراءة السعر من Binance ========
def get_price_binance():
    try:
        resp = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BNBUSDT", timeout=5)
        data = resp.json()
        return float(data['price'])
    except Exception as e:
        print(f"خطأ في جلب سعر Binance: {e}")
        return None

# ======== دورة المسح الرئيسية ========
def scan_cycle(cycle_number):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    price_pancake = get_price_pancake()
    price_binance = get_price_binance()
    
    if price_pancake is None or price_binance is None:
        msg = f"⚠️ جولة #{cycle_number} الساعة {now}\nفشل في جلب الأسعار من أحد المصادر."
        send_telegram(msg)
        return
    
    diff = abs(price_pancake - price_binance)
    percent = (diff / price_binance) * 100
    
    if percent >= 0.3:  # عدّل الرقم إلى 2.0 لو أردت أرباحاً حقيقية
        msg = (
            f"🔥🔥🔥 فرصة أرباح كبيرة! 🔥🔥🔥\n"
            f"📅 الوقت: {now}\n"
            f"🟢 سعر Pancake: {price_pancake:.4f} USDT\n"
            f"🔵 سعر Binance: {price_binance:.4f} USDT\n"
            f"📈 نسبة الربح المتوقعة: {percent:.2f}%\n"
            f"💰 استعد للتنفيذ فوراً!"
        )
    else:
        msg = (
            f"🔄 جولة مراقبة #{cycle_number}\n"
            f"🕒 الوقت: {now}\n"
            f"سعر Pancake: {price_pancake:.4f} USDT\n"
            f"سعر Binance: {price_binance:.4f} USDT\n"
            f"📉 الفرق الحالي: {percent:.2f}%\n"
            f"❌ لا توجد فرصة ربح مجدية الآن."
        )
    
    send_telegram(msg)
    print(msg)

# ======== التشغيل الرئيسي ========
if __name__ == "__main__":
    print("=== Shadow Sniffer - بدء التشغيل ===")
    send_telegram("🚀 تم تفعيل Shadow Sniffer بنجاح، بدء المراقبة...")
    
    for i in range(1, 6):
        scan_cycle(i)
        if i < 5:
            time.sleep(30)
    
    send_telegram("⏸️ انتهت دورة المسح الحالية. سأعود للمسح بعد 10 دقائق (حسب الجدول).")
    print("=== انتهى التشغيل ===")
