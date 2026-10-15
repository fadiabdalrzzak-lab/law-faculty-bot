import google.generativeai as genai
from telebot import types
from config import GEMINI_API_KEY

# تهيئة الذكاء الاصطناعي بالمفتاح السري
genai.configure(api_key=GEMINI_API_KEY)

# التوجيه الصارم (System Prompt) لتقمص الشخصية القانونية السورية
SYRIAN_LAW_PROMPT = """أنت مستشار وأستاذ في القانون السوري حصراً. مهمتك شرح الأسئلة لطلاب كلية الحقوق بجامعة دمشق. 
استند في تبريرك إلى التشريع السوري، والاجتهاد القضائي السوري (محكمة النقض السورية)، والفقه السوري المعتمد. 
تجنب تماماً أي إشارة لقوانين دول أخرى (كالمصري أو الفرنسي) ما لم يكن السؤال صراحة عن القانون المقارن. 
كن أكاديمياً، دقيقاً، واستخدم لغة قانونية رصينة، مع تبسيط العلة التشريعية للطالب لتسهيل الفهم وليس الحفظ فقط."""

# دالة ذكية لاختيار أحدث نموذج متاح تلقائياً لمنع خطأ 404 مستقبلاً
def get_working_model():
    preferred_models = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash-latest",
        "gemini-pro"
    ]
    for model_name in preferred_models:
        try:
            return genai.GenerativeModel(
                model_name=model_name,
                system_instruction=SYRIAN_LAW_PROMPT
            )
        except Exception:
            continue
    return genai.GenerativeModel("gemini-2.5-flash")

# قاموس لحفظ جلسات النقاش النشطة للطلاب
active_ai_sessions = {}

def register_ai_handlers(bot):

    @bot.callback_query_handler(func=lambda call: call.data.startswith("ai_explain_"))
    def handle_ai_explain(call):
        q_id = int(call.data.split("_")[2])
        user_id = call.from_user.id
        
        from database import get_db, release_db
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("SELECT question_text, option_a, option_b, option_c, option_d, correct_option FROM questions WHERE id=%s", (q_id,))
            q = cur.fetchone()
            cur.close()
        except Exception:
            q = None
        finally:
            release_db(conn)

        if not q:
            return bot.answer_callback_query(call.id, "❌ لم يتم العثور على السؤال.", show_alert=True)

        bot.answer_callback_query(call.id, "⚖️ جاري تحضير التكييف القانوني للسؤال...")
        bot.send_chat_action(call.message.chat.id, 'typing')

        q_text, a, b, c, d, correct = q
        correct_full = {"أ": a, "ب": b, "ج": c, "د": d}.get(correct.strip(), "")

        prompt = f"""
        الرجاء شرح هذا السؤال الامتحاني المؤتمت:
        النص: {q_text}
        الخيارات:
        أ) {a}
        ب) {b}
        ج) {c}
        د) {d}
        
        الإجابة الصحيحة المعتمدة في السلم الامتحاني هي: ({correct}) {correct_full}
        
        اشرح لي باختصار لماذا هذه الإجابة هي الصحيحة وفقاً للقانون السوري؟ ولماذا تعتبر الخيارات الأخرى خاطئة؟
        """

        try:
            # محاولة الاتصال بالنموذج الأحدث، وفي حال رفضه يتم جلب أول نموذج متاح في الحساب تلقائياً
            try:
                model = genai.GenerativeModel(model_name="gemini-2.5-flash", system_instruction=SYRIAN_LAW_PROMPT)
                chat = model.start_chat(history=[])
                response = chat.send_message(prompt)
            except Exception:
                available_models = [
                    m.name for m in genai.list_models() 
                    if 'generateContent' in m.supported_generation_methods
                ]
                if not available_models:
                    raise Exception("لا توجد نماذج متاحة لهذا المفتاح.")
                # اختيار أول نموذج متاح من قائمة جوجل الرسمية
                fallback_model_name = available_models[0]
                model = genai.GenerativeModel(model_name=fallback_model_name)
                chat = model.start_chat(history=[])
                response = chat.send_message(SYRIAN_LAW_PROMPT + "\n\n" + prompt)

            active_ai_sessions[user_id] = chat

            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 إنهاء النقاش والعودة للتدريب", callback_data="exit_ai_chat"))
            
            msg_text = f"⚖️ **التكييف القانوني (المستشار الذكي):**\n\n{response.text}\n\n*💡 يمكنك الآن الرد على هذه الرسالة لطرح المزيد من الأسئلة حول هذه القاعدة القانونية.*"
            try:
                bot.send_message(call.message.chat.id, msg_text, parse_mode="Markdown", reply_markup=markup)
            except Exception:
                bot.send_message(call.message.chat.id, msg_text, reply_markup=markup)

        except Exception as e:
            print(f"Gemini API Error: {e}")
            bot.send_message(call.message.chat.id, f"⚠️ **حدث خطأ أثناء الاتصال بالمستشار الذكي:**\n`{str(e)}`", parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data == "exit_ai_chat")
    def handle_exit_ai(call):
        user_id = call.from_user.id
        if user_id in active_ai_sessions:
            del active_ai_sessions[user_id]
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        bot.send_message(call.message.chat.id, "🔙 **تم إنهاء النقاش القانوني.**\nيمكنك الآن متابعة التدريب من رسالة الاختبار بالأعلى 👆", parse_mode="Markdown")
        bot.answer_callback_query(call.id, "تمت العودة للتدريب")

    @bot.message_handler(func=lambda msg: msg.from_user.id in active_ai_sessions and msg.text not in [
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
            markup.add(types.InlineKeyboardButton("🔙 إنهاء النقاش والعودة للتدريب", callback_data="exit_ai_chat"))
            try:
                bot.reply_to(message, response.text, parse_mode="Markdown", reply_markup=markup)
            except Exception:
                bot.reply_to(message, response.text, reply_markup=markup)
        except Exception as e:
            print(f"Gemini Chat Error: {e}")
            bot.reply_to(message, f"⚠️ **خطأ تقني:**\n`{str(e)}`", parse_mode="Markdown")
