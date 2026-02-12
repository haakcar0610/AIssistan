import os
import asyncio
from groq import Groq
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Tokenlar
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
PORT = int(os.environ.get("PORT", 8080))
HOST = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "aissistan-v2.onrender.com")

# Groq client
client = Groq(api_key=GROQ_API_KEY)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Merhaba! Ben AI asistanınız. Size Türkçe yardımcı olabilirim.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    
    # "." MESAJINI SİL - KESİN ÇÖZÜM
    if user_message == ".":
        try:
            # 1. YÖNTEM: Direkt sil
            await update.message.delete()
            print(f"✅ Silindi (1.yöntem): {update.message.message_id}")
            return
        except Exception as e:
            print(f"❌ 1.yöntem hatası: {e}")
            
        try:
            # 2. YÖNTEM: Bot üzerinden sil
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=update.message.message_id
            )
            print(f"✅ Silindi (2.yöntem): {update.message.message_id}")
            return
        except Exception as e:
            print(f"❌ 2.yöntem hatası: {e}")
            
        try:
            # 3. YÖNTEM: Botun kendi mesajını da sil (arka arkaya)
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=update.message.message_id + 1
            )
        except:
            pass
        
        print("❌ TÜM SİLME YÖNTEMLERİ BAŞARISIZ!")
        return
    
    # Normal mesaj - AI cevap ver
    await update.message.chat.send_action(action="typing")
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Sen Türkçe konuşan bir AI asistanısın. Sadece Türkçe cevap ver."},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        ai_reply = completion.choices[0].message.content
        
    except Exception as e:
        ai_reply = f"Hata: {str(e)}"
        print(f"GROQ HATASI: {e}")
    
    await update.message.reply_text(ai_reply)

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Webhook kurulumu
    webhook_url = f"https://{HOST}/{TELEGRAM_TOKEN}"
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(app.bot.set_webhook(url=webhook_url))
    print(f"✅ Webhook set to {webhook_url}")
    
    # Webhook'u başlat
    print(f"🚀 Starting webhook on port {PORT}...")
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TELEGRAM_TOKEN,
        webhook_url=webhook_url
    )

if __name__ == "__main__":
    main()
