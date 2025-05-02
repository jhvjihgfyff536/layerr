import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import requests
import sqlite3
from datetime import datetime

# إعدادات البوت
TOKEN = '2049848765:AAHzQG4k219L9NgrC9D79uHJkxH8yKh1JGs'  # استبدل هذا بالتوكن الحقيقي
ADMIN_USER_ID = 1588300801
DEVELOPER_LINK = "https://t.me/T_7_P"  # رابط حساب المطور

bot = telebot.TeleBot(TOKEN)
user_links = {}

# تهيئة قاعدة البيانات
def init_db():
    conn = sqlite3.connect('downloads_log.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        action TEXT,
        title TEXT,
        timestamp TEXT
    )
    ''')
    conn.commit()
    conn.close()

init_db()

# تحميل فيديو من TikTok
def download_tiktok(url):
    api = "https://tikwm.com/api/"
    params = {"url": url}
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(api, params=params, headers=headers).json()

    if response.get("code") == 0 and response.get("data"):
        return {
            "video": response["data"].get("play"),
            "audio": response["data"].get("music"),
            "title": response["data"].get("title", "")
        }
    elif response.get("code") == -1:
        return {"error": "فشل في تحليل الرابط. يرجى التحقق من الرابط."}
    return None

# حفظ السجل
def log_download(user_id, username, action, url):
    conn = sqlite3.connect('downloads_log.db')
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
    INSERT INTO logs (user_id, username, action, title, timestamp)
    VALUES (?, ?, ?, ?, ?)
    ''', (user_id, username, action, url, timestamp))
    conn.commit()
    conn.close()

# لوحة تحكم الأدمن
def admin_panel(message):
    if message.chat.id == ADMIN_USER_ID:
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("عرض السجل", callback_data="view_logs"),
            InlineKeyboardButton("مسح السجل", callback_data="clear_logs")
        )
        bot.send_message(message.chat.id, "مرحبًا بك في لوحة التحكم:", reply_markup=markup)
    else:
        bot.reply_to(message, "أنت لست الأدمن!")

# التعامل مع روابط تيك توك
@bot.message_handler(func=lambda m: any(x in m.text for x in ["tiktok.com", "vm.tiktok.com", "vt.tiktok.com"]))
def handle_tiktok(message):
    url = message.text.strip()
    data = download_tiktok(url)

    if data and "error" in data:
        bot.reply_to(message, data["error"])
        return

    if not data or not data.get("video"):
        bot.reply_to(message, "فشل في استخراج البيانات. تأكد من أن الرابط صحيح.")
        return

    user_links[message.chat.id] = url

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("تحميل الفيديو", callback_data="download_video"),
        InlineKeyboardButton("تحميل الصوت", callback_data="download_audio")
    )
    bot.send_message(message.chat.id, "اختر ما تريد تحميله:", reply_markup=markup)

# تحميل فيديو أو صوت
@bot.callback_query_handler(func=lambda call: call.data in ["download_video", "download_audio"])
def callback_query(call: CallbackQuery):
    url = user_links.get(call.message.chat.id)
    if not url:
        bot.answer_callback_query(call.id, "لم يتم العثور على الرابط.")
        return

    data = download_tiktok(url)
    if data:
        if "error" in data:
            bot.answer_callback_query(call.id, data["error"])
            return

        dev_markup = InlineKeyboardMarkup()
        dev_markup.add(InlineKeyboardButton("T_7_P", url=DEVELOPER_LINK))

        if call.data == "download_video" and data["video"]:
            bot.send_chat_action(call.message.chat.id, "upload_video")
            bot.send_video(call.message.chat.id, data["video"], caption="تم تحميل الفيديو.", reply_markup=dev_markup)
            log_download(call.message.chat.id, call.from_user.username, "فيديو", url)
        elif call.data == "download_audio" and data["audio"]:
            bot.send_chat_action(call.message.chat.id, "upload_audio")
            bot.send_audio(call.message.chat.id, data["audio"], caption="تم تحميل الصوت.", reply_markup=dev_markup)
            log_download(call.message.chat.id, call.from_user.username, "صوت", url)
        else:
            bot.answer_callback_query(call.id, "لا يوجد فيديو أو صوت في هذا الرابط.")
    else:
        bot.answer_callback_query(call.id, "فشل في استخراج البيانات.")

# عرض السجل أو حذفه
@bot.callback_query_handler(func=lambda call: call.data in ["view_logs", "clear_logs"])
def admin_actions(call: CallbackQuery):
    if call.message.chat.id == ADMIN_USER_ID:
        conn = sqlite3.connect('downloads_log.db')
        cursor = conn.cursor()

        if call.data == "view_logs":
            cursor.execute('SELECT * FROM logs ORDER BY timestamp DESC LIMIT 10')
            logs = cursor.fetchall()
            if logs:
                logs_text = "السجل الأخير:\n\n"
                for log in logs:
                    logs_text += f"{log[5]} | المستخدم: {log[2]} ({log[1]}) | نوع: {log[3]} | الرابط: {log[4]}\n"
                bot.send_message(call.message.chat.id, logs_text)
            else:
                bot.send_message(call.message.chat.id, "لا توجد سجلات.")
        elif call.data == "clear_logs":
            cursor.execute('DELETE FROM logs')
            conn.commit()
            bot.send_message(call.message.chat.id, "تم مسح السجلات.")
        conn.close()
    else:
        bot.answer_callback_query(call.id, "أنت لست الأدمن!")

# /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    if message.chat.id == ADMIN_USER_ID:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("لوحة تحكم الأدمن", callback_data="admin_panel"))
        bot.send_message(message.chat.id, "مرحبًا بك في البوت! اختر من القائمة:", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "مرحبًا! أرسل رابط تيك توك لتحميل الفيديو أو الصوت.")

# عرض لوحة التحكم
@bot.callback_query_handler(func=lambda call: call.data == "admin_panel")
def admin_panel_action(call):
    admin_panel(call.message)

# بدء البوت
print("البوت يعمل الآن...")
bot.infinity_polling()