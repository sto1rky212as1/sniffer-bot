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
PANCAKE_ROUTER_V2 = "0x10ED43C718714eb63d5aA57B78B54704E256024E"

def send_telegram(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=10)
    except:
        pass

def get_current_price(retries=2):
    """يجلب السعر الحالي من PancakeSwap V2"""
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
            router = w3.eth.contract(address=PANCAKE_ROUTER_V2, abi=abi)
            amount_in = 10**18
            path = [WBNB, USDT]
            amounts = router.functions.getAmountsOut(amount_in, path).call()
            return amounts[1] / 10**18
        except:
            time.sleep(1)
    return None

# ======== المتغيرات العامة لتخزين الأسعار السابقة (لحساب المتوسطات) ========
price_history = []

def generate_signal(current_price, price_history):
    """
    توليد إشارة تداول بناءً على تقاطع المتوسطات المتحركة البسيطة (SMA)
    SMA5 و SMA10
    """
    if len(price_history) < 10:
        return "انتظار", None, None, None, None  # بيانات غير كافية
    
    # حساب SMA5 و SMA10
    sma5 = sum(price_history[-5:]) / 5
    sma10 = sum(price_history[-10:]) / 10
    
    # تحديد الإشارة
    if sma5 > sma10 * 1.002:  # شرط شراء مع زيادة 0.2% لتجنب الإشارات الخاطئة
        signal = "شراء"
        entry_price = current_price
        stop_loss = entry_price * 0.98  # وقف خسارة 2% تحت سعر الدخول
        take_profit = entry_price * 1.04  # جني أرباح 4% فوق سعر الدخول
        reason = f"SMA5 ({sma5:.2f}) > SMA10 ({sma10:.2f}) بفارق {(sma5/sma10-1)*100:.2f}%"
    elif sma5 < sma10 * 0.998:  # شرط بيع
        signal = "بيع"
        entry_price = current_price
        stop_loss = entry_price * 1.02  # وقف خسارة 2% فوق سعر الدخول (للبيع)
        take_profit = entry_price * 0.96  # جني أرباح 4% تحت سعر الدخول (للبيع)
        reason = f"SMA5 ({sma5:.2f}) < SMA10 ({sma10:.2f}) بفارق {(1 - sma5/sma10)*100:.2f}%"
    else:
        signal = "لا تتداول"
        entry_price = None
        stop_loss = None
        take_profit = None
        reason = f"SMA5 ({sma5:.2f}) قريب من SMA10 ({sma10:.2f})، الفرق ضئيل"
    
    return signal, entry_price, stop_loss, take_profit, reason

def scan_cycle(cycle_number, price_history):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    current_price = get_current_price()
    
    if current_price is None:
        msg = f"⚠️ جولة #{cycle_number} الساعة {now}\nفشل جلب السعر الحالي."
        send_telegram(msg)
        return price_history
    
    # إضافة السعر الجديد للتاريخ
    price_history.append(current_price)
    if len(price_history) > 20:
        price_history.pop(0)  # الاحتفاظ بآخر 20 سعر فقط
    
    # توليد الإشارة
    signal, entry, sl, tp, reason = generate_signal(current_price, price_history)
    
    # بناء الرسالة
    if signal == "شراء":
        msg = (
            f"🟢 **إشارة شراء قوية** 🟢\n"
            f"📅 الوقت: {now}\n"
            f"💰 سعر الدخول المقترح: {entry:.4f} USDT\n"
            f"🛑 وقف الخسارة: {sl:.4f} USDT (خسارة 2%)\n"
            f"🎯 جني الأرباح: {tp:.4f} USDT (ربح 4%)\n"
            f"📊 السبب: {reason}\n"
            f"⚠️ نصيحة: ضع أمر شراء معلق عند {entry:.4f}، وأوقف الخسارة عند {sl:.4f}."
        )
    elif signal == "بيع":
        msg = (
            f"🔴 **إشارة بيع قوية** 🔴\n"
            f"📅 الوقت: {now}\n"
            f"💰 سعر الدخول المقترح: {entry:.4f} USDT\n"
            f"🛑 وقف الخسارة: {sl:.4f} USDT (خسارة 2%)\n"
            f"🎯 جني الأرباح: {tp:.4f} USDT (ربح 4%)\n"
            f"📊 السبب: {reason}\n"
            f"⚠️ نصيحة: ضع أمر بيع معلق عند {entry:.4f}، وأوقف الخسارة عند {sl:.4f}."
        )
    else:
        msg = (
            f"⏸️ **لا توجد إشارة تداول حالياً**\n"
            f"📅 الوقت: {now}\n"
            f"💰 السعر الحالي: {current_price:.4f} USDT\n"
            f"📊 السبب: {reason}\n"
            f"💡 انتظر حتى يتكون اتجاه واضح."
        )
    
    send_telegram(msg)
    print(msg)
    return price_history

# ======== التشغيل الرئيسي ========
if __name__ == "__main__":
    print("=== Shadow Sniffer - نظام التداول الذكي (SMA Crossover) ===")
    send_telegram("🚀 تم تفعيل نظام التداول الذكي (متوسطات متحركة)...")
    
    price_history = []
    for i in range(1, 6):
        price_history = scan_cycle(i, price_history)
        if i < 5:
            time.sleep(30)
    
    send_telegram("⏸️ انتهت دورة التحليل. سأعود بعد 10 دقائق.")
