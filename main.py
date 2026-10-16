import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

import google.generativeai as genai
from telebot import types
from config import GEMINI_API_KEY
from database import get_db, release_db
from utils import safe_answer_callback, check_subscription, send_sub_required_msg

# تهيئة الذكاء الاصطناعي بالمفتاح السري
genai.configure(api_key=GEMINI_API_KEY)

# التوجيه الصارم (System Prompt) لتقمص الشخصية القانونية السورية
SYRIAN_LAW_PROMPT = """أنت مستشار وأستاذ جامعي في القانون السوري حصراً. مهمتك مساعدة وشرح المواد والأسئلة لطلاب كلية الحقوق بجامعة دمشق. 
استند في إجاباتك وتبريرك إلى التشريع السوري النافذ، والاجتهاد القضائي السوري (محكمة النقض السورية)، والفقه القانوني السوري المعتمد. 
تجنب تماماً أي إشارة لقوانين دول أخرى (كالمصري أو الفرنسي) ما لم يكن السؤال صراحة عن القانون المقارن أو تاريخ القانون. 
كن أكاديمياً، دقيقاً، واستخدم لغة قانونية رصينة، مع تبسيط العلة التشريعية للطالب لتسهيل الفهم العميق وليس الحفظ البصم فقط."""

# قاموس لحفظ جلسات النقاش النشطة للطلاب
active_ai_sessions = {}

def create_smart_chat_session(initial_prompt=None):
    """دالة ذكية تتصل بـ gemini-3.8-flash وتتخطى أي نموذج قديم تلقائياً"""
    candidate_models = ["gemini-3.8-flash", "gemini-3.8-pro", "gemini-3.5-flash", "gemini-3.0-flash"]
    
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                clean_name = m.name.replace("models/", "")
                if clean_name not in candidate_models and "2.5" not in clean_name and "1.5" not in clean_name:
                    candidate_models.append(clean_name)
    except Exception:
        pass

    last_error = None
    for model_name in candidate_models:
        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=SYRIAN_LAW_PROMPT
            )
            chat = model.start_chat(history=[])
            if initial_prompt:
                response = chat.send_message(initial_prompt)
                return chat, response
            else:
                # اختبار سريع للتأكد من صلاحية النموذج قبل فتح الجلسة الحرة
                response = chat.send_message("مرحباً، عرف عن نفسك باختصار شديد بسطرين كمستشار قانوني سوري جاهز لمساعدة الطالب.")
                return chat, response
        except Exception as e:
            last_error = e
            continue

    raise last_error if last_error else Exception("لم يتم العثور على نموذج ذكاء اصطناعي متاح.")

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

        bot.send_chat_action(message.chat.id, 'typing')
        try:
            chat, _ = create_smart_chat_session(initial_prompt=None)
            active_ai_sessions[user_id] = chat

            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🏠 إنهاء الجلسة وإغلاق المساعد", callback_data="exit_ai_chat"))

            welcome_msg = (
                "⚖️ **أهلاً بك في مكتب المستشار القانوني الذكي (AI)**\n\n"
                "أنا مبرمج خصيصاً لمساعدتك في دراسة **القانون السوري** وفق مناهج كلية الحقوق بجامعة دمشق.\n\n"
                "🔹 **كيف يمكنني مساعدتك اليوم؟**\n"
                "• اشرح لي فكرة أو نظرية قانونية مستعصية.\n"
                "• ما الفرق بين مصطلحين قانونيين (مثل البطلان والفسخ)؟\n"
                "• اطرح عليّ قضية عملية لنقوم بتكييفها قانونياً معاً.\n\n"
                "✍️ **اكتب سؤالك أو استفسارك في رسالة الآن مباشرة:**"
            )
            bot.send_message(message.chat.id, welcome_msg, parse_mode="Markdown", reply_markup=markup)
        except Exception as e:
            print(f"Gemini Main Init Error: {e}")
            bot.send_message(message.chat.id, f"⚠️ **حدث خطأ أثناء تشغيل المساعد الذكي:**\n`{str(e)}`", parse_mode="Markdown")


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
        except Exception as e:
            conn.rollback()
            q = None
        finally:
            release_db(conn)

        if not q:
            return safe_answer_callback(bot, call.id, "❌ لم يتم العثور على السؤال.", show_alert=True)

        safe_answer_callback(bot, call.id, "⚖️ جاري تحضير التكييف القانوني للسؤال...")
        bot.send_chat_action(call.message.chat.id, 'typing')

        sub, q_text, a, b, c, d, correct = q
        correct_clean = str(correct).strip() if correct else ""
        correct_full = {"أ": a, "ب": b, "ج": c, "د": d}.get(correct_clean, "")

        prompt = f"""
        المادة الدراسية: {sub}
        الرجاء شرح هذا السؤال الامتحاني المؤتمت:
        النص: {q_text}
        الخيارات:
        أ) {a}
        ب) {b}
        ج) {c}
        د) {d}
        
        الإجابة الصحيحة المعتمدة في السلم الامتحاني هي: ({correct_clean}) {correct_full}
        
        اشرح لي باختصار ووضوح:
        1. لماذا تعتبر هذه الإجابة هي الصحيحة وفقاً للقانون السوري؟
        2. لماذا تعتبر الخيارات الأخرى غير دقيقة أو خاطئة؟
        """

        try:
            chat, response = create_smart_chat_session(initial_prompt=prompt)
            active_ai_sessions[user_id] = chat

            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 إنهاء النقاش والعودة للتدريب", callback_data="exit_ai_chat"))
            
            msg_text = f"⚖️ **التكييف القانوني (المستشار الذكي):**\n\n{response.text}\n\n*💡 يمكنك الآن الرد على هذه الرسالة لطرح أي سؤال إضافي حول هذه القاعدة القانونية.*"
            try:
                bot.send_message(call.message.chat.id, msg_text, parse_mode="Markdown", reply_markup=markup)
            except Exception:
                bot.send_message(call.message.chat.id, msg_text, reply_markup=markup)

        except Exception as e:
            print(f"Gemini API Error: {e}")
            bot.send_message(call.message.chat.id, f"⚠️ **حدث خطأ أثناء الاتصال بالمستشار الذكي:**\n`{str(e)}`", parse_mode="Markdown")


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
        chat_session = active_ai_sessions[user_id]
        
        bot.send_chat_action(message.chat.id, 'typing')
        try:
            response = chat_session.send_message(message.text)
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 إنهاء النقاش", callback_data="exit_ai_chat"))
            try:
                bot.reply_to(message, response.text, parse_mode="Markdown", reply_markup=markup)
            except Exception:
                bot.reply_to(message, response.text, reply_markup=markup)
        except Exception as e:
            print(f"Gemini Chat Error: {e}")
            bot.reply_to(message, f"⚠️ **خطأ تقني أثناء الرد:**\n`{str(e)}`", parse_mode="Markdown")
