import re
from datetime import datetime, timedelta

def kelime_benzerligi(mesaj1, mesaj2):
    """İki mesaj arasındaki kelime benzerliğini hesapla (0-1 arası)"""
    if not mesaj1 or not mesaj2:
        return 0
    
    kelimeler1 = set(re.findall(r'\w+', mesaj1.lower()))
    kelimeler2 = set(re.findall(r'\w+', mesaj2.lower()))
    
    if not kelimeler1 or not kelimeler2:
        return 0
    
    ortak = kelimeler1 & kelimeler2
    benzerlik = len(ortak) / max(len(kelimeler1), len(kelimeler2))
    return benzerlik

def konu_degisti_mi(mesaj, onceki_mesajlar, son_aktivite, esik=0.3):
    """
    Konu değişimini kontrol et
    - esik: 0.3 = %30 benzerlik altı yeni konu
    """
    # 1. Zaman aşımı (60 dk - daha toleranslı)
    if datetime.now() - son_aktivite > timedelta(minutes=60):
        return True, "⏰ 60 dakika geçti"
    
    # 2. Manuel komut
    if mesaj.startswith("/yeni"):
        return True, "🆕 Manuel komut"
    
    # 3. Eğer hiç mesaj yoksa veya çok az varsa, yeni konu açma
    if len(onceki_mesajlar) < 3:  # En az 3 mesaj olmalı ki konu değişsin
        print(f"📊 Çok az mesaj ({len(onceki_mesajlar)}), konu korunuyor", flush=True)
        return False, None
    
    # 4. Kelime benzerliği
    if onceki_mesajlar:
        benzerlik = kelime_benzerligi(mesaj, onceki_mesajlar[-1])
        print(f"📊 Benzerlik hesabı: %{benzerlik*100:.0f} (eşik: %{esik*100:.0f})", flush=True)
        
        # Eğer benzerlik çok düşükse yeni konu
        if benzerlik < esik:
            return True, f"📌 Konu değişti (%{benzerlik*100:.0f} benzerlik)"
        else:
            print(f"✅ Konu aynı devam ediyor (%{benzerlik*100:.0f} benzerlik)", flush=True)
    
    return False, None

def tarih_formatla(tarih_str, format="%d.%m.%Y %H:%M"):
    """Supabase'den gelen tarihi formatla"""
    try:
        if isinstance(tarih_str, str):
            # ISO formatını düzenle
            tarih_str = tarih_str.replace("T", " ")[:16]
            return tarih_str
        return str(tarih_str)
    except:
        return "tarih yok"

def mesaj_kisalt(mesaj, uzunluk=100):
    """Mesajı belirtilen uzunlukta kısalt"""
    if len(mesaj) <= uzunluk:
        return mesaj
    return mesaj[:uzunluk] + "..."

def konu_basligi_olustur(mesaj, max_uzunluk=50):
    """İlk mesajdan konu başlığı oluştur"""
    # İlk 50 karakter veya ilk cümle
    baslik = mesaj[:max_uzunluk]
    if '.' in baslik:
        baslik = baslik.split('.')[0]
    if len(mesaj) > max_uzunluk:
        baslik += "..."
    return baslik

def temizle_metin(metin):
    """Metni temizle: gereksiz boşlukları, karakterleri düzenle"""
    if not metin:
        return ""
    # Birden fazla boşluğu tek boşluk yap
    metin = re.sub(r'\s+', ' ', metin)
    # Baştaki ve sondaki boşlukları temizle
    return metin.strip()
