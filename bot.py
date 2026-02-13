import os
import asyncio
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

from memory import Memory

# Tokenlar DOĞRUDAN environment'tan alınıyor
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
PORT = int(os.environ.get("PORT", 8080))
HOST = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "localhost")

# Kontrol
if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    raise ValueError("TELEGRAM_TOKEN ve GROQ_API_KEY environment variable'ları tanımlanmalı!")

# Groq client
client = Groq(api_key=GROQ_API_KEY)

# Hafıza sistemi
memory = Memory()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot başlangıç mesajı"""
    user_id = str(update.effective_user.id)
    name = memory.get_user_name(user_id)
    
    if name:
        await update.message.reply_text(f"Hoş geldin {name}! 👋")
    else:
        await update.message.reply_text(
            "Merhaba! Ben AI asistanınız.\n\n"
            "Adınızı söyleyerek başlayabiliriz: 'benim adım ...'"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    user_id = str(update.effective_user.id)
    
    # "." mesajını sil
    if user_message == ".":
        try:
            await update.message.delete()
            return
        except:
            pass
    
    # İsim öğrenme
    if "benim adım" in user_message.lower():
        ad = re.search(r"benim adım (\w+)", user_message.lower())
        if ad and ad.group(1) not in ["ne", "kim", "nasıl"]:
            name = ad.group(1).capitalize()
            memory.save_user_name(user_id, name)
            await update.message.reply_text(f"Tamam {name}, artık seni hatırlayacağım! 🧠")
            return
    
    # İsim sorma
    if "benim adım ne" in user_message.lower():
        name = memory.get_user_name(user_id)
        if name:
            await update.message.reply_text(f"Adın {name}.")
        else:
            await update.message.reply_text("Adını bilmiyorum. Bana 'benim adım ...' diye söyleyebilirsin.")
        return
    
    # Normal mesaj işleme
    await update.message.chat.send_action(action="typing")
    
    try:
        # Kullanıcı adını al
        user_name = memory.get_user_name(user_id)
        
        # Son 30 mesajı al
        recent = memory.get_recent_messages(user_id, limit=30)
        
        # Mesajı kaydet (kullanıcı mesajı)
        memory.save_message(user_id, "user", user_message)
        
        # Prompt oluştur
        messages = []
        
        # Sistem mesajı
        system_msg = "Sen Türkçe konuşan bir AI asistanısın. Sadece Türkçe cevap ver."
        if user_name:
            system_msg += f" Kullanıcının adı: {user_name}."
        messages.append({"role": "system", "content": system_msg})
        
        # Son konuşmaları ekle
        for role, content in recent:
            messages.append({"role": role, "content": content})
        
        # Yeni soruyu ekle
        messages.append({"role": "user", "content": user_message})
        
        # Groq'a sor
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.3,
            max_tokens=500
        )
        
        ai_reply = completion.choices[0].message.content
        
        # Cevabı kaydet
        memory.save_message(user_id, "assistant", ai_reply)
        
        await update.message.reply_text(ai_reply)
        
    except Exception as e:
        print(f"Hata: {e}", flush=True)
        await update.message.reply_text("Bir hata oluştu. Lütfen tekrar dener misiniz?")

def main():
    print("🚀 Bot başlatılıyor...", flush=True)
    
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Webhook
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
