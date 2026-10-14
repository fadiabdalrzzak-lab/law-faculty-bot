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

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=SYRIAN_LAW_PROMPT
)

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
        finally: release_db(conn)

        if not q:
            return bot.answer_callback_query(call.id, "❌ لم يتم العثور على السؤال.", show_alert=True)

        bot.answer_callback_query(call.id, "⚖️ جاري تحضير التكييف القانوني للسؤال...")
        bot.send_chat_action(call.message.chat.id, 'typing')

        q_text, a, b, c, d, correct = q
        correct_full = {"أ": a, "ب": b, "ج": c, "د": d}.get(correct.strip(), "")

        # صياغة السؤال الموجه للذكاء الاصطناعي في الخلفية
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
            chat = model.start_chat(history=[])
            response = chat.send_message(prompt)
            # تسجيل الطالب في وضع النقاش الذكي
            active_ai_sessions[user_id] = chat

            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 إنهاء النقاش والعودة للتدريب", callback_data="exit_ai_chat"))
            
            msg_text = f"⚖️ **التكييف القانوني (المستشار الذكي):**\n\n{response.text}\n\n*💡 يمكنك الآن الرد على هذه الرسالة لطرح المزيد من الأسئلة حول هذه القاعدة القانونية.*"
            try:
                bot.send_message(call.message.chat.id, msg_text, parse_mode="Markdown", reply_markup=markup)
            except Exception:
                # لتفادي أخطاء الماركدوان من ردود Gemini
                bot.send_message(call.message.chat.id, msg_text, reply_markup=markup)

        except Exception as e:
            bot.send_message(call.message.chat.id, "⚠️ عذراً، المستشار الذكي يواجه ضغطاً حالياً. يرجى المحاولة بعد قليل.")

    @bot.callback_query_handler(func=lambda call: call.data == "exit_ai_chat")
    def handle_exit_ai(call):
        user_id = call.from_user.id
        if user_id in active_ai_sessions:
            del active_ai_sessions[user_id]
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception: pass
        bot.send_message(call.message.chat.id, "🔙 **تم إنهاء النقاش القانوني.**\nيمكنك الآن متابعة التدريب من رسالة الاختبار بالأعلى 👆", parse_mode="Markdown")
        bot.answer_callback_query(call.id, "تمت العودة للتدريب")

    # التقاط رسائل الطالب أثناء النقاش وتمريرها لـ Gemini
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
            bot.reply_to(message, "⚠️ حدث خطأ أثناء الاتصال بالمستشار الذكي. حاول مجدداً.")
