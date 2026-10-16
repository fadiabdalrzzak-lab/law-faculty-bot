import os
import time
import threading
import telebot
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler

# استدعاء إعدادات البوت وقاعدة البيانات
from config import bot
from database import init_pool, init_db, get_db, release_db
from utils import md

# استدعاء ملفات التحكم (Handlers)
from handlers.student_handler import register_student_handlers
from handlers.exam_handler import register_exam_handlers
from handlers.ai_handler import register_ai_handlers
try:
    from handlers.admin_handler import register_admin_handlers
except ImportError:
    pass

# تسجيل أوامر البوت
register_student_handlers(bot)
register_exam_handlers(bot)
register_ai_handlers(bot)
try:
    register_admin_handlers(bot)
except NameError:
    pass

# إعداد تطبيق Flask لإبقاء السيرفر حياً (Web Server)
app = Flask(__name__)

@app.route('/')
def home():
    return "Law Quiz Bot is Live and Running smoothly! 🚀"

# دالة إرسال تحدي اليوم للطلاب
def send_daily_challenges():
    print("🎯 بدء إرسال تحدي اليوم...")
    conn = get_db()
    try:
        cur = conn.cursor()
        # جلب السنوات والفصول المتاحة
        cur.execute("SELECT DISTINCT academic_year, academic_semester FROM users")
        groups = cur.fetchall()
        
        for year, sem in groups:
            cur.execute("SELECT id, subject, question_text, option_a, option_b, option_c, option_d FROM questions WHERE academic_year=%s AND academic_semester=%s ORDER BY RANDOM() LIMIT 1", (year, sem))
            q = cur.fetchone()
            if not q: 
                continue
            
            q_id, sub, text, opt_a, opt_b, opt_c, opt_d = q
            options = [opt_a, opt_b, opt_c, opt_d]
            
            msg_text = f"🎯 **تحدي اليوم!** ركز جيداً، الإجابة الصحيحة تمنحك 20 نقطة 🌟\n\n📚 {md(sub)}\n\n❓ {md(text)}"
            markup = telebot.types.InlineKeyboardMarkup()
            for i, letter in enumerate(['أ', 'ب', 'ج', 'د']):
                if i < len(options) and options[i]:
                    markup.add(telebot.types.InlineKeyboardButton(f"{letter}) {md(options[i])}", callback_data=f"challenge_{letter}_{q_id}"))
            
            # إرسال التحدي للطلاب المطابقين
            cur.execute("SELECT user_id FROM users WHERE academic_year=%s AND academic_semester=%s", (year, sem))
            students = cur.fetchall()
            
            for (u_id,) in students:
                try:
                    bot.send_message(u_id, msg_text, parse_mode="Markdown", reply_markup=markup)
                    time.sleep(0.05) # منع حظر تيليجرام
                except Exception: 
                    pass
        cur.close()
        print("✅ تم إرسال جميع التحديات بنجاح.")
    except Exception as e:
        print(f"❌ خطأ في إرسال التحديات: {e}")
    finally: 
        release_db(conn)

# نقطة الإطلاق التلقائية وإدارة اتصال تيليجرام
def start_bot_and_db():
    try:
        print("🔄 جاري الاتصال بقاعدة البيانات...")
        init_pool()
        init_db()

        bot.set_my_commands([
            telebot.types.BotCommand("start", "🚀 بدء أو إعادة تشغيل المنصة")
        ])

        # تشغيل المجدول الزمني بتوقيت دمشق
        scheduler = BackgroundScheduler(timezone="Asia/Damascus")
        scheduler.add_job(send_daily_challenges, 'cron', hour=10, minute=0)
        scheduler.start()

        print("✅ قاعدة البيانات جاهزة. جاري تشغيل البوت...")
        
        # حلقة التشغيل المعزولة (لمنع خطأ 409 والخروج المبكر)
        def run_polling():
            time.sleep(3)  # انتظار إغلاق النسخة القديمة لتجنب التضارب 409
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

# ==========================================
# تشغيل العمليات الأساسية (بدون مسافات بادئة)
# ==========================================
start_bot_and_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
