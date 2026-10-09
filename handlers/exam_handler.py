from telebot import types
from config import OPTION_LETTERS, user_mistakes_cache
from database import get_db, release_db, load_session_from_db, save_session_to_db, delete_session
from keyboards import get_exam_control_keyboard, get_student_main_keyboard
from utils import md, safe_answer_callback, is_admin

def register_exam_handlers(bot):

    def send_current_question(chat_id, user_id, session, message_id=None):
        bot.send_chat_action(chat_id, 'typing')
        questions, index = session.get("question_ids", []), session.get("index", 0)

        if index >= len(questions):
            if message_id:
                try: bot.edit_message_reply_markup(chat_id, message_id, reply_markup=None)
                except Exception: pass
            finish_exam(chat_id, user_id, session)
            return

        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, question_text, option_a, option_b, option_c, option_d FROM questions WHERE id=%s", (questions[index],))
            q = cur.fetchone()
            cur.close()
        finally: release_db(conn)

        if not q:
            bot.send_message(chat_id, "❌ حدث خطأ: السؤال غير موجود.")
            return

        q_id, text, options = q[0], q[1], [q[2], q[3], q[4], q[5]]
        markup = types.InlineKeyboardMarkup()
        for i, letter in enumerate(['أ', 'ب', 'ج', 'د']):
            if i < len(options) and options[i]:
                markup.add(types.InlineKeyboardButton(f"{letter}) {md(options[i])}", callback_data=f"ans_{letter}_{q_id}"))

        total, correct, wrong = len(questions), session.get("correct_count", 0), session.get("wrong_count", 0)
        progress_count = int((index / total) * 10) if total else 0
        progress = "▓" * progress_count + "░" * (10 - progress_count)

        header = f"❓ **سؤال ({index + 1}/{total}) - {md(session.get('subject', ''))}**\n📊 {progress} | ✅ {correct} | ❌ {wrong}\n\n"
        if is_admin(user_id): markup.add(types.InlineKeyboardButton("⚙️ لوحة التعديل", callback_data=f"admin_menu_{q_id}"))

        full_text = header + md(text)
        if not message_id: message_id = session.get("q_msg_id")

        if message_id:
            try:
                bot.edit_message_text(full_text, chat_id=chat_id, message_id=message_id, parse_mode="Markdown", reply_markup=markup)
                return
            except Exception: pass

        msg = bot.send_message(chat_id, full_text, parse_mode="Markdown", reply_markup=markup)
        session["q_msg_id"] = msg.message_id
        save_session_to_db(user_id, session)

    def finish_exam(chat_id, user_id, session):
        bot.send_chat_action(chat_id, 'typing')
        total, correct, wrong = len(session.get("question_ids", [])), session.get("correct_count", 0), session.get("wrong_count", 0)
        percent = round((correct / total) * 100, 1) if total > 0 else 0
        status = "🎉 ممتاز / ناجح 🏆" if percent >= 60 else "⚠️ يرجى إعارة المادة مزيداً من الانتباه 💪"

        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("""INSERT INTO quiz_results (user_id, subject, session_name, score, total, percent) VALUES (%s,%s,%s,%s,%s,%s)""", (user_id, session.get("subject", ""), session.get("session_name", ""), correct, total, percent))
            # تحديث مستوى الطالب ونقاطه
            cur.execute("UPDATE users SET xp_points = xp_points + %s WHERE user_id = %s", (correct * 10, user_id))
            conn.commit()
            cur.close()
        except Exception: pass
        finally: release_db(conn)

        wrong_ids = session.get("wrong_ids", [])
        result_text = f"🏁 **انتهى الاختبار!**\n\n📖 المادة: {md(session.get('subject', ''))}\n📊 الصحيحة: {correct}\n❌ الخاطئة: {wrong}\n💯 النسبة: **{percent}%**\n📌 التقييم: **{status}**"

        delete_session(user_id)

        if wrong_ids:
            user_mistakes_cache[user_id] = {"subject": session.get("subject", ""), "session_name": session.get("session_name", ""), "q_ids": wrong_ids}
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔄 إعادة اختبار الأسئلة الخاطئة", callback_data="retry_mistakes"))
            bot.send_message(chat_id, result_text, parse_mode="Markdown", reply_markup=markup)
        else:
            bot.send_message(chat_id, result_text, parse_mode="Markdown", reply_markup=get_student_main_keyboard())

    # ==================== استقبال ضغطة الطالب على الإجابة ====================
    @bot.callback_query_handler(func=lambda call: call.data.startswith("ans_"))
    def handle_answer(call):
        user_id = call.from_user.id
        session = load_session_from_db(user_id)
        if not session: return safe_answer_callback(bot, call.id, "⚠️ انتهت الجلسة.", show_alert=True)

        selected_letter, q_id = call.data.split("_")[1], int(call.data.split("_")[2])
        if q_id != session["question_ids"][session["index"]]:
            return safe_answer_callback(bot, call.id, "⚠️ أجبت مسبقاً.", show_alert=True)

        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("SELECT option_a, option_b, option_c, option_d, correct_option FROM questions WHERE id = %s;", (q_id,))
            row = cur.fetchone()
            cur.close()
        finally: release_db(conn)

        correct_letter = str(row[4]).strip()
        if selected_letter.lower() == correct_letter.lower():
            session["correct_count"] = session.get("correct_count", 0) + 1
            safe_answer_callback(bot, call.id, "✅ إجابة صحيحة! (+10 XP)")
        else:
            session["wrong_count"] = session.get("wrong_count", 0) + 1
            session.setdefault("wrong_ids", []).append(q_id)
            safe_answer_callback(bot, call.id, f"❌ إجابة خاطئة!\nالصحيح ({correct_letter})", show_alert=True)

        session["index"] += 1
        save_session_to_db(user_id, session)
        send_current_question(call.message.chat.id, user_id, session, message_id=call.message.message_id)

    # ==================== بدء الاختبار ====================
    @bot.callback_query_handler(func=lambda call: call.data.startswith("ss_"))
    def handle_session_selection(call):
        parts = call.data.split("_")
        year_num, sem_num, sub_idx, sess_idx = map(int, parts[1:5])
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("SELECT subject FROM questions WHERE year=%s AND semester=%s GROUP BY subject ORDER BY subject ASC", (year_num, sem_num))
            subject_name = cur.fetchall()[sub_idx][0]
            cur.execute("SELECT exam_session FROM questions WHERE year=%s AND semester=%s AND subject=%s GROUP BY exam_session ORDER BY MAX(id) DESC", (year_num, sem_num, subject_name))
            session_name = cur.fetchall()[sess_idx][0]
            cur.execute("SELECT id FROM questions WHERE year=%s AND semester=%s AND subject=%s AND exam_session=%s ORDER BY id ASC", (year_num, sem_num, subject_name, session_name))
            q_ids = [r[0] for r in cur.fetchall()]
            cur.close()
        finally: release_db(conn)

        user_id = call.from_user.id
        save_session_to_db(user_id, {"question_ids": q_ids, "index": 0, "correct_count": 0, "wrong_count": 0, "answered": [], "subject": subject_name, "session_name": session_name})
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception: pass
        safe_answer_callback(bot, call.id, "🚀 بدأ الاختبار!")
        bot.send_message(call.message.chat.id, f"🚀 **بدء اختبار: {md(subject_name)}**\nالأسئلة: {len(q_ids)}", parse_mode="Markdown", reply_markup=get_exam_control_keyboard())
        send_current_question(call.message.chat.id, user_id, load_session_from_db(user_id))
