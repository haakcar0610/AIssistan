import os
import asyncio
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

from memory import Memory

# Tokenlar DOĞRUDAN environment'tan alınıyor
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
PORT = int(os.environ.get("PORT", 8080))
HOST = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "localhost")

# Kontrol
if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    raise ValueError("TELEGRAM_TOKEN ve GROQ_API_KEY environment variable'ları tanımlanmalı!")

# Groq client
client = Groq(api_key=GROQ_API_KEY)

# Hafıza sistemi
memory = Memory()

# ... (diğer fonksiyonlar aynen kalacak)
