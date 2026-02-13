from telegram import Update
from telegram.ext import ContextTypes
from config import user_sessions

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
