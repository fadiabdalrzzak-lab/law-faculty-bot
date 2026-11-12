import json
from apscheduler.schedulers.background import BackgroundScheduler
from telebot import types
from database import get_db, release_db

def send_morning_goals(bot):
    """إرسال الهدف اليومي كل صباح الساعة 7:00"""
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT user_id, plan_data FROM study_plans")
        plans = cur.fetchall()
        cur.close()
    except Exception as e:
        print(f"Scheduler Error (Morning): {e}")
        plans = []
    finally:
        release_db(conn)
    
    for user_id, plan_data in plans:
        try:
            plan = plan_data if isinstance(plan_data, dict) else json.loads(plan_data)
            subject = plan.get('subject', 'المادة')
            daily_quota = plan.get('daily_quota', 0)
            
            msg = (
                f"🌅 **صباح الخير يا بطل!**\n\n"
                f"🎯 هدفك اليوم في مادة **{subject}** هو إنجاز **{daily_quota} صفحة**.\n\n"
                f"توكل على الله، وابدأ يومك بنشاط وتفاؤل ⚖️💪"
            )
            bot.send_message(user_id, msg, parse_mode="Markdown")
        except Exception as e:
            print(f"Failed to send morning goal to {user_id}: {e}")

def send_evening_checkins(bot):
    """إرسال الاستبيان المسائي كل ليلة الساعة 9:00"""
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT user_id, plan_data FROM study_plans")
        plans = cur.fetchall()
        cur.close()
    except Exception as e:
        print(f"Scheduler Error (Evening): {e}")
        plans = []
    finally:
        release_db(conn)
    
    for user_id, plan_data in plans:
        try:
            plan = plan_data if isinstance(plan_data, dict) else json.loads(plan_data)
            subject = plan.get('subject', 'المادة')
            daily_quota = plan.get('daily_quota', 0)
            
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(
                types.InlineKeyboardButton("✅ أنجزت الهدف بالكامل (100%)", callback_data="chk_100"),
                types.InlineKeyboardButton("👍 أنجزت معظمه (75%)", callback_data="chk_75"),
                types.InlineKeyboardButton("⚖️ أنجزت النصف (50%)", callback_data="chk_50"),
                types.InlineKeyboardButton("🤏 أنجزت القليل (25%)", callback_data="chk_25"),
                types.InlineKeyboardButton("❌ لم أدرس اليوم (0%)", callback_data="chk_0")
            )
            
            msg = (
                f"🌃 **مساء الخير! حان وقت حصاد اليوم:**\n\n"
                f"مادة: **{subject}**\n"
                f"🎯 هدفك اليوم كان: **{daily_quota} صفحة**.\n\n"
                f"أخبرني، كم نسبة إنجازك اليوم لتعديل خطتك غداً؟"
            )
            bot.send_message(user_id, msg, parse_mode="Markdown", reply_markup=markup)
        except Exception as e:
            print(f"Failed to send evening checkin to {user_id}: {e}")

def start_scheduler(bot):
    """تشغيل المجدول الزمني"""
    # ضبط التوقيت على توقيت سوريا لضمان دقة الإشعارات
    scheduler = BackgroundScheduler(timezone="Asia/Damascus")
    
    # رسالة الصباح: الساعة 07:00
    scheduler.add_job(send_morning_goals, 'cron', hour=7, minute=0, args=[bot])
    
    # رسالة المساء: الساعة 21:00 (9 مساءً)
    scheduler.add_job(send_evening_checkins, 'cron', hour=21, minute=0, args=[bot])
    
    scheduler.start()
    print("✅ تم تشغيل نظام المتابعة الآلي بنجاح!")
