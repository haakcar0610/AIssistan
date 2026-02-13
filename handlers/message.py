from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime

from config import user_sessions, client
from memory.jsonbin import load_conversation, load_memory, save_conversation
from memory.context import yeni_konu_olustur, isim_kaydet
from utils.helpers import konu_degisti_mi
import asyncio

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    user_id = str(update.effective_user.id)
    
    # "." MESAJINI SİL
    if user_message == ".":
        try:
            await update.message.delete()
            print(f"✅ Silindi: {update.message.message_id}", flush=True)
            return
        except:
            pass
    
    # Kullanıcı oturumunu başlat
    if user_id not in user_sessions:
        gecmis_konular = load_conversation(user_id)
        kalici_bellek = load_memory(user_id)
        
        user_sessions[user_id] = {
            "konular": gecmis_konular if gecmis_konular else [],
            "bellek": kalici_bellek,
            "aktif_konu": gecmis_konular[-1]["id"] if gecmis_konular else None,
            "son_aktivite": datetime.now(),
            "mesaj_gecmisi": []
        }
    
    session = user_sessions[user_id]
    simdi = datetime.now()
    
    # İsim kaydetme kontrolü
    isim_kaydet(user_id, user_message, session)
    
    # Konu değişimi kontrolü
    degisti, sebep = konu_degisti_mi(
        user_message, 
        session["mesaj_gecmisi"],
        session["son_aktivite"]
    )
    
    if degisti:
        yeni_konu_olustur(user_id, user_message, sebep)
    
    # Mesajı aktif konuya ekle
    for konu in session["konular"]:
        if konu["id"] == session["aktif_konu"]:
            konu["mesajlar"].append({"role": "user", "content": user_message})
            break
    
    # Geçmişe ekle
    if not user_message.startswith("/"):
        session["mesaj_gecmisi"].append(user_message)
        if len(session["mesaj_gecmisi"]) > 20:
            session["mesaj_gecmisi"].pop(0)
    
    session["son_aktivite"] = simdi
    
    # Komutları AI'a gönderme
    if user_message.startswith("/"):
        return
    
    await update.message.chat.send_action(action="typing")
    
    try:
        # Aktif konu mesajlarını al
        aktif_mesajlar = []
        for konu in session["konular"]:
            if konu["id"] == session["aktif_konu"]:
                aktif_mesajlar = konu["mesajlar"][-10:]
                break
             # KALICI BELLEĞİ SYSTEM PROMPT'A EKLE
        bellek_str = ""
        if session.get("bellek"):
            bellek_str = "Kullanıcı hakkında bildiklerin (ASLA UNUTMA): "
            for key, value in session["bellek"].items():
                if isinstance(value, dict) and "value" in value:
                    bellek_str += f"{key}: {value['value']}, "
                elif isinstance(value, str):
                    bellek_str += f"{key}: {value}, "
                else:
                    bellek_str += f"{key}: {str(value)}, "
        
        # GROQ'A GÖNDERİLECEK MESAJLARI HAZIRLA
        mesaj_gecmisi = [
            {
                "role": "system", 
                "content": (
                    "Sen sadece Türkçe konuşan bir AI asistanısın. "
                    "Kesinlikle İngilizce veya yabancı kelime kullanma. "
                    "Kullanıcının sorusunun ana amacını anla, ona odaklan. "
                    "Gereksiz giriş cümleleri kurma, doğrudan ve net cevap ver.\n\n"
                    f"{bellek_str}\n\n"
                    "ÖNCEKİ KONUŞMA BAĞLAMI:"
                )
            }
        ]
        
        # Geçmiş mesajları ekle
        for m in aktif_mesajlar[-6:]:
            mesaj_gecmisi.append(m)
        
        # GROQ API ÇAĞRISI
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=mesaj_gecmisi,
            temperature=0.3,
            max_tokens=500
        )
        
        ai_reply = completion.choices[0].message.content   
