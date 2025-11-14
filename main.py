import time
import threading
import requests
import numpy as np
from datetime import datetime, timedelta
from flask import Flask
import os

# ======================= AYARLAR =======================
TARGET_PRICE = 5800.0
CHAT_ID = 6117720602
BOT_TOKEN = "8342891622:AAH0Y66rdj4cMRYaMv87XgByIrgk6MRKlEY"
API_URL = "https://canlipiyasalar.haremaltin.com/tmp/altin.json?dil_kodu=tr"
SELF_URL = "https://altin-8cf8.onrender.com"   # Render URL'in
# =======================================================

app = Flask(__name__)


@app.route("/")
def home():
    return "Bot çalışıyor"


def telegram_mesaj_gonder(text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text}
    try:
        resp = requests.post(url, data=data, timeout=10)
        print("Telegram status:", resp.status_code, resp.text)
    except Exception as e:
        print("Telegram HATASI:", e)


def altin_fiyat():
    try:
        r = requests.get(API_URL, timeout=10)
        r.raise_for_status()
        return float(r.json()["data"]["KULCEALTIN"]["satis"])
    except Exception as e:
        print("Altın fiyatı alınamadı:", e)
        return None


# ========= FİYAT KAYIT SİSTEMİ =========
fiyat_24saat = []
fiyat_haftalik = []
fiyat_aylik = []


def fiyat_kaydet(fiyat):
    suan = datetime.now()

    # 24 saatlik
    fiyat_24saat[:] = [(t, f) for (t, f) in fiyat_24saat if t > suan - timedelta(days=1)]
    fiyat_24saat.append((suan, fiyat))

    # haftalık
    fiyat_haftalik[:] = [(t, f) for (t, f) in fiyat_haftalik if t > suan - timedelta(days=7)]
    fiyat_haftalik.append((suan, fiyat))

    # aylık
    fiyat_aylik[:] = [(t, f) for (t, f) in fiyat_aylik if t > suan - timedelta(days=30)]
    fiyat_aylik.append((suan, fiyat))


def rapor_olustur(veriler, baslik):
    fiyatlar = [f for (t, f) in veriler]

    ilk = fiyatlar[0]
    son = fiyatlar[-1]
    degisim = ((son - ilk) / ilk) * 100

    ort = sum(fiyatlar) / len(fiyatlar)
    mx = max(fiyatlar)
    mn = min(fiyatlar)
    vol = np.std(fiyatlar)

    return f"""
📊 {baslik} Raporu ({datetime.now().strftime('%H:%M')})

Ortalama: {ort:.2f} TL
En Yüksek: {mx:.2f} TL
En Düşük: {mn:.2f} TL
Değişim: %{degisim:.2f}
Volatilite: {vol:.2f}
"""


def periyodik_rapor_gonder():
    saat = datetime.now().hour
    dakika = datetime.now().minute

    # 24 saatlik rapor → her gün 14:00
    if saat == 14 and dakika == 0 and len(fiyat_24saat) > 10:
        telegram_mesaj_gonder(rapor_olustur(fiyat_24saat, "24 Saatlik Altın"))

    # haftalık rapor → pazar 21:00
    if datetime.now().weekday() == 6 and saat == 21 and dakika == 0 and len(fiyat_haftalik) > 10:
        telegram_mesaj_gonder(rapor_olustur(fiyat_haftalik, "Haftalık Altın"))

    # aylık rapor → ayın 1’i 09:00
    if datetime.now().day == 1 and saat == 9 and dakika == 0 and len(fiyat_aylik) > 10:
        telegram_mesaj_gonder(rapor_olustur(fiyat_aylik, "Aylık Altın"))


# ========= SELF PING (UYUMASIN DİYE) =========
def self_ping():
    try:
        requests.get(SELF_URL, timeout=5)
        print("Self ping atıldı")
    except Exception as e:
        print("Self ping HATASI:", e)


def bot_loop():
    alarm = False
    fiyat_kayit = []
    baslama_zamani = time.time()

    while True:
        fiyat = altin_fiyat()

        if fiyat:
            print("Gram:", fiyat)
            fiyat_kaydet(fiyat)
            periyodik_rapor_gonder()

            # Render uyumasın diye her 4 dakikada bir kendi URL'ine ping at
            if int(time.time()) % 240 == 0:
                self_ping()

            # Alarm sistemi
            if fiyat <= TARGET_PRICE and not alarm:
                telegram_mesaj_gonder(
                    f"📉 ALTIN ALARMI!\nGram: {fiyat} TL\nHedef: {TARGET_PRICE} TL"
                )
                alarm = True

            if fiyat > TARGET_PRICE:
                alarm = False

            # 10 dakikalık mini analiz
            fiyat_kayit.append(fiyat)
            if time.time() - baslama_zamani >= 600:
                ilk = fiyat_kayit[0]
                son = fiyat_kayit[-1]
                yuzde = ((son - ilk) / ilk) * 100
                telegram_mesaj_gonder(
                    f"📊 10 Dakika Mini Analiz\nİlk: {ilk}\nSon: {son}\nDeğişim: %{yuzde:.3f}"
                )
                fiyat_kayit = []
                baslama_zamani = time.time()

        time.sleep(30)


if __name__ == "__main__":
    telegram_mesaj_gonder("✅ Render üzerinde altın botu başlatıldı")
    threading.Thread(target=bot_loop, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
