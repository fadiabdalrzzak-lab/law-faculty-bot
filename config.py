import os

# ==================== الإعدادات الأساسية والمفاتيح ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# تصحيح رابط قاعدة البيانات ليتوافق مع SQLAlchemy و Psycopg2
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if not BOT_TOKEN:
    raise ValueError("❌ لم يتم العثور على متغير البيئة BOT_TOKEN!")

# جلب معرفات المشرفين
RAW_ADMINS = os.environ.get("ADMIN_IDS", os.environ.get("ADMIN_ID", "1281831877"))
ADMIN_IDS = [int(x.strip()) for x in RAW_ADMINS.split(",") if x.strip().isdigit()]

# معرف قناة الاشتراك الإجباري
CHANNEL_USERNAME = "@Lawer_support"

# ==================== الثوابت الأكاديمية (كلية الحقوق) ====================
PDF_PER_PAGE = 5
MNG_Q_PER_PAGE = 3

YEARS = {1: "السنة الأولى", 2: "السنة الثانية", 3: "السنة الثالثة", 4: "السنة الرابعة"}
SEMESTERS = {1: "الفصل الأول", 2: "الفصل الثاني"}
OPTION_LETTERS = ["أ", "ب", "ج", "د"]
OPTION_MAP = {"A": "أ", "B": "ب", "C": "ج", "D": "د", "أ": "أ", "ب": "ب", "ج": "ج", "د": "د"}

# ==================== قواميس الذاكرة المؤقتة (Cache) ====================
admin_states = {}
user_mistakes_cache = {}
user_search_cache = {}
