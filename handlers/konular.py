from telegram import Update
from telegram.ext import ContextTypes
from memory.supabase import get_topics, get_topic_messages
from config import user_sessions

async def konular(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Geçmiş konuları listele"""
    user_id = str(update.effective_user.id)
    
    konular = get_topics(user_id, limit=20)
    
    if not konular:
        await update.message.reply_text("📭 Henüz hiç konuşmanız yok.")
        return
    
    aktif_konu_id = None
    if user_id in user_sessions:
        aktif_konu_id = user_sessions[user_id].get("aktif_konu")
    
    mesaj = "📋 **Son Konularınız:**\n\n"
    
    for konu in konular:
        topic_id = konu["topic_id"]
        tarih = konu["created_at"][:16].replace("T", " ").replace("-", ".")
        aktif = "✅ " if aktif_konu_id == topic_id else "   "
        baslik = konu["title"][:40] + "..." if len(konu["title"]) > 40 else konu["title"]
        sebep_str = f" ({konu['reason']})" if konu.get("reason") else ""
        
        mesaj += f"{aktif}• **{baslik}**{sebep_str}\n"
        mesaj += f"  🕐 {tarih}\n\n"
    
    mesaj += "\n💡 `bana [konu] getir` veya `ara [konu]: kelime`"
    
    await update.message.reply_text(mesaj)
