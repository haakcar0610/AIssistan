import requests
import json
from datetime import datetime
from config import JSONBIN_ID, JSONBIN_SECRET

def save_conversation(user_id, konular):
    """Tüm konuşmaları JSONBin'e kaydet"""
    if not konular:
        return False
        
    url = f"https://api.jsonbin.io/v3/b/{JSONBIN_ID}"
    headers = {
        "Content-Type": "application/json",
        "X-Master-Key": JSONBIN_SECRET
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json().get("record", {})
        data[str(user_id)] = konular[-20:]
        requests.put(url, headers=headers, json=data, timeout=5)
        print(f"✅ JSONBin kaydedildi: {user_id} - {len(konular)} konu", flush=True)
        return True
    except Exception as e:
        print(f"❌ JSONBin kayıt hatası: {e}", flush=True)
        return False

def load_conversation(user_id):
    """Kullanıcının geçmiş konuşmalarını yükle"""
    url = f"https://api.jsonbin.io/v3/b/{JSONBIN_ID}"
    headers = {"X-Master-Key": JSONBIN_SECRET}
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json().get("record", {})
        konular = data.get(str(user_id), [])
        print(f"✅ JSONBin yüklendi: {user_id} - {len(konular)} konu", flush=True)
        return konular
    except Exception as e:
        print(f"❌ JSONBin yükleme hatası: {e}", flush=True)
        return []

def save_memory(user_id, key, value):
    """Kullanıcıya ait kalıcı bilgileri kaydet"""
    url = f"https://api.jsonbin.io/v3/b/{JSONBIN_ID}"
    headers = {
        "Content-Type": "application/json",
        "X-Master-Key": JSONBIN_SECRET
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json().get("record", {})
        
        if "memory" not in data:
            data["memory"] = {}
        if str(user_id) not in data["memory"]:
            data["memory"][str(user_id)] = {}
            
        data["memory"][str(user_id)][key] = {
            "value": value,
            "timestamp": datetime.now().isoformat()
        }
        
        requests.put(url, headers=headers, json=data, timeout=5)
        print(f"✅ Bellek kaydedildi: {user_id} - {key}: {value}", flush=True)
        return True
    except Exception as e:
        print(f"❌ Bellek kayıt hatası: {e}", flush=True)
        return False

def load_memory(user_id):
    """Kullanıcının kalıcı bilgilerini yükle"""
    url = f"https://api.jsonbin.io/v3/b/{JSONBIN_ID}"
    headers = {"X-Master-Key": JSONBIN_SECRET}
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json().get("record", {})
        memory = data.get("memory", {}).get(str(user_id), {})
        print(f"✅ Bellek yüklendi: {user_id} - {len(memory)} bilgi", flush=True)
        return memory
    except Exception as e:
        print(f"❌ Bellek yükleme hatası: {e}", flush=True)
        return {}
