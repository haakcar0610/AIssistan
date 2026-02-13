import re
from datetime import datetime, timedelta

def kelime_benzerligi(mesaj1, mesaj2):
    """İki mesaj arasındaki kelime benzerliğini hesapla"""
    kelimeler1 = set(re.findall(r'\w+', mesaj1.lower()))
    kelimeler2 = set(re.findall(r'\w+', mesaj2.lower()))
    
    if not kelimeler1 or not kelimeler2:
        return 0
    
    ortak = kelimeler1 & kelimeler2
    return len(ortak) / max(len(kelimeler1), len(kelimeler2))

def konu_degisti_mi(mesaj, onceki_mesajlar, son_aktivite):
    """Konu değişimini kontrol et"""
    # 1. Zaman aşımı (60 dk)
    if datetime.now() - son_aktivite > timedelta(minutes=60):
        return True, "⏰ 60 dakika geçti"
    
    # 2. Manuel komut
    if mesaj.startswith("/yeni"):
        return True, "🆕 Manuel komut"
    
    # 3. Kelime benzerliği (%5)
    if onceki_mesajlar:
        benzerlik = kelime_benzerligi(mesaj, onceki_mesajlar[-1])
        if benzerlik < 0.05:
            return True, f"📌 Konu değişti"
    
    return False, None
