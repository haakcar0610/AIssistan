from config import user_sessions
from utils.helpers import konu_degisti_mi
from memory.supabase import save_topic, save_message, save_memory, get_topic_by_title
import asyncio
import re
from datetime import datetime

def yeni_konu_olustur(user_id, user_message, sebep):
    """Yeni konu oluştur ve SUPABASE'e kaydet"""
    session = user_sessions[user_id]
    simdi = datetime.now()
    
    # Başlık oluştur (ilk 30 karakter veya tamamı)
    baslik = user_message[:30] + "..." if len(user_message) > 30 else user_message
    if user_message.startswith("/yeni"):
        baslik = "Yeni Konu"
    
    # Eğer "yeni konu: [başlık]" formatı varsa
    if "yeni konu:" in user_message.lower():
        baslik = user_message.lower().split("yeni konu:")[-1].strip()
        baslik = baslik[:50]  # Çok uzun olmasın
    
    # Konu ID'si (tarih + başlık)
    topic_id = f"{simdi.strftime('%Y%m%d')}_{baslik.replace(' ', '_')[:30]}"
    
    # SUPABASE'E KAYDET
    save_topic(user_id, topic_id, baslik, sebep)
    
    yeni_konu = {
        "id": topic_id,
        "baslik": baslik,
        "tarih": simdi.strftime("%d.%m.%Y %H:%M"),
        "sebep": sebep,
        "mesajlar": []
    }
    
    session["konular"].append(yeni_konu)
    session["aktif_konu"] = yeni_konu["id"]
    
    # Geçmişi kısalt
    if len(session["mesaj_gecmisi"]) > 20:
        session["mesaj_gecmisi"] = session["mesaj_gecmisi"][-10:]
        
    print(f"🆕 Yeni konu: {baslik} ({sebep})", flush=True)
    return topic_id

def konu_yukle(user_id, baslik):
    """Daha önceki bir konuyu yükle ve aktif yap"""
    session = user_sessions[user_id]
    
    # Konuyu Supabase'de ara
    konu = get_topic_by_title(user_id, baslik)
    
    if not konu:
        return False, "Konu bulunamadı."
    
    # Konuyu session'a ekle (eğer yoksa)
    mevcut = False
    for k in session["konular"]:
        if k["id"] == konu["topic_id"]:
            mevcut = True
            session["aktif_konu"] = k["id"]
            break
    
    if not mevcut:
        yeni_konu = {
            "id": konu["topic_id"],
            "baslik": konu["title"],
            "tarih": konu["created_at"],
            "sebep": konu.get("reason", ""),
            "mesajlar": []
        }
        session["konular"].append(yeni_konu)
        session["aktif_konu"] = yeni_konu["id"]
    
    print(f"📂 Konu yüklendi: {baslik}", flush=True)
    return True, konu["topic_id"]

def isim_kaydet(user_id, user_message, session):
    """Kullanıcı adını öğren ve belleğe kaydet"""
    if "benim adım" in user_message.lower() and len(user_message.split()) >= 4:
        ad = re.search(r"benim adım (\w+)", user_message.lower())
        if ad and ad.group(1) not in ["ne", "kim", "nasıl", "senin", "benim"]:
            isim = ad.group(1).capitalize()
            save_memory(user_id, "isim", isim)
            session["bellek"]["isim"] = {"value": isim}
            print(f"✅ İsim kaydedildi: {isim}", flush=True)
            return isim
    return None

def komut_kontrol(user_message):
    """Mesajın özel komut içerip içermediğini kontrol et"""
    
    # Konu yükleme: "bana [konu] getir"
    konu_yukleme = re.search(r"bana (.+?) (konuşmasını|konusunu|getir)", user_message.lower())
    if konu_yukleme:
        return "konu_yukle", konu_yukleme.group(1).strip()
    
    # Arama: "ara [konu] : [kelime]" veya "şu konuda [kelime] ara"
    arama = re.search(r"ara (.+?):(.+)", user_message.lower())
    if arama:
        return "ara_konu", (arama.group(1).strip(), arama.group(2).strip())
    
    # Genel arama: "[kelime] ara" veya "[kelime] ile ilgili mesaj"
    genel_arama = re.search(r"(.+?) (ara|ile ilgili)", user_message.lower())
    if genel_arama:
        return "ara_genel", genel_arama.group(1).strip()
    
    # Yeni konu: "yeni konu: [başlık]"
    if "yeni konu:" in user_message.lower():
        return "yeni_konu", user_message.lower().split("yeni konu:")[-1].strip()
    
    return None, None
