import os
from groq import Groq

# Tokenlar ve sabitler
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
PORT = int(os.environ.get("PORT", 8080))
HOST = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "aissistan-v2.onrender.com")

# Groq client
client = Groq(api_key=GROQ_API_KEY)

# Kullanıcı oturumları (RAM'de tutulur)
# Her kullanıcı için: {
#   "konular": [],           # Tüm konular (Supabase'den yüklenir)
#   "aktif_konu": None,      # Şu anki konu ID'si
#   "son_aktivite": None,    # Son mesaj zamanı
#   "mesaj_gecmisi": [],     # Son 5 mesaj (konu değişimi için)
#   "bellek": {}             # Kalıcı bilgiler (Supabase'den yüklenir)
# }
user_sessions = {}
