from telebot import types as tg_types
from database import get_db, release_db
from utils import safe_answer_callback, check_subscription, send_sub_required_msg, md

def send_safe_explanation(bot, chat_id, text, reply_markup=None):
    """دالة مؤمنة لإرسال التكييف القانوني وتقسيمه إن كان طويلاً مع حماية الـ Markdown"""
    if not text:
        return
    max_len = 4000
    parts = [text[i:i+max_len] for i in range(0, len(text), max_len)]
    for idx, part in enumerate(parts):
        markup = reply_markup if idx == len(parts) - 1 else None
        try:
            bot.send_message(chat_id, part, parse_mode="Markdown", reply_markup=markup)
        except Exception:
            # إرسال آمن بدون Markdown في حال وجود رموز خاصة في ملف الإكسل
            bot.send_message(chat_id, part.replace("*", ""), reply_markup=markup)


def register_ai_handlers(bot):

    # ==================== 1. زر المساعد الذكي (وضع قيد البرمجة) ====================
    @bot.message_handler(func=lambda msg: msg.text == "🤖 المساعد الذكي")
    def handle_main_ai_button(message):
        user_id = message.from_user.id
        if not check_subscription(bot, user_id):
            return send_sub_required_msg(bot, message.chat.id)

        # حذف رسالة ضغطة الزر للحفاظ على نظافة المحادثة
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except Exception:
            pass

        msg_text = (
            "🤖 **المستشار القانوني الذكي (AI)**\n\n"
            "⚙️ **هذه الميزة قيد التطوير والبرمجة حالياً!**\n"
            "نعمل على تجهيز محرك قانوني خاص بطلاب كلية الحقوق بجامعة دمشق ليتم إطلاقه قريباً بأعلى دقة وسرعة.\n\n"
            "💡 *ملاحظة: يمكنك حالياً الاستفادة من ميزة **«التكييف القانوني»** المتوفرة تحت كل سؤال داخل قسم تدريب الدورات المؤتمتة!*"
        )
        bot.send_message(message.chat.id, msg_text, parse_mode="Markdown")


    # ==================== 2. زر التكييف القانوني الثابت والسريع ====================
    @bot.callback_query_handler(func=lambda call: call.data.startswith("ai_explain_"))
    def handle_ai_explain(call):
        try:
            q_id = int(call.data.split("_")[2])
        except (IndexError, ValueError):
            return safe_answer_callback(bot, call.id, "❌ خطأ في معرف السؤال.", show_alert=True)
        
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT subject, question_text, option_a, option_b, option_c, option_d, correct_option, explanation 
                FROM questions WHERE id=%s
            """, (q_id,))
            q = cur.fetchone()
            cur.close()
        except Exception:
            conn.rollback()
            q = None
        finally:
            release_db(conn)

        if not q:
            return safe_answer_callback(bot, call.id, "❌ لم يتم العثور على السؤال.", show_alert=True)

        sub, q_text, a, b, c, d, correct, explanation = q
        correct_clean = str(correct).strip() if correct else ""
        correct_full = {"أ": a, "ب": b, "ج": c, "د": d}.get(correct_clean, "")

        # التحقق مما إذا كان التكييف القانوني مضافاً للسؤال في قاعدة البيانات
        if explanation and str(explanation).strip() and str(explanation).strip().lower() not in ["nan", "none", ""]:
            exp_text = str(explanation).strip()
        else:
            exp_text = "التكييف القانوني المفصل لهذا السؤال قيد الإضافة من المقرر الدراسي المعتمد."

        safe_answer_callback(bot, call.id, "⚖️ تم جلب التكييف القانوني!")

        msg_text = (
            f"⚖️ **التكييف القانوني المعتمد — {md(sub)}**\n\n"
            f"✅ **الإجابة الصحيحة:** ({md(correct_clean)}) {md(correct_full)}\n\n"
            f"📖 **الشرح والسند القانوني:**\n{md(exp_text)}"
        )

        markup = tg_types.InlineKeyboardMarkup()
        markup.add(tg_types.InlineKeyboardButton("🗑️ إخفاء التكييف القانوني", callback_data="close_explanation"))

        send_safe_explanation(bot, call.message.chat.id, msg_text, reply_markup=markup)


    # ==================== 3. زر إخفاء رسالة التكييف لعدم ازدحام المحادثة ====================
    @bot.callback_query_handler(func=lambda call: call.data == "close_explanation")
    def handle_close_explanation(call):
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        safe_answer_callback(bot, call.id, "تم إخفاء الشرح")
