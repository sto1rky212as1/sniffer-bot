import os
import time
import requests
import json
from web3 import Web3
from datetime import datetime

# ======== قراءة المتغيرات ========
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ======== قائمة نقاط RPC احتياطية (لو وحدة علقت، يروح للثانية) ========
RPC_URLS = [
    "https://bsc-dataseed1.binance.org/",
    "https://bsc-dataseed2.binance.org/",
    "https://rpc.ankr.com/bsc"
]

def get_web3():
    for url in RPC_URLS:
        try:
            w3 = Web3(Web3.HTTPProvider(url, request_kwargs={'timeout': 10}))
            if w3.is_connected():
                return w3
        except:
            continue
    return None

w3 = get_web3()
if w3 is None:
    send_telegram("❌ فشل الاتصال بجميع نقاط BSC. تأكد من الإنترنت.")
    exit()

# عناوين العقود الحقيقية على BSC
WBNB = "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"
USDT = "0x55d398326f99059fF775485246999027B3197955"
PANCAKE_ROUTER_V2 = "0x10ED43C718714eb63d5aA57B78B54704E256024E"

def send_telegram(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("[-] Telegram Token أو Chat ID غير موجودة.")
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print(f"فشل إرسال رسالة تيليجرام: {e}")

def get_price_pancake(retries=3):
    """يجلب السعر من PancakeSwap مع إعادة المحاولة"""
    for attempt in range(retries):
        try:
            router_abi = [{
                "inputs": [
                    {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                    {"internalType": "address[]", "name": "path", "type": "address[]"}
                ],
                "name": "getAmountsOut",
                "outputs": [{"internalType": "uint256[]", "name": "", "type": "uint256[]"}],
                "stateMutability": "view",
                "type": "function"
            }]
            router = w3.eth.contract(address=PANCAKE_ROUTER_V2, abi=router_abi)
            amount_in = 10**18
            path = [WBNB, USDT]
            amounts = router.functions.getAmountsOut(amount_in, path).call()
            price = amounts[1] / 10**18
            return price
        except Exception as e:
            print(f"محاولة Pancake #{attempt+1} فشلت: {e}")
            time.sleep(2)
    return None

def get_price_binance():
    """يجلب السعر من Binance API"""
    try:
        resp = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BNBUSDT", timeout=5)
        if resp.status_code == 200:
            return float(resp.json()['price'])
        return None
    except:
        return None

def scan_cycle(cycle_number):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # جلب الأسعار مع محاولات متعددة
    price_pancake = get_price_pancake(retries=2)
    price_binance = get_price_binance()
    
    # لو فشل المصدرين معاً
    if price_pancake is None and price_binance is None:
        msg = f"⚠️ جولة #{cycle_number} الساعة {now}\nفشل جلب الأسعار من جميع المصادر (قد تكون الشبكة مشغولة)."
        send_telegram(msg)
        return
    
    # لو فشل Pancake لكن Binance نجح (نستخدم سعر Binance كبديل)
    if price_pancake is None:
        msg = f"⚠️ جولة #{cycle_number} الساعة {now}\nسعر Pancake غير متاح حالياً، نعرض سعر Binance فقط.\n🔵 سعر Binance: {price_binance:.4f} USDT"
        send_telegram(msg)
        return
    
    # لو فشل Binance لكن Pancake نجح
    if price_binance is None:
        msg = f"⚠️ جولة #{cycle_number} الساعة {now}\nسعر Binance غير متاح، نعرض سعر Pancake فقط.\n🟢 سعر Pancake: {price_pancake:.4f} USDT"
        send_telegram(msg)
        return
    
    # الحالة الطبيعية (المصدران موجودان)
    diff = abs(price_pancake - price_binance)
    percent = (diff / price_binance) * 100
    
    if percent >= 0.3:  # عدّل إلى 2.0 للأرباح الحقيقية
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
    print("=== Shadow Sniffer V2 - بدء التشغيل ===")
    send_telegram("🚀 تم تفعيل Shadow Sniffer V2 (نسخة مقاومة للأعطال)...")
    
    for i in range(1, 6):
        scan_cycle(i)
        if i < 5:
            time.sleep(30)
    
    send_telegram("⏸️ انتهت دورة المسح الحالية. سأعود بعد 10 دقائق.")
    print("=== انتهى التشغيل ===")
