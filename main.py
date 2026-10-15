import os
import time
import threading
from flask import Flask
import telebot
from apscheduler.schedulers.background import BackgroundScheduler

# استدعاء الإعدادات وقاعدة البيانات والواجهات
from config import BOT_TOKEN
from database import init_pool, init_db, get_db, release_db
from keyboards import get_admin_main_keyboard, get_student_main_keyboard
from utils import check_subscription, send_sub_required_msg, is_admin, safe_answer_callback, md

# استدعاء مسارات البوت (Handlers)
from handlers.student_handler import register_student_handlers
from handlers.exam_handler import register_exam_handlers
from handlers.admin_handler import register_admin_handlers
from handlers.ai_handler import register_ai_handlers

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
        cur.execute("""INSERT INTO users (user_id, username, first_name) VALUES (%s, %s, %s) ON CONFLICT (user_id) DO UPDATE SET username=%s, first_name=%s""", (user_id, message.from_user.username, message.from_user.first_name, message.from_user.username, message.from_user.first_name))
        conn.commit()
        cur.close()
    finally:
        release_db(conn)

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
register_admin_handlers(bot)
register_student_handlers(bot)
register_exam_handlers(bot)
register_ai_handlers(bot)

# ==================== محرك تحدي اليوم الآلي ====================
def send_daily_challenges():
    print("🎯 بدء إرسال تحدي اليوم...")
    conn = get_db()
    try:
        cur = conn.cursor()
        # جلب السنوات والفصول التي اختارها الطلاب في الإعدادات
        cur.execute("SELECT DISTINCT academic_year, academic_semester FROM users WHERE academic_year > 0 AND academic_semester > 0")
        groups = cur.fetchall()
        
        for year, sem in groups:
            # اختيار سؤال عشوائي واحد لهذه السنة والفصل
            cur.execute("SELECT id, subject, question_text, option_a, option_b, option_c, option_d FROM questions WHERE year=%s AND semester=%s ORDER BY RANDOM() LIMIT 1", (year, sem))
            q = cur.fetchone()
            if not q: continue
            
            q_id, sub, text, opt_a, opt_b, opt_c, opt_d = q
            options = [opt_a, opt_b, opt_c, opt_d]
            
            # تصميم رسالة التحدي
            msg_text = f"🎯 **تحدي اليوم الآلي!**\n📖 المادة: {md(sub)}\n\nركز جيداً، الإجابة الصحيحة تمنحك **20 نقطة XP** وترفع مستواك ✨\n\n❓ {md(text)}"
            markup = telebot.types.InlineKeyboardMarkup()
            for i, letter in enumerate(['أ', 'ب', 'ج', 'د']):
                if i < len(options) and options[i]:
                    markup.add(telebot.types.InlineKeyboardButton(f"{letter}) {md(options[i])}", callback_data=f"dc_ans_{q_id}_{letter}"))
            
            # إرسال السؤال لطلاب هذه الدفعة فقط
            cur.execute("SELECT user_id FROM users WHERE academic_year=%s AND academic_semester=%s", (year, sem))
            students = cur.fetchall()
            
            for (u_id,) in students:
                try:
                    bot.send_message(u_id, msg_text, parse_mode="Markdown", reply_markup=markup)
                    time.sleep(0.05) # تأخير بسيط لتجنب حظر تيليجرام للإرسال الجماعي
                except Exception: pass
        cur.close()
        print("✅ تم إرسال جميع التحديات بنجاح.")
    except Exception as e:
        print(f"❌ خطأ في إرسال التحديات: {e}")
    finally: release_db(conn)

# ==================== نقطة الإطلاق التلقائية ====================
def start_bot_and_db():
    try:
        print("🔄 جاري الاتصال بقاعدة البيانات...")
        init_pool()
        init_db()

        bot.set_my_commands([
            telebot.types.BotCommand("start", "🚀 بدء أو إعادة تشغيل المنصة")
        ])

        # تشغيل المجدول الزمني (يعمل يومياً الساعة 10 صباحاً بتوقيت دمشق)
        scheduler = BackgroundScheduler(timezone="Asia/Damascus")
        scheduler.add_job(send_daily_challenges, 'cron', hour=10, minute=0)
        scheduler.start()

        print("✅ قاعدة البيانات جاهزة. جاري تشغيل البوت...")
        
        def run_polling():
            import time
            time.sleep(3)  # انتظار 3 ثوانٍ لإغلاق النسخة القديمة على Render وتجنب خطأ 409
            while True:
                try:
                    bot.infinity_polling(skip_pending=True, timeout=20, long_polling_timeout=10)
                except Exception as err:
                    print(f"⚠️ خطأ في الاتصال، إعادة المحاولة خلال 5 ثوانٍ: {err}")
                    time.sleep(5)

        bot_thread = threading.Thread(target=run_polling, daemon=True)
        bot_thread.start()
        print("🚀 البوت يعمل الآن بنجاح!")
    except Exception as e:
        print(f"❌ خطأ أثناء بدء التشغيل: {e}")

start_bot_and_db()
