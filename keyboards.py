from telebot import types
from config import YEARS, SEMESTERS, CHANNEL_USERNAME

# ==================== لوحات مفاتيح الطالب ====================
def get_student_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    # القائمة الرئيسية الاحترافية الجديدة (كما ورد في خطة التطوير)
    markup.row("🏛 المواد الدراسية", "📝 الاختبارات")
    markup.row("📚 المكتبة", "🧠 البطاقات التعليمية")
    markup.row("📅 خطة الدراسة", "📈 تقدمي الدراسي")
    markup.row("🏆 الإنجازات", "🤖 المساعد الذكي")
    markup.row("💬 الدعم والملاحظات")
    return markup

def get_exam_control_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("➡️ السؤال التالي", "⬅️ السؤال السابق")
    markup.row("💾 حفظ السؤال للمراجعة", "⚠️ الإبلاغ عن خطأ")
    markup.row("🔄 إعادة الاختبار", "🏁 إنهاء وعرض النتيجة")
    markup.row("🏠 القائمة الرئيسية")
    return markup

def get_sub_required_inline():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(
        "📢 انضم إلى قناتنا الأكاديمية", 
        url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}"
    ))
    markup.add(types.InlineKeyboardButton("✅ تحققت من الانضمام، دعنا نبدأ!", callback_data="check_sub"))
    return markup

# ==================== لوحات مفاتيح المشرف ====================
def get_admin_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📥 رفع أسئلة (Excel/CSV)", "📝 إضافة سؤال فردي")
    markup.row("📊 إحصائيات البوت", "🗑️ إدارة/حذف الأسئلة")
    markup.row("🗂️ حذف دورة كاملة", "📄 رفع ملف PDF جديد")
    markup.row("📢 إذاعة للجميع", "📤 تصدير الأسئلة (Excel)")
    markup.row("📚 قائمة سنوات الحقوق", "📑 المكتبة والملفات PDF")
    return markup

def get_cancel_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🏠 القائمة الرئيسية", "❌ إلغاء العملية")
    return markup

def get_years_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(YEARS[1], YEARS[2])
    markup.row(YEARS[3], YEARS[4])
    markup.row("🏠 القائمة الرئيسية", "❌ إلغاء العملية")
    return markup

def get_semesters_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(SEMESTERS[1], SEMESTERS[2])
    markup.row("🏠 القائمة الرئيسية", "❌ إلغاء العملية")
    return markup

def get_correct_option_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("أ", "ب", "ج", "د")
    markup.row("❌ إلغاء العملية")
    return markup
