import os
import asyncio
import requests
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Tokenlar
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
HUGGINGFACE_TOKEN = os.environ.get("HUGGINGFACE_TOKEN")
PORT = int(os.environ.get("PORT", 8080))
HOST = os.environ.get("RENDER_EXTERNAL_HOSTNAME")

# Başlangıç komutu
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Merhaba! Ben AI asistanınız. Bana istediğiniz soruyu sorabilirsiniz.")

# Mesajları işle
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    
    # "." mesajını görmezden gel ve sil
    if user_message == ".":
        try:
            await update.message.delete()
        except:
            pass
        return
    
    # Kullanıcıya "yazıyor..." göster
    await update.message.chat.send_action(action="typing")
    
    # AI'a sor
    try:
        response = requests.post(
            "https://api-inference.huggingface.co/models/Qwen/Qwen2.5-Coder-32B-Instruct",
            headers={"Authorization": f"Bearer {HUGGINGFACE_TOKEN}"},
            json={
                "inputs": f"<|im_start|>user\n{user_message}<|im_end|>\n<|im_start|>assistant\n",
                "parameters": {
                    "max_new_tokens": 500,
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "do_sample": True
                }
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                ai_reply = result[0].get("generated_text", "")
                # Cevabı temizle
                ai_reply = ai_reply.split("<|im_start|>assistant\n")[-1].strip()
            else:
                ai_reply = "Üzgünüm, cevap üretemedim."
        else:
            ai_reply = f"AI servisi şu an yanıt vermiyor. (Hata: {response.status_code})"
            
    except Exception as e:
        ai_reply = f"Bir hata oluştu: {str(e)}"
    
    await update.message.reply_text(ai_reply)

# Ana fonksiyon
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
