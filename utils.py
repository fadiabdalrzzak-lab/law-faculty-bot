from telebot import apihelper
from config import ADMIN_IDS, CHANNEL_USERNAME
from keyboards import get_sub_required_inline

# ==================== الصلاحيات ====================
def is_admin(user_id):
    return user_id in ADMIN_IDS

# ==================== تنسيق النصوص (Markdown) ====================
def md(text):
    return str(text).replace("*", "\\*").replace("_", "\\_").replace("`", "\\`")

# ==================== معالجة الاستجابات الشفافة بأمان ====================
def safe_answer_callback(bot, call_id, text=None, show_alert=False):
    try:
        bot.answer_callback_query(call_id, text=text, show_alert=show_alert)
    except Exception:
        pass

# ==================== نظام التحقق من الاشتراك الإجباري ====================
def check_subscription(bot, user_id):
    if is_admin(user_id):
        return True
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["creator", "administrator", "member", "restricted"]
    except apihelper.ApiTelegramException:
        # إذا لم يكن المستخدم في القناة
        return False
    except Exception as e:
        print(f"⚠️ خطأ فحص الاشتراك: {e}")
        return False

def send_sub_required_msg(bot, chat_id):
    markup = get_sub_required_inline()
    bot.send_message(
        chat_id,
        f"أهلاً بك يا زميلي في عالم القانون! ⚖️\n\n"
        f"يسعدنا جداً انضمامك إلينا. لكي تتمكن من استخدام جميع ميزات البوت مجاناً وبحرية، يُرجى الانضمام إلى قناتنا الرسمية أولاً عبر الرابط أدناه:\n\n"
        f"{md(CHANNEL_USERNAME)}\n\n"
        f"بمجرد انضمامك، اضغط على الزر بالأسفل لنبدأ رحلة التفوق معاً! 👇",
        parse_mode="Markdown", reply_markup=markup,
    )
