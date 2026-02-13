from supabase import create_client
from datetime import datetime
from config import SUPABASE_URL, SUPABASE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ================== KONU İŞLEMLERİ ==================

def save_topic(user_id, topic_id, title, reason=None):
    """Yeni konuyu kaydet"""
    try:
        data = {
            "user_id": str(user_id),
            "topic_id": topic_id,
            "title": title,
            "reason": reason
        }
        supabase.table("topics").insert(data).execute()
        print(f"✅ Konu kaydedildi: {title}", flush=True)
        return True
    except Exception as e:
        print(f"❌ Konu kayıt hatası: {e}", flush=True)
        return False

def get_topics(user_id, limit=20):
    """Kullanıcının tüm konularını getir (en yeniden eskiye)"""
    try:
        response = supabase.table("topics") \
            .select("topic_id, title, created_at, reason") \
            .eq("user_id", str(user_id)) \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()
        return response.data
    except Exception as e:
        print(f"❌ Konu listesi hatası: {e}", flush=True)
        return []

def get_topic_by_title(user_id, title):
    """Başlığa göre konu bul (tam eşleşme)"""
    try:
        response = supabase.table("topics") \
            .select("topic_id, title, created_at") \
            .eq("user_id", str(user_id)) \
            .eq("title", title) \
            .execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"❌ Konu arama hatası: {e}", flush=True)
        return None

# ================== MESAJ İŞLEMLERİ ==================

def save_message(user_id, topic_id, role, content):
    """Mesajı kaydet"""
    try:
        data = {
            "user_id": str(user_id),
            "topic_id": topic_id,
            "role": role,
            "content": content
        }
        supabase.table("messages").insert(data).execute()
        return True
    except Exception as e:
        print(f"❌ Mesaj kayıt hatası: {e}", flush=True)
        return False

def get_topic_messages(user_id, topic_id, limit=50):
    """Bir konudaki son mesajları getir"""
    try:
        response = supabase.table("messages") \
            .select("role, content, created_at") \
            .eq("user_id", str(user_id)) \
            .eq("topic_id", topic_id) \
            .order("created_at", desc=False) \
            .limit(limit) \
            .execute()
        return response.data
    except Exception as e:
        print(f"❌ Mesaj getirme hatası: {e}", flush=True)
        return []

# ================== ARAMA İŞLEMLERİ (YENİ!) ==================

def search_in_topic(user_id, topic_id, keyword):
    """Bir konu içinde kelime ara (PostgreSQL full-text search)"""
    try:
        # Basit versiyon - ILIKE ile (Türkçe karakter duyarsız)
        response = supabase.table("messages") \
            .select("content, created_at") \
            .eq("user_id", str(user_id)) \
            .eq("topic_id", topic_id) \
            .ilike("content", f"%{keyword}%") \
            .order("created_at", desc=True) \
            .limit(10) \
            .execute()
        return response.data
    except Exception as e:
        print(f"❌ Arama hatası: {e}", flush=True)
        return []

def search_all_topics(user_id, keyword):
    """Tüm konularda kelime ara"""
    try:
        response = supabase.table("messages") \
            .select("content, created_at, topic_id") \
            .eq("user_id", str(user_id)) \
            .ilike("content", f"%{keyword}%") \
            .order("created_at", desc=True) \
            .limit(20) \
            .execute()
        return response.data
    except Exception as e:
        print(f"❌ Genel arama hatası: {e}", flush=True)
        return []

def search_by_date(user_id, start_date, end_date, keyword=None):
    """Tarih aralığında ara (opsiyonel kelime)"""
    try:
        query = supabase.table("messages") \
            .select("content, created_at, topic_id") \
            .eq("user_id", str(user_id)) \
            .gte("created_at", start_date) \
            .lte("created_at", end_date)
        
        if keyword:
            query = query.ilike("content", f"%{keyword}%")
        
        response = query.order("created_at", desc=True).limit(50).execute()
        return response.data
    except Exception as e:
        print(f"❌ Tarihli arama hatası: {e}", flush=True)
        return []

# ================== KALICI BELLEK İŞLEMLERİ ==================

def save_memory(user_id, key, value):
    """Kalıcı belleği kaydet (ad, tercihler vs)"""
    try:
        # Önce var mı kontrol et
        response = supabase.table("memory") \
            .select("*") \
            .eq("user_id", str(user_id)) \
            .eq("key", key) \
            .execute()
        
        if response.data:
            # Güncelle
            supabase.table("memory") \
                .update({"value": value, "updated_at": "now()"}) \
                .eq("user_id", str(user_id)) \
                .eq("key", key) \
                .execute()
        else:
            # Yeni ekle
            data = {
                "user_id": str(user_id),
                "key": key,
                "value": value
            }
            supabase.table("memory").insert(data).execute()
        
        print(f"✅ Bellek kaydedildi: {key}={value}", flush=True)
        return True
    except Exception as e:
        print(f"❌ Bellek kayıt hatası: {e}", flush=True)
        return False

def load_memory(user_id):
    """Kullanıcının kalıcı bilgilerini yükle"""
    try:
        response = supabase.table("memory") \
            .select("key, value") \
            .eq("user_id", str(user_id)) \
            .execute()
        
        memory = {}
        for item in response.data:
            memory[item["key"]] = {"value": item["value"]}
        
        print(f"✅ Bellek yüklendi: {len(memory)} bilgi", flush=True)
        return memory
    except Exception as e:
        print(f"❌ Bellek yükleme hatası: {e}", flush=True)
        return {}
