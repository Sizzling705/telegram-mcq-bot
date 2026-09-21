import os
import json
import logging
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Dummy web server to satisfy Render's port check
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()

# Your Bot Father Token
BOT_TOKEN = "8800485717:AAEt1QiGXpkUvYpt7_1fZm3shwefNHIzl4Q"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome! Bulk MCQs add karne ke liye Web App open karein.")

async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_data = update.message.web_app_data.data
    mcq_list = json.loads(raw_data)
    total = len(mcq_list)
    
    for index, mcq in enumerate(mcq_list, start=1):
        print(f"[{index}] Q: {mcq['question']} | Ans: {mcq['answer']}")

    await update.message.reply_text(f"✅ Successful! Total {total} MCQs Receive ho gaye hain.")

if __name__ == '__main__':
    # Start dummy web server in background thread
    Thread(target=run_dummy_server, daemon=True).start()
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
    
    app.run_polling()
