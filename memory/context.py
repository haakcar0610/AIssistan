from config import user_sessions
from utils.helpers import konu_degisti_mi
from memory.jsonbin import save_conversation, save_memory
import asyncio
import re

def yeni_konu_olustur(user_id, user_message, sebep):
    """Yeni konu oluştur ve oturuma ekle"""
    from datetime import datetime
    session = user_sessions[user_id]
    simdi = datetime.now()
    
    baslik = user_message[:30] + "..." if len(user_message) > 30 else user_message
    if user_message.startswith("/yeni"):
        baslik = "Yeni Konu"
        
    yeni_konu = {
        "id": simdi.strftime("%Y%m%d_%H%M%S"),
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
    
    if session["konular"]:
        asyncio.create_task(
            asyncio.to_thread(save_conversation, user_id, session["konular"])
        )

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
