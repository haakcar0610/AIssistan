from telegram import Update
from telegram.ext import ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Merhaba! Ben AI asistanınız. Size Türkçe yardımcı olabilirim.\n\n"
        "📌 /konular ile geçmiş konuşmalarınızı görebilirsiniz.\n"
        "🆕 /yeni ile yeni bir konu başlatabilirsiniz.\n\n"
        "Adınızı, tercihlerinizi ve önemli bilgileri hiç unutmam. 🧠"
    )
