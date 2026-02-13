from supabase import create_client
from datetime import datetime
from config import SUPABASE_URL, SUPABASE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

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
        return True
    except Exception as e:
        print(f"❌ Konu kayıt hatası: {e}", flush=True)
        return False

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

def save_memory(user_id, key, value):
    """Kalıcı belleği kaydet"""
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
        
        print(f"✅ Bellek kaydedildi: {user_id} - {key}: {value}", flush=True)
        return True
    except Exception as e:
        print(f"❌ Bellek kayıt hatası: {e}", flush=True)
        return False

def load_memory(user_id):
    """Kalıcı belleği yükle"""
    try:
        response = supabase.table("memory") \
            .select("key, value") \
            .eq("user_id", str(user_id)) \
            .execute()
        
        memory = {}
        for item in response.data:
            memory[item["key"]] = {"value": item["value"]}
        
        print(f"✅ Bellek yüklendi: {user_id} - {len(memory)} bilgi", flush=True)
        return memory
    except Exception as e:
        print(f"❌ Bellek yükleme hatası: {e}", flush=True)
        return {}

def get_recent_messages(user_id, topic_id, limit=10):
    """Son mesajları getir"""
    try:
        response = supabase.table("messages") \
            .select("role, content") \
            .eq("user_id", str(user_id)) \
            .eq("topic_id", topic_id) \
            .order("created_at") \
            .limit(limit) \
            .execute()
        
        return response.data
    except Exception as e:
        print(f"❌ Mesaj yükleme hatası: {e}", flush=True)
        return []

def get_recent_topics(user_id, limit=10):
    """Son konuları getir"""
    try:
        response = supabase.table("topics") \
            .select("topic_id, title, created_at, reason") \
            .eq("user_id", str(user_id)) \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()
        
        return response.data
    except Exception as e:
        print(f"❌ Konu yükleme hatası: {e}", flush=True)
        return []
