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
def get_db_connection():
    return sqlite3.connect('mcqs.db')

def init_db():
    conn = get_db_connection()
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
    await update.message.reply_text("👋 Welcome! Bulk MCQs add karne ke liye Web App open karein, `/count` se total questions dekhein ya `/quiz` se test lein.")

async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        raw_data = update.message.web_app_data.data
        logging.info(f"RAW DATA: {raw_data}")
        
        mcq_list = json.loads(raw_data)
        total = len(mcq_list)
        
        option_map = {'A': 0, 'B': 1, 'C': 2, 'D': 3, '1': 0, '2': 1, '3': 2, '4': 3}
        
        conn = get_db_connection()
        cursor = conn.cursor()

        await update.message.reply_text(f"📥 Received {total} MCQs! Processing & Saving...")

        saved_count = 0
        for mcq in mcq_list:
            # Flexible field extraction (handles compressed keys or full keys)
            q = mcq.get('q') or mcq.get('question')
            opts = mcq.get('o') or mcq.get('options')
            ans_raw = mcq.get('a') or mcq.get('answer')
            
            if not q or not opts or len(opts) < 4:
                continue

            ans_str = str(ans_raw).strip().upper() if ans_raw is not None else 'A'
            correct_idx = option_map.get(ans_str, 0)

            # 1. Database me Save
            cursor.execute('''
                INSERT INTO mcqs (question, option_a, option_b, option_c, option_d, correct_option)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (str(q), str(opts[0]), str(opts[1]), str(opts[2]), str(opts[3]), correct_idx))
            saved_count += 1

            # 2. Anonymous Quiz Poll Send
            try:
                await context.bot.send_poll(
                    chat_id=update.effective_chat.id,
                    question=str(q)[:300],  # Telegram max length guard
                    options=[str(opt)[:100] for opt in opts[:4]],
                    type='quiz',
                    correct_option_id=correct_idx,
                    is_anonymous=True
                )
            except Exception as poll_err:
                logging.error(f"Poll Error: {poll_err}")
                await asyncio.sleep(2)

            await asyncio.sleep(1.2) # Rate limit safety

        conn.commit()
        conn.close()

        # Success message
        await update.message.reply_text(f"✅ Successful! **{saved_count}** MCQs Database me save aur post ho gaye hain.", parse_mode="Markdown")

    except Exception as e:
        logging.error(f"Error in handle_webapp_data: {e}")
        await update.message.reply_text(f"❌ Error aaya: {e}")

async def count_mcqs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM mcqs')
    total = cursor.fetchone()[0]
    conn.close()

    await update.message.reply_text(f"📊 **Database Status:**\nTotal uploaded MCQs: **{total}**", parse_mode="Markdown")

async def send_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db_connection()
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
            is_anonymous=True
        )
    else:
        await update.message.reply_text("Abhi database me koi MCQs nahi hain. Pehle Web App se add karein!")

if __name__ == '__main__':
    Thread(target=run_dummy_server, daemon=True).start()
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("quiz", send_quiz))
    app.add_handler(CommandHandler("count", count_mcqs))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
    
    app.run_polling()
