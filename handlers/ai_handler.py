from google import genai
from google.genai import types
from telebot import types as tg_types
from config import GEMINI_API_KEY
from database import get_db, release_db
from utils import safe_answer_callback, check_subscription, send_sub_required_msg

# التوجيه الصارم (System Prompt) لتقمص الشخصية القانونية السورية
SYRIAN_LAW_PROMPT = """أنت مستشار قانوني وأستاذ جامعي خبير في القانون السوري حصراً. مهمتك مساعدة وشرح المواد والأسئلة لطلاب كلية الحقوق بجامعة دمشق. 
استند في إجاباتك وتحليلاتك القانونية إلى التشريع السوري النافذ، والاجتهاد القضائي السوري (محكمة النقض)، والفقه القانوني السوري المعتمد. 
تجنب تماماً أي إشارة لقوانين دول أخرى ما لم يطلب الطالب ذلك صراحة. 
كن دقيقاً، أكاديمياً، واستخدم لغة قانونية رصينة، مع تفصيل العلة التشريعية لتسهيل الفهم العميق."""

# قاموس لحفظ سجل المحادثة لكل طالب
active_ai_sessions = {}

def ask_gemini(user_id, user_text, reset_session=False):
    """دالة اتصال مخصصة لحسابات Pro لاستخدام النماذج الاحترافية المستقرة"""
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    if reset_session or user_id not in active_ai_sessions:
        active_ai_sessions[user_id] = []

    active_ai_sessions[user_id].append(
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_text)]
        )
    )

    # الاعتماد حصرياً على النماذج الاحترافية القوية لحسابات الـ Pro
        pro_models = ["gemini-3.1-pro", "gemini-3.1-pro-preview", "gemini-3.8-flash"]

    last_error = None

    for model_name in pro_models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=active_ai_sessions[user_id],
                config=types.GenerateContentConfig(
                    system_instruction=SYRIAN_LAW_PROMPT,
                    temperature=0.2 # دقة عالية جداً وثبات قانوني
                )
            )
            reply_text = response.text
            active_ai_sessions[user_id].append(
                types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=reply_text)]
                )
            )
            return reply_text
        except Exception as e:
            last_error = e
            continue

    if active_ai_sessions.get(user_id):
        active_ai_sessions[user_id].pop()
    raise last_error if last_error else Exception("تعذر الاتصال بالنماذج الاحترافية.")

def send_long_response(bot, chat_id, text, reply_markup=None, reply_to=None):
    """دالة لتقسيم النصوص الطويلة جداً لتجنب خطأ 400 message is too long"""
    if not text:
        return
    max_len = 4000
    parts = [text[i:i+max_len] for i in range(0, len(text), max_len)]
    for idx, part in enumerate(parts):
        markup = reply_markup if idx == len(parts) - 1 else None
        try:
            if reply_to and idx == 0:
                bot.reply_to(reply_to, part, parse_mode="Markdown", reply_markup=markup)
            else:
                bot.send_message(chat_id, part, parse_mode="Markdown", reply_markup=markup)
        except Exception:
            if reply_to and idx == 0:
                bot.reply_to(reply_to, part, reply_markup=markup)
            else:
                bot.send_message(chat_id, part, reply_markup=markup)


def register_ai_handlers(bot):

    # ==================== 1. زر المساعد الذكي من القائمة الرئيسية ====================
    @bot.message_handler(func=lambda msg: msg.text == "🤖 المساعد الذكي")
    def handle_main_ai_button(message):
        user_id = message.from_user.id
        if not check_subscription(bot, user_id):
            return send_sub_required_msg(bot, message.chat.id)

        try:
            bot.delete_message(message.chat.id, message.message_id)
        except Exception:
            pass

        active_ai_sessions[user_id] = []

        markup = tg_types.InlineKeyboardMarkup()
        markup.add(tg_types.InlineKeyboardButton("🏠 إنهاء الجلسة وإغلاق المساعد", callback_data="exit_ai_chat"))

        welcome_msg = (
            "⚖️ **أهلاً بك في مكتب المستشار القانوني المحترف (Pro AI)**\n\n"
            "أنا مدعوم بنماذج Pro الاحترافية لمساعدتك في دراسة **القانون السوري** وفق مناهج كلية الحقوق بجامعة دمشق بدقة متناهية.\n\n"
            "🔹 **كيف يمكنني مساعدتك اليوم؟**\n"
            "• اشرح لي فكرة أو نظرية قانونية مستعصية.\n"
            "• ما الفرق بين مصطلحين قانونيين (مثل البطلان والفسخ)؟\n"
            "• اطرح عليّ قضية عملية لنقوم بتكييفها قانونياً معاً.\n\n"
            "✍️ **اكتب سؤالك أو استفسارك في رسالة الآن مباشرة:**"
        )
        bot.send_message(message.chat.id, welcome_msg, parse_mode="Markdown", reply_markup=markup)


    # ==================== 2. زر التكييف القانوني داخل التدريب ====================
    @bot.callback_query_handler(func=lambda call: call.data.startswith("ai_explain_"))
    def handle_ai_explain(call):
        q_id = int(call.data.split("_")[2])
        user_id = call.from_user.id
        
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("SELECT subject, question_text, option_a, option_b, option_c, option_d, correct_option FROM questions WHERE id=%s", (q_id,))
            q = cur.fetchone()
            cur.close()
        except Exception:
            conn.rollback()
            q = None
        finally:
            release_db(conn)

        if not q:
            return safe_answer_callback(bot, call.id, "❌ لم يتم العثور على السؤال.", show_alert=True)

        safe_answer_callback(bot, call.id, "⚖️ جاري تحضير التكييف القانوني المحترف...")
        bot.send_chat_action(call.message.chat.id, 'typing')

        sub, q_text, a, b, c, d, correct = q
        correct_clean = str(correct).strip() if correct else ""
        correct_full = {"أ": a, "ب": b, "ج": c, "د": d}.get(correct_clean, "")

        prompt = f"""
        المادة الدراسية: {sub}
        قم بالتكييف القانوني لهذا السؤال الامتحاني بأسلوب أكاديمي دقيق ومباشر:
        النص: {q_text}
        الخيارات: أ) {a} | ب) {b} | ج) {c} | د) {d}
        الإجابة الصحيحة: ({correct_clean}) {correct_full}
        
        وضّح السند القانوني السوري للإجابة الصحيحة وسبب استبعاد بقية الخيارات بدقة.
        """

        try:
            reply_text = ask_gemini(user_id, prompt, reset_session=True)

            markup = tg_types.InlineKeyboardMarkup()
            markup.add(tg_types.InlineKeyboardButton("🔙 إنهاء النقاش والعودة للتدريب", callback_data="exit_ai_chat"))
            
            full_msg = f"⚖️ **التكييف القانوني (المستشار المحترف Pro):**\n\n{reply_text}\n\n*💡 يمكنك الرد على هذه الرسالة لطرح أي استفسار إضافي.*"
            send_long_response(bot, call.message.chat.id, full_msg, reply_markup=markup)

        except Exception as e:
            print(f"Gemini Pro API Error: {e}")
            bot.send_message(call.message.chat.id, f"⚠️ **خطأ في الاتصال بنماذج Pro:**\n`{str(e)}`", parse_mode="Markdown")


    # ==================== 3. إنهاء النقاش والعودة ====================
    @bot.callback_query_handler(func=lambda call: call.data == "exit_ai_chat")
    def handle_exit_ai(call):
        user_id = call.from_user.id
        if user_id in active_ai_sessions:
            del active_ai_sessions[user_id]
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        bot.send_message(call.message.chat.id, "🔙 **تم إغلاق جلسة النقاش القانوني.**\nيمكنك متابعة دراستك أو تدريباتك كالمعتاد 👆", parse_mode="Markdown")
        safe_answer_callback(bot, call.id, "تم إنهاء النقاش")


    # ==================== 4. التقاط رسائل النقاش المفتوح مع المستشار ====================
    @bot.message_handler(func=lambda msg: msg.from_user.id in active_ai_sessions and msg.text and not msg.text.startswith("/") and msg.text not in [
        "➡️ السؤال التالي", "⬅️ السؤال السابق", "🔄 إعادة الاختبار", 
        "🏁 إنهاء وعرض النتيجة", "🏁 إنهاء وتسليم الورقة", "💾 حفظ السؤال للمراجعة", 
        "⚠️ الإبلاغ عن خطأ", "📚 الانتقال إلى مادة أخرى", "🏠 القائمة الرئيسية",
        "🏛 تدريب الدورات المؤتمتة", "📝 الاختبارات", "📚 المكتبة", 
        "🧠 البطاقات التعليمية", "📅 خطة الدراسة", "📈 تقدمي الدراسي", 
        "🏆 الإنجازات", "⚙️ إعدادات حسابي", "🤖 المساعد الذكي", "💬 الدعم والملاحظات"
    ])
    def handle_ai_discussion(message):
        user_id = message.from_user.id
        bot.send_chat_action(message.chat.id, 'typing')
        try:
            reply_text = ask_gemini(user_id, message.text, reset_session=False)
            markup = tg_types.InlineKeyboardMarkup()
            markup.add(tg_types.InlineKeyboardButton("🔙 إنهاء النقاش", callback_data="exit_ai_chat"))
            send_long_response(bot, message.chat.id, reply_text, reply_markup=markup, reply_to=message)
        except Exception as e:
            print(f"Gemini Pro Chat Error: {e}")
            bot.reply_to(message, f"⚠️ **خطأ تقني:**\n`{str(e)}`", parse_mode="Markdown")
