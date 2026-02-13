from telegram import Update
from telegram.ext import ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot başlangıç mesajı"""
    await update.message.reply_text(
        "👋 Merhaba! Ben AI asistanınız.\n\n"
        "📌 **Komutlar:**\n"
        "• /konular - Geçmiş konularınızı listeler\n"
        "• /yeni - Yeni konu başlatır\n\n"
        "🗣️ **Konuşma Özellikleri:**\n"
        "• 'bana [konu] getir' - Eski bir konuyu yükler\n"
        "• 'ara [konu]: [kelime]' - Konu içinde arama yapar\n"
        "• '[kelime] ara' - Tüm konularda arama yapar\n"
        "• 'yeni konu: [başlık]' - İstediğiniz başlıkla konu açar\n\n"
        "🧠 Adınızı, tercihlerinizi ve tüm konuşmalarınızı hatırlarım."
    )
