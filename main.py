import os
import time
import requests
from web3 import Web3
from datetime import datetime

# ======== قراءة المتغيرات ========
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ======== نقاط RPC احتياطية ========
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
    print("فشل الاتصال بجميع نقاط BSC.")
    exit()

# عناوين العقود
WBNB = "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"
USDT = "0x55d398326f99059fF775485246999027B3197955"

# عنواني الروترين (V2 و V3) لمقارنة الأسعار بينهما
PANCAKE_ROUTER_V2 = "0x10ED43C718714eb63d5aA57B78B54704E256024E"
PANCAKE_ROUTER_V3 = "0x13f4EA83D0bd40E75C8222255bc855a974568Dd4"

def send_telegram(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=10)
    except:
        pass

def get_price_from_router(router_address, retries=2):
    """يجلب السعر من أي روتير (V2 أو V3)"""
    for attempt in range(retries):
        try:
            abi = [{
                "inputs": [
                    {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                    {"internalType": "address[]", "name": "path", "type": "address[]"}
                ],
                "name": "getAmountsOut",
                "outputs": [{"internalType": "uint256[]", "name": "", "type": "uint256[]"}],
                "stateMutability": "view",
                "type": "function"
            }]
            router = w3.eth.contract(address=router_address, abi=abi)
            amount_in = 10**18
            path = [WBNB, USDT]
            amounts = router.functions.getAmountsOut(amount_in, path).call()
            return amounts[1] / 10**18
        except:
            time.sleep(1)
    return None

def scan_cycle(cycle_number):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    price_v2 = get_price_from_router(PANCAKE_ROUTER_V2)
    price_v3 = get_price_from_router(PANCAKE_ROUTER_V3)
    
    # إذا فشل المصدران
    if price_v2 is None and price_v3 is None:
        msg = f"⚠️ جولة #{cycle_number} الساعة {now}\nفشل جلب الأسعار من جميع المجمعات."
        send_telegram(msg)
        return
    
    # إذا نجح مصدر واحد فقط
    if price_v2 is None:
        msg = f"⚠️ جولة #{cycle_number} الساعة {now}\nسعر V2 غير متاح، نعرض V3 فقط.\n🟣 سعر V3: {price_v3:.4f} USDT"
        send_telegram(msg)
        return
    if price_v3 is None:
        msg = f"⚠️ جولة #{cycle_number} الساعة {now}\nسعر V3 غير متاح، نعرض V2 فقط.\n🟢 سعر V2: {price_v2:.4f} USDT"
        send_telegram(msg)
        return
    
    # الحالة الطبيعية (المصدران موجودان)
    diff = abs(price_v2 - price_v3)
    percent = (diff / price_v3) * 100
    
    if percent >= 0.3:  # عدّل إلى 2.0 للأرباح الحقيقية
        msg = (
            f"🔥🔥🔥 فرصة أرباح كبيرة بين V2 و V3! 🔥🔥🔥\n"
            f"📅 الوقت: {now}\n"
            f"🟢 V2: {price_v2:.4f} USDT\n"
            f"🟣 V3: {price_v3:.4f} USDT\n"
            f"📈 نسبة الربح المتوقعة: {percent:.2f}%\n"
            f"💰 استعد للتنفيذ فوراً!"
        )
    else:
        msg = (
            f"🔄 جولة مراقبة #{cycle_number}\n"
            f"🕒 الوقت: {now}\n"
            f"V2: {price_v2:.4f} USDT\n"
            f"V3: {price_v3:.4f} USDT\n"
            f"📉 الفرق الحالي: {percent:.2f}%\n"
            f"❌ لا توجد فرصة ربح مجدية الآن."
        )
    
    send_telegram(msg)
    print(msg)

# ======== التشغيل الرئيسي ========
if __name__ == "__main__":
    print("=== Shadow Sniffer V3 (مقارنة V2 vs V3) ===")
    send_telegram("🚀 تم تفعيل النسخة V3 - مقارنة مجمعين لا مركزيين...")
    
    for i in range(1, 6):
        scan_cycle(i)
        if i < 5:
            time.sleep(30)
    
    send_telegram("⏸️ انتهت دورة المسح. سأعود بعد 10 دقائق.")
