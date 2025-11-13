import time
import requests
import numpy as np
from datetime import datetime, timedelta
from flask import Flask
from keep_alive import keep_alive

# ======================= AYARLAR =======================
TARGET_PRICE = 5800.0
CHAT_ID = 6117720602
BOT_TOKEN = "8342891622:AAH0Y66rdj4cMRYaMv87XgByIrgk6MRKlEY"
API_URL = "https://canlipiyasalar.haremaltin.com/tmp/altin.json?dil_kodu=tr"

# ========================================================


# ========= Telegram Gönderici =========
def telegram_mesaj_gonder(text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text}
    try:
        requests.post(url, data=data, timeout=10)
    except:
        pass


# ========= Altın Fiyat API =========
def altin_fiyat():
    try:
        r = requests.get(API_URL, timeout=10)
        r.raise_for_status()
        return float(r.json()["data"]["KULCEALTIN"]["satis"])
    except:
        return None


# ========= FİYAT KAYIT SİSTEMİ =========
fiyat_24saat = []
fiyat_haftalik = []
fiyat_aylik = []


def fiyat_kaydet(fiyat):
    suan = datetime.now()

    fiyat_24saat.append((suan, fiyat))
    fiyat_24saat[:] = [(t, f) for (t, f) in fiyat_24saat
                       if t > suan - timedelta(days=1)]

    fiyat_haftalik.append((suan, fiyat))
    fiyat_haftalik[:] = [(t, f) for (t, f) in fiyat_haftalik
                         if t > suan - timedelta(days=7)]

    fiyat_aylik.append((suan, fiyat))
    fiyat_aylik[:] = [(t, f) for (t, f) in fiyat_aylik
                      if t > suan - timedelta(days=30)]


# ========= RAPOR OLUŞTURUCU =========
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


# ========= PERİYODİK RAPOR SİSTEMİ =========
def periyodik_rapor_gonder():
    saat = datetime.now().hour
    dakika = datetime.now().minute

    # 24 saatlik rapor → Her gün 14:00
    if saat == 14 and dakika == 0 and len(fiyat_24saat) > 10:
        rapor = rapor_olustur(fiyat_24saat, "24 Saatlik Altın")
        telegram_mesaj_gonder(rapor)

    # Hafta sonu raporu → Pazar 21:00
    if datetime.now().weekday() == 6 and saat == 21 and dakika == 0 and len(
            fiyat_haftalik) > 10:
        rapor = rapor_olustur(fiyat_haftalik, "Haftalık Altın")
        telegram_mesaj_gonder(rapor)

    # Aylık rapor → Her ay 1’i, saat 09:00
    if datetime.now().day == 1 and saat == 9 and dakika == 0 and len(
            fiyat_aylik) > 10:
        rapor = rapor_olustur(fiyat_aylik, "Aylık Altın")
        telegram_mesaj_gonder(rapor)


# ======== 10 DAKİKA ANALİZ ========
fiyat_kayit = []
baslama_zamani = time.time()

# ======== Keep Alive Aç ========
keep_alive()

print("Altın Botu + Analiz Sistemleri Başladı!")

# =================== ANA LOOP ===================
alarm_gonderildi = False

while True:
    fiyat = altin_fiyat()

    if fiyat:
        print(f"Gram: {fiyat} TL")

        # Fiyat kayıt sistemi
        fiyat_kaydet(fiyat)

        # Periyodik rapor kontrol
        periyodik_rapor_gonder()

        # Alarm sistemi
        if fiyat <= TARGET_PRICE and not alarm_gonderildi:
            telegram_mesaj_gonder(
                f"📉 ALTIN ALARMI!\nGram altın {fiyat} TL\nHedef: {TARGET_PRICE} TL"
            )
            alarm_gonderildi = True

        if fiyat > TARGET_PRICE:
            alarm_gonderildi = False

        # 10 dk mini analiz
        fiyat_kayit.append(fiyat)
        if time.time() - baslama_zamani >= 600:
            ilk = fiyat_kayit[0]
            son = fiyat_kayit[-1]
            yuzde = ((son - ilk) / ilk) * 100

            telegram_mesaj_gonder(
                f"📊 10 Dakika Mini Analiz\n"
                f"İlk: {ilk}\nSon: {son}\nDeğişim: %{yuzde:.3f}")

            fiyat_kayit = []
            baslama_zamani = time.time()

    time.sleep(30)
