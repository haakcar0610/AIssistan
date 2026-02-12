import os
import asyncio
from groq import Groq
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Tokenlar
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
PORT = int(os.environ.get("PORT", 8080))
HOST = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "aissistan.onrender.com")

# Groq client
client = Groq(api_key=GROQ_API_KEY)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Merhaba! Ben AI asistanınız. Size Türkçe yardımcı olabilirim.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    
    # "." mesajını sil - GÜÇLENDİRİLMİŞ VERSİYON
    if user_message == ".":
        try:
            await update.message.delete()
            print(f"✅ '.' mesajı silindi - ID: {update.message.message_id}")
        except Exception as e:
            print(f"❌ '.' mesajı silinemedi - Hata: {e}")
            # Alternatif silme yöntemi
            try:
                await context.bot.delete_message(
                    chat_id=update.message.chat_id,
                    message_id=update.message.message_id
                )
                print(f"✅ Alternatif silme başarılı - ID: {update.message.message_id}")
            except Exception as e2:
                print(f"❌ Alternatif silme de başarısız: {e2}")
        return
    
    await update.message.chat.send_action(action="typing")
    
    try:
        # Groq ile Llama 3.3 70B
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Sen Türkçe konuşan bir AI asistanısın. Sadece Türkçe cevap ver, asla İngilizce kelime kullanma. Kullanıcıya anlayacağı dilden, net ve doğal cevaplar ver."},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=500,
            top_p=0.95
        )
        
        ai_reply = completion.choices[0].message.content
        
    except Exception as e:
        ai_reply = f"Hata oluştu: {str(e)}"
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
