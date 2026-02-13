import os
import asyncio
import sys
import requests
import json
from groq import Groq
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import datetime, timedelta
import re
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
    # 1. Zaman aşımı (30 dk)
    if datetime.now() - son_aktivite > timedelta(minutes=30):
        return True, "⏰ 30 dakika geçti"
    
    # 2. Manuel komut
    if mesaj.startswith("/yeni"):
        return True, "🆕 Manuel komut"
    
    # 3. Kelime benzerliği
    if onceki_mesajlar:
        benzerlik = kelime_benzerligi(mesaj, onceki_mesajlar[-1])
        if benzerlik < 0.15:
            return True, f"📌 Konu değişti"
    
    # 4. Soru değişimi
    soru_var = "?" in mesaj
    onceki_soru = "?" in onceki_mesajlar[-1] if onceki_mesajlar else False
    
    if soru_var and not onceki_soru:
        return True, "❓ Yeni soru"
    
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
        # Önce mevcut veriyi al
        response = requests.get(url, headers=headers)
        data = response.json().get("record", {})
        
        # Kullanıcıya ait konuları güncelle (son 20 konu)
        data[str(user_id)] = konular[-20:]
        
        # Kaydet
        requests.put(url, headers=headers, json=data)
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
        response = requests.get(url, headers=headers)
        data = response.json().get("record", {})
        konular = data.get(str(user_id), [])
        print(f"✅ JSONBin yüklendi: {user_id} - {len(konular)} konu", flush=True)
        return konular
    except Exception as e:
        print(f"❌ JSONBin yükleme hatası: {e}", flush=True)
        return []

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
        "Konuşmalarınız kalıcı hafızada saklanır, her zaman kaldığınız yerden devam edebilirsiniz. 🧠"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    user_id = str(update.effective_user.id)
    
    # "." MESAJINI SİL - KESİN ÇÖZÜM
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
        
        user_sessions[user_id] = {
            "konular": gecmis_konular if gecmis_konular else [],
            "aktif_konu": gecmis_konular[-1]["id"] if gecmis_konular else None,
            "son_aktivite": datetime.now(),
            "mesaj_gecmisi": []
        }
    
    session = user_sessions[user_id]
    simdi = datetime.now()
    
    # Konu değişti mi kontrol et
    degisti, sebep = konu_degisti_mi(
        user_id, 
        user_message, 
        session["mesaj_gecmisi"],
        session["son_aktivite"]
    )
    
    if degisti:
        # Yeni konu başlığı oluştur
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
        session["mesaj_gecmisi"] = []
        print(f"🆕 Yeni konu: {baslik} ({sebep})", flush=True)
        
        # Yeni konu açıldığında JSONBin'e kaydet
        asyncio.create_task(
            asyncio.to_thread(save_conversation, user_id, session["konular"])
        )
    
    # Mesajı aktif konuya ekle
    for konu in session["konular"]:
        if konu["id"] == session["aktif_konu"]:
            konu["mesajlar"].append({"role": "user", "content": user_message})
            break
    
    # Geçmişe ekle (benzerlik kontrolü için son 5 mesaj)
    if not user_message.startswith("/"):
        session["mesaj_gecmisi"].append(user_message)
        if len(session["mesaj_gecmisi"]) > 5:
            session["mesaj_gecmisi"].pop(0)
    
    session["son_aktivite"] = simdi
    
    # Normal mesaj - AI cevap ver
    if user_message.startswith("/"):
        return
    
    await update.message.chat.send_action(action="typing")
    
    try:
        # Önce bu konudaki son 5 mesajı al (bağlam için)
        aktif_konu_mesajlari = []
        for konu in session["konular"]:
            if konu["id"] == session["aktif_konu"]:
                aktif_konu_mesajlari = konu["mesajlar"][-10:]  # Son 10 mesaj
                break
        
        # Mesajları Groq formatına çevir
        mesaj_gecmisi = [
            {
                "role": "system", 
                "content": (
                    "Sen sadece Türkçe konuşan bir AI asistanısın. "
                    "Kesinlikle İngilizce veya yabancı kelime kullanma. "
                    "Kullanıcının sorusunun ana amacını anla, ona odaklan. "
                    "Gereksiz giriş cümleleri kurma, doğrudan ve net cevap ver.\n\n"
                    "ÖNCEKİ KONUŞMA BAĞLAMI:"
                )
            }
        ]
        
        # Geçmiş mesajları ekle
        for m in aktif_konu_mesajlari[-6:]:  # Son 6 mesajı al
            mesaj_gecmisi.append(m)
        
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=mesaj_gecmisi,
            temperature=0.3,
            max_tokens=500
        )
        
        ai_reply = completion.choices[0].message.content
        
        # Cevabı aktif konuya ekle
        for konu in session["konular"]:
            if konu["id"] == session["aktif_konu"]:
                konu["mesajlar"].append({"role": "assistant", "content": ai_reply})
                break
        
        # Her mesajdan sonra JSONBin'e kaydet (arka planda)
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
    
    # Webhook kurulumu
    webhook_url = f"https://{HOST}/{TELEGRAM_TOKEN}"
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(app.bot.set_webhook(url=webhook_url))
    print(f"✅ Webhook set to {webhook_url}", flush=True)
    
    # Webhook'u başlat
    print(f"🚀 Starting webhook on port {PORT}...", flush=True)
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TELEGRAM_TOKEN,
        webhook_url=webhook_url
    )

if __name__ == "__main__":
    main()
