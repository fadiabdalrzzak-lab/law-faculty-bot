import os

# ==================== مفاتيح الربط ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# مفتاح الذكاء الاصطناعي للمرحلة 13 (شرح الأسئلة وتوليدها) - سيتم استخدامه لاحقاً
AI_API_KEY = os.environ.get("AI_API_KEY", "") 

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if not BOT_TOKEN:
    raise ValueError("❌ لم يتم العثور على متغير البيئة BOT_TOKEN!")

# ==================== الصلاحيات والقنوات ====================
RAW_ADMINS = os.environ.get("ADMIN_IDS", os.environ.get("ADMIN_ID", "1281831877"))
ADMIN_IDS = [int(x.strip()) for x in RAW_ADMINS.split(",") if x.strip().isdigit()]
CHANNEL_USERNAME = "@Lawer_support"

# ==================== الثوابت الأكاديمية والتنقل ====================
PDF_PER_PAGE = 5
MNG_Q_PER_PAGE = 3

YEARS = {1: "السنة الأولى", 2: "السنة الثانية", 3: "السنة الثالثة", 4: "السنة الرابعة"}
SEMESTERS = {1: "الفصل الأول", 2: "الفصل الثاني"}
OPTION_LETTERS = ["أ", "ب", "ج", "د"]
OPTION_MAP = {"A": "أ", "B": "ب", "C": "ج", "D": "د", "أ": "أ", "ب": "ب", "ج": "ج", "د": "د"}

# ==================== الذاكرة المؤقتة (Session Cache) ====================
admin_states = {}
user_mistakes_cache = {}
user_search_cache = {}
