import os
import time
import threading
from flask import Flask
import telebot

# استدعاء الإعدادات وقاعدة البيانات والواجهات
from config import BOT_TOKEN
from database import init_pool, init_db, get_db, release_db
from keyboards import get_admin_main_keyboard, get_student_main_keyboard
from utils import check_subscription, send_sub_required_msg, is_admin, safe_answer_callback

# استدعاء مسارات البوت (Handlers) من المجلد الذي أنشأناه
from handlers.student_handler import register_student_handlers
from handlers.exam_handler import register_exam_handlers
from handlers.admin_handler import register_admin_handlers

# ==================== تهيئة البوت والخادم ====================
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

@app.route("/")
def home():
    return "Law Faculty Platform is running smoothly! ⚖️"

# ==================== أوامر البداية (Start) ====================
@bot.message_handler(commands=["start"])
def start_cmd(message):
    user_id = message.from_user.id
    conn = get_db()
    try:
        cur = conn.cursor()
        # إضافة المستخدم أو تحديث بياناته في قاعدة البيانات الجديدة
        cur.execute("""INSERT INTO users (user_id, username, first_name) VALUES (%s, %s, %s) ON CONFLICT (user_id) DO UPDATE SET username=%s, first_name=%s""", (user_id, message.from_user.username, message.from_user.first_name, message.from_user.username, message.from_user.first_name))
        conn.commit()
        cur.close()
    finally:
        release_db(conn)

    # فحص الاشتراك الإجباري
    if not check_subscription(bot, user_id):
        return send_sub_required_msg(bot, message.chat.id)

    bot.send_chat_action(message.chat.id, 'typing')
    time.sleep(0.5)

    if is_admin(user_id):
        bot.send_message(message.chat.id, "أهلاً بك يا أدمن 👑\nتم تفعيل لوحة التحكم الشاملة.", reply_markup=get_admin_main_keyboard())
    else:
        bot.send_message(message.chat.id, f"أهلاً بك يا {message.from_user.first_name} في منصة كلية الحقوق! ⚖️\nحدد وجهتك من القائمة أدناه للبدء 🌟", reply_markup=get_student_main_keyboard())

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def handle_check_sub(call):
    user_id = call.from_user.id
    if check_subscription(bot, user_id):
        safe_answer_callback(bot, call.id, "✅ شكراً لانضمامك إلينا!")
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception: pass
        
        bot.send_chat_action(call.message.chat.id, 'typing')
        bot.send_message(call.message.chat.id, "✅ **تم التحقق بنجاح!**\nأهلاً بك في منصة كلية الحقوق ⚖️", parse_mode="Markdown", reply_markup=get_student_main_keyboard())
    else:
        safe_answer_callback(bot, call.id, "❌ لم تشترك بعد! يرجى الاشتراك في القناة أولاً.", show_alert=True)

# ==================== تسجيل مسارات البوت (Handlers) ====================
# نقوم بتمرير متغير البوت (bot) إلى الملفات الأخرى لتعمل كأنها ملف واحد
register_admin_handlers(bot)
register_student_handlers(bot)
register_exam_handlers(bot)

# ==================== نقطة الإطلاق التلقائية ====================
def start_bot_and_db():
    try:
        print("🔄 جاري الاتصال بقاعدة البيانات...")
        init_pool()
        init_db()
        
        # وضع قائمة جانبية (Menu) لزر البداية
        bot.set_my_commands([
            telebot.types.BotCommand("start", "🚀 بدء أو إعادة تشغيل المنصة")
        ])
        
        print("✅ قاعدة البيانات جاهزة. جاري تشغيل البوت...")
        bot_thread = threading.Thread(target=lambda: bot.infinity_polling(skip_pending=True), daemon=True)
        bot_thread.start()
        print("🚀 البوت يعمل الآن بنجاح!")
    except Exception as e:
        print(f"❌ خطأ أثناء بدء التشغيل: {e}")

# تشغيل النظام
start_bot_and_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
