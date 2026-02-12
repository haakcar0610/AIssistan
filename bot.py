import os
import asyncio
from huggingface_hub import InferenceClient
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Tokenlar
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
HUGGINGFACE_TOKEN = os.environ.get("HUGGINGFACE_TOKEN")
PORT = int(os.environ.get("PORT", 8080))
HOST = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "aissistan.onrender.com")

# Inference Client - YENİ MİMARİ
client = InferenceClient(
    provider="hf-inference",
    token=HUGGINGFACE_TOKEN
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Merhaba! Ben AI asistanınız.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    
    # "." mesajını sil
    if user_message == ".":
        try:
            await update.message.delete()
        except:
            pass
        return
    
    await update.message.chat.send_action(action="typing")
    
    try:
        # YENİ: Hugging Face'in yeni InferenceClient'ı ile
        messages = [
            {
                "role": "user",
                "content": f"Sadece Türkçe cevap ver. Soru: {user_message}"
            }
        ]
        
        response = client.chat.completions.create(
            model="CohereForAI/aya-expanse-8b",
            messages=messages,
            max_tokens=500,
            temperature=0.7
        )
        
        ai_reply = response.choices[0].message.content
        
    except Exception as e:
        ai_reply = f"Hata oluştu: {str(e)}"
        # Hata log'da görünsün diye print ekle
        print(f"HATA: {e}")
    
    await update.message.reply_text(ai_reply)

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    webhook_url = f"https://{HOST}/{TELEGRAM_TOKEN}"
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(app.bot.set_webhook(url=webhook_url))
    
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TELEGRAM_TOKEN,
        webhook_url=webhook_url
    )

if __name__ == "__main__":
    main()
