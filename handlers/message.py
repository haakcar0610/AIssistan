from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime

from config import user_sessions, client
from memory.supabase import (
    load_memory, save_message, get_topic_messages,
    search_in_topic, search_all_topics
)
from memory.context import (
    yeni_konu_olustur, isim_kaydet, komut_kontrol, konu_yukle
)
from utils.helpers import konu_degisti_mi
import asyncio

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    user_id = str(update.effective_user.id)
    
    # "." MESAJINI SİL
    if user_message == ".":
        try:
            await update.message.delete()
            print(f"✅ Silindi: {update.message.message_id}", flush=True)
            return
        except:
            pass
    
    # Kullanıcı oturumunu başlat
    if user_id not in user_sessions:
        from memory.supabase import load_memory
        kalici_bellek = load_memory(user_id)
        
        user_sessions[user_id] = {
            "konular": [],
            "bellek": kalici_bellek,
            "aktif_konu": None,
            "son_aktivite": datetime.now(),
            "mesaj_gecmisi": []
        }
    
    session = user_sessions[user_id]
    simdi = datetime.now()
    
    # ========== ÖZEL KOMUT KONTROLÜ ==========
    komut_tip, komut_param = komut_kontrol(user_message)
    
    # 1. KONU YÜKLEME ("bana ... getir")
    if komut_tip == "konu_yukle":
        baslik = komut_param
        basari, sonuc = konu_yukle(user_id, baslik)
        if basari:
            # Konudaki mesajları yükle
            messages = get_topic_messages(user_id, sonuc, limit=30)
            # Mesajları session'a ekle (ileride kullanmak için)
            for konu in session["konular"]:
                if konu["id"] == sonuc:
                    konu["mesajlar"] = messages
                    break
            await update.message.reply_text(f"📂 '{baslik}' konusu yüklendi. Kaldığın yerden devam edebilirsin.")
        else:
            await update.message.reply_text(f"❌ {sonuc}")
        return
    
    # 2. KONU İÇİNDE ARAMA ("ara konu: kelime")
    if komut_tip == "ara_konu":
        konu_adi, kelime = komut_param
        # Önce konuyu bul
        from memory.supabase import get_topic_by_title
        konu = get_topic_by_title(user_id, konu_adi)
        if konu:
            results = search_in_topic(user_id, konu["topic_id"], kelime)
            if results:
                cevap = f"🔍 '{konu_adi}' konusunda '{kelime}' arama sonuçları:\n\n"
                for r in results[:5]:
                    tarih = r["created_at"][:16].replace("T", " ")
                    cevap += f"📌 {tarih}\n> {r['content'][:200]}...\n\n"
                await update.message.reply_text(cevap)
            else:
                await update.message.reply_text(f"❌ '{kelime}' ile ilgili sonuç bulunamadı.")
        else:
            await update.message.reply_text(f"❌ '{konu_adi}' konusu bulunamadı.")
        return
    
    # 3. GENEL ARAMA ("kelime ara")
    if komut_tip == "ara_genel":
        kelime = komut_param
        results = search_all_topics(user_id, kelime)
        if results:
            cevap = f"🔍 Tüm konularda '{kelime}' arama sonuçları:\n\n"
            for r in results[:5]:
                tarih = r["created_at"][:16].replace("T", " ")
                cevap += f"📌 {tarih} (konu: {r.get('topic_id', '?')})\n> {r['content'][:150]}...\n\n"
            await update.message.reply_text(cevap)
        else:
            await update.message.reply_text(f"❌ '{kelime}' ile ilgili sonuç bulunamadı.")
        return
    
    # 4. YENİ KONU ("yeni konu: başlık")
    if komut_tip == "yeni_konu":
        baslik = komut_param
        yeni_konu_olustur(user_id, f"yeni konu: {baslik}", "🆕 Manuel")
        await update.message.reply_text(f"🆕 Yeni konu açıldı: '{baslik}'. Artık bu konuda konuşabiliriz.")
        return
    
    # ========== NORMAL MESAJ İŞLEME ==========
    
    # İsim kaydetme kontrolü
    isim_kaydet(user_id, user_message, session)
    
    # Eğer aktif konu yoksa, yeni konu aç
    if not session["aktif_konu"]:
        yeni_konu_olustur(user_id, user_message, "🆕 İlk konu")
    
    # Konu değişimi kontrolü (sadece aktif konu varsa)
    if session["aktif_konu"]:
        degisti, sebep = konu_degisti_mi(
            user_message, 
            session["mesaj_gecmisi"],
            session["son_aktivite"]
        )
        
        if degisti:
            yeni_konu_olustur(user_id, user_message, sebep)
    
    # Mesajı SUPABASE'E KAYDET
    for konu in session["konular"]:
        if konu["id"] == session["aktif_konu"]:
            konu["mesajlar"].append({"role": "user", "content": user_message})
            save_message(user_id, konu["id"], "user", user_message)
            break
    
    # Geçmişe ekle (konu değişimi için)
    if not user_message.startswith("/"):
        session["mesaj_gecmisi"].append(user_message)
        if len(session["mesaj_gecmisi"]) > 20:
            session["mesaj_gecmisi"].pop(0)
    
    session["son_aktivite"] = simdi
    
    # ========== AI CEVAP ÜRET ==========
    await update.message.chat.send_action(action="typing")
    
    try:
        # Aktif konunun mesajlarını al
        aktif_mesajlar = []
        aktif_konu_id = session["aktif_konu"]
        
        for konu in session["konular"]:
            if konu["id"] == aktif_konu_id:
                aktif_mesajlar = konu["mesajlar"][-30:]  # Son 30 mesaj
                break
        
        # KALICI BELLEĞİ HAZIRLA
        bellek_str = ""
        if session.get("bellek"):
            bellek_str = "Kullanıcı hakkında bildiklerin (ASLA UNUTMA): "
            for key, value in session["bellek"].items():
                if isinstance(value, dict) and "value" in value:
                    bellek_str += f"{key}: {value['value']}, "
                elif isinstance(value, str):
                    bellek_str += f"{key}: {value}, "
        
        # SYSTEM PROMPT
        mesaj_gecmisi = [
            {
                "role": "system", 
                "content": (
                    "Sen sadece Türkçe konuşan bir AI asistanısın. "
                    "Kesinlikle İngilizce veya yabancı kelime kullanma. "
                    "Kullanıcının sorusunun ana amacını anla, ona odaklan. "
                    "Gereksiz giriş cümleleri kurma, doğrudan ve net cevap ver.\n\n"
                    f"{bellek_str}\n\n"
                    "ÖNCEKİ KONUŞMA:"
                )
            }
        ]
        
        # Geçmiş mesajları ekle
        for m in aktif_mesajlar:
            mesaj_gecmisi.append(m)
        
        # GROQ API ÇAĞRISI
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=mesaj_gecmisi,
            temperature=0.3,
            max_tokens=500
        )
        
        ai_reply = completion.choices[0].message.content
        
        # Cevabı kaydet
        for konu in session["konular"]:
            if konu["id"] == aktif_konu_id:
                konu["mesajlar"].append({"role": "assistant", "content": ai_reply})
                save_message(user_id, konu["id"], "assistant", ai_reply)
                break
        
    except Exception as e:
        ai_reply = f"Bir hata oluştu. Lütfen tekrar dener misiniz?"
        print(f"❌ GROQ HATASI: {e}", flush=True)
    
    await update.message.reply_text(ai_reply)
