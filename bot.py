import os
import json
import sqlite3
import logging
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('mcqs.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mcqs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT,
            option_a TEXT,
            option_b TEXT,
            option_c TEXT,
            option_d TEXT,
            correct_option INTEGER
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- DUMMY SERVER FOR RENDER PORT BINDING ---
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()

# --- BOT CODE ---
BOT_TOKEN = "8800485717:AAEt1QiGXpkUvYpt7_1fZm3shwefNHIzl4Q"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome! Bulk MCQs add karne ke liye Web App open karein ya `/quiz` bhej kar test start karein.")

async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_data = update.message.web_app_data.data
    mcq_list = json.loads(raw_data)
    total = len(mcq_list)
    
    option_map = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
    
    conn = sqlite3.connect('mcqs.db')
    cursor = conn.cursor()

    await update.message.reply_text(f"📥 Received {total} MCQs! Database me save aur Quiz Polls generate ho rahe hain...")

    for mcq in mcq_list:
        q = mcq['question']
        opts = mcq['options']
        ans_letter = mcq['answer'].strip().upper()
        correct_idx = option_map.get(ans_letter, 0)

        # 1. Database me save karein
        cursor.execute('''
            INSERT INTO mcqs (question, option_a, option_b, option_c, option_d, correct_option)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (q, opts[0], opts[1], opts[2], opts[3], correct_idx))

        # 2. Telegram Native Quiz Poll Send karein
        await context.bot.send_poll(
            chat_id=update.effective_chat.id,
            question=q,
            options=opts,
            type='quiz',
            correct_option_id=correct_idx,
            is_anonymous=False
        )
        await asyncio.sleep(0.5) # Rate limiting delay

    conn.commit()
    conn.close()

    await update.message.reply_text(f"✅ Successful! Sabhi {total} MCQs Quiz format me post ho gaye hain aur database me save ho chuke hain.")

async def send_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('mcqs.db')
    cursor = conn.cursor()
    cursor.execute('SELECT question, option_a, option_b, option_c, option_d, correct_option FROM mcqs ORDER BY RANDOM() LIMIT 1')
    row = cursor.fetchone()
    conn.close()

    if row:
        q, a, b, c, d, correct_idx = row
        await context.bot.send_poll(
            chat_id=update.effective_chat.id,
            question=q,
            options=[a, b, c, d],
            type='quiz',
            correct_option_id=correct_idx,
            is_anonymous=False
        )
    else:
        await update.message.reply_text("Abhi database me koi MCQs nahi hain. Pehle Web App se add karein!")

if __name__ == '__main__':
    Thread(target=run_dummy_server, daemon=True).start()
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("quiz", send_quiz))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
    
    app.run_polling()
