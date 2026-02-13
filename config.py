import os
from groq import Groq

# Tokenlar ve sabitler
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
JSONBIN_ID = os.environ.get("JSONBIN_ID")
JSONBIN_SECRET = os.environ.get("JSONBIN_SECRET")
PORT = int(os.environ.get("PORT", 8080))
HOST = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "aissistan-v2.onrender.com")

# Groq client
client = Groq(api_key=GROQ_API_KEY)

# Kullanıcı oturumları (RAM'de tutulur)
user_sessions = {}
