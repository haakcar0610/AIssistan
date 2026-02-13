import os
import asyncio
import sys
import requests
import json
import re
from groq import Groq
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import datetime, timedelta
from collections import Counter

# Tokenlar
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
JSONBIN_ID = os.environ.get("JSONBIN_ID")
JSONBIN_SECRET = os.environ.get("JSONBIN_SECRET")
PORT = int(os.environ.get("PORT", 8080))
HOST = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "aissistan-v2.onrender.com")

# Groq client
client = Groq(api_key=GROQ_API_KEY)

# Konu takibi için sözlük (her kullanıcı için)
user_sessions = {}

def kelime_benzerligi(mesaj1, mesaj2):
    kelimeler1 = set(re.findall(r'\w+', mesaj1.lower()))
    kelimeler2 = set(re.findall(r'\w+', mesaj2.lower()))
    
    if not kelimeler1 or not kelimeler2:
        return 0
    
    ortak = kelimeler1 & kelimeler2
    benzerlik = len(ortak) / max(len(kelimeler1), len(kelimeler2))
    return benzerlik

def konu_degisti_mi(user_id, mesaj, onceki_mesajlar, son_aktivite):
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

# JSONBin Hafıza Fonksiyonları
def save_conversation(user_id, konular):
    """Tüm konuşmaları JSONBin'e kaydet"""
    url = f"https://api.jsonbin.io/v3/b/{JSONBIN_ID}"
    headers = {
        "Content-Type": "application/json",
        "X-Master-Key": JSONBIN_SECRET
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json().get("record", {})
        
        data[str(user_id)] = konular[-20:]
        
        requests.put(url, headers=headers, json=data, timeout=5)
        print(f"✅ JSONBin kaydedildi: {user_id} - {len(konular)} konu", flush=True)
        return True
    except Exception as e:
        print(f"❌ JSONBin kayıt hatası: {e}", flush=True)
        return False

def load_conversation(user_id):
    """Kullanıcının geçmiş konuşmalarını yükle"""
    url = f"https://api.jsonbin.io/v3/b/{JSONBIN_ID}"
    headers = {"X-Master-Key": JSONBIN_SECRET}
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json().get("record", {})
        konular = data.get(str(user_id), [])
        print(f"✅ JSONBin yüklendi: {user_id} - {len(konular)} konu", flush=True)
        return konular
    except Exception as e:
        print(f"❌ JSONBin yükleme hatası: {e}", flush=True)
        return []

# KALICI BELLEK FONKSİYONLARI
def save_memory(user_id, key, value):
    """Kullanıcıya ait kalıcı bilgileri kaydet (ad, tercihler, vb)"""
    url = f"https://api.jsonbin.io/v3/b/{JSONBIN_ID}"
    headers = {
        "Content-Type": "application/json",
        "X-Master-Key": JSONBIN_SECRET
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json().get("record", {})
        
        if "memory" not in data:
            data["memory"] = {}
        if str(user_id) not in data["memory"]:
            data["memory"][str(user_id)] = {}
            
        data["memory"][str(user_id)][key] = {
            "value": value,
            "timestamp": datetime.now().isoformat()
        }
        
        requests.put(url, headers=headers, json=data, timeout=5)
        print(f"✅ Bellek kaydedildi: {user_id} - {key}: {value}", flush=True)
        return True
    except Exception as e:
        print(f"❌ Bellek kayıt hatası: {e}", flush=True)
        return False

def load_memory(user_id):
    """Kullanıcının kalıcı bilgilerini yükle"""
    url = f"https://api.jsonbin.io/v3/b/{JSONBIN_ID}"
    headers = {"X-Master-Key": JSONBIN_SECRET}
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json().get("record", {})
        memory = data.get("memory", {}).get(str(user_id), {})
        print(f"✅ Bellek yüklendi: {user_id} - {len(memory)} bilgi", flush=True)
        return memory
    except Exception as e:
        print(f"❌ Bellek yükleme hatası: {e}", flush=True)
        return {}

async def konular(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id not in user_sessions:
        await update.message.reply_text("Henüz hiç konuşmanız yok.")
        return
    
    konular = user_sessions[user_id]["konular"][-10:]
    
    if not konular:
        await update.message.reply_text("Konu listeniz boş.")
        return
    
    mesaj = "📋 **Son Konularınız:**\n\n"
    for konu in reversed(konular):
        aktif = "✅ " if konu["id"] == user_sessions[user_id]["aktif_konu"] else "   "
        mesaj += f"{aktif}• {konu['baslik']}\n"
        mesaj += f"  🕐 {konu['tarih']} - {konu.get('sebep', '')}\n\n"
    
    await update.message.reply_text(mesaj)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Merhaba! Ben AI asistanınız. Size Türkçe yardımcı olabilirim.\n\n"
        "📌 /konular ile geçmiş konuşmalarınızı görebilirsiniz.\n"
        "🆕 /yeni ile yeni bir konu başlatabilirsiniz.\n\n"
        "Adınızı, tercihlerinizi ve önemli bilgileri hiç unutmam. 🧠"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    user_id = str(update.effective_user.id)
    
    # "." MESAJINI SİL
    if user_message == ".":
        try:
            await update.message.delete()
            print(f"✅ Silindi (1.yöntem): {update.message.message_id}", flush=True)
            return
        except Exception as e:
            print(f"❌ 1.yöntem hatası: {e}", flush=True)
            
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=update.message.message_id
            )
            print(f"✅ Silindi (2.yöntem): {update.message.message_id}", flush=True)
            return
        except Exception as e:
            print(f"❌ 2.yöntem hatası: {e}", flush=True)
            
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=update.message.message_id + 1
            )
        except:
            pass
        
        print("❌ TÜM SİLME YÖNTEMLERİ BAŞARISIZ!", flush=True)
        return
    
    # Kullanıcı oturumunu başlat - JSONBin'den yükle
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
    
    # KULLANICI ADINI ÖĞREN VE KAYDET
    if "benim adım" in user_message.lower():
        ad = re.search(r"benim adım (\w+)", user_message.lower())
        if ad:
            save_memory(user_id, "isim", ad.group(1))
            session["bellek"]["isim"] = {"value": ad.group(1)}
    
    # Konu değişti mi kontrol et
    degisti, sebep = konu_degisti_mi(
        user_id, 
        user_message, 
        session["mesaj_gecmisi"],
        session["son_aktivite"]
    )
    
    if degisti:
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
        # GEÇMİŞİ SIFIRLAMA - SADECE KISALT
        if len(session["mesaj_gecmisi"]) > 20:
            session["mesaj_gecmisi"] = session["mesaj_gecmisi"][-10:]
        print(f"🆕 Yeni konu: {baslik} ({sebep})", flush=True)
        
        asyncio.create_task(
            asyncio.to_thread(save_conversation, user_id, session["konular"])
        )
    
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
    
    if user_message.startswith("/"):
        return
    
    await update.message.chat.send_action(action="typing")
    
    try:
        aktif_konu_mesajlari = []
        for konu in session["konular"]:
            if konu["id"] == session["aktif_konu"]:
                aktif_konu_mesajlari = konu["mesajlar"][-10:]
                break
        
        # KALICI BELLEĞİ SYSTEM PROMPT'A EKLE
        bellek_str = ""
        if session.get("bellek"):
            bellek_str = "Kullanıcı hakkında bildiklerin: "
            for key, value in session["bellek"].items():
                if isinstance(value, dict) and "value" in value:
                    bellek_str += f"{key}: {value['value']}, "
        
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
        
        for m in aktif_konu_mesajlari[-6:]:
            mesaj_gecmisi.append(m)
        
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=mesaj_gecmisi,
            temperature=0.3,
            max_tokens=500
        )
        
        ai_reply = completion.choices[0].message.content
        
        for konu in session["konular"]:
            if konu["id"] == session["aktif_konu"]:
                konu["mesajlar"].append({"role": "assistant", "content": ai_reply})
                break
        
        asyncio.create_task(
            asyncio.to_thread(save_conversation, user_id, session["konular"])
        )
        
    except Exception as e:
        ai_reply = f"Hata: {str(e)}"
        print(f"GROQ HATASI: {e}", flush=True)
    
    await update.message.reply_text(ai_reply)

def main():
    print("🚨 TEST: Bot başlatılıyor...", flush=True)
    print(f"✅ JSONBin ID: {JSONBIN_ID}", flush=True)
    
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("konular", konular))
    app.add_handler(CommandHandler("yeni", handle_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    webhook_url = f"https://{HOST}/{TELEGRAM_TOKEN}"
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(app.bot.set_webhook(url=webhook_url))
    print(f"✅ Webhook set to {webhook_url}", flush=True)
    
    print(f"🚀 Starting webhook on port {PORT}...", flush=True)
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TELEGRAM_TOKEN,
        webhook_url=webhook_url
    )

if __name__ == "__main__":
    main()
