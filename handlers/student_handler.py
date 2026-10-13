from telebot import types
from config import YEARS, SEMESTERS, OPTION_LETTERS
from database import get_db, release_db, save_session_to_db, load_session_from_db
from keyboards import get_student_main_keyboard, get_exam_control_keyboard, get_real_exam_control_keyboard
from utils import md, safe_answer_callback, check_subscription, send_sub_required_msg, is_admin
import json

def register_student_handlers(bot):

    @bot.message_handler(func=lambda msg: msg.text in [
        "🏛 تدريب الدورات المؤتمتة", "📝 الاختبارات", "📚 المكتبة", 
        "🧠 البطاقات التعليمية", "📅 خطة الدراسة", "📈 تقدمي الدراسي", 
        "🏆 الإنجازات", "⚙️ إعدادات حسابي", "🤖 المساعد الذكي", "💬 الدعم والملاحظات"
    ])
    def handle_student_menus(message):
        user_id = message.from_user.id
        if not check_subscription(bot, user_id):
            return send_sub_required_msg(bot, message.chat.id)
        
        text = message.text
        try: bot.delete_message(message.chat.id, message.message_id)
        except Exception: pass

        if text == "🏛 تدريب الدورات المؤتمتة":
            markup = types.InlineKeyboardMarkup()
            for y_num, y_name in YEARS.items():
                markup.add(types.InlineKeyboardButton(y_name, callback_data=f"yr_{y_num}"))
            markup.add(types.InlineKeyboardButton("🏠 إغلاق", callback_data="delete_this_message"))
            bot.send_message(message.chat.id, "🏛 **تدريب الدورات المؤتمتة:**\nاختر السنة الدراسية للبدء:", parse_mode="Markdown", reply_markup=markup)

        elif text == "📝 الاختبارات":
            markup = types.InlineKeyboardMarkup()
            for y_num, y_name in YEARS.items():
                markup.add(types.InlineKeyboardButton(y_name, callback_data=f"exm_yr_{y_num}"))
            markup.add(types.InlineKeyboardButton("🏠 إغلاق", callback_data="delete_this_message"))
            bot.send_message(message.chat.id, "⏱️ **محاكاة الاختبارات الشاملة:**\nسيتم توليد امتحان عشوائي من كافة دورات المادة.\nاختر السنة الدراسية:", parse_mode="Markdown", reply_markup=markup)

        elif text == "📚 المكتبة":
            conn = get_db()
            try:
                cur = conn.cursor()
                cur.execute("SELECT DISTINCT year FROM pdf_files WHERE year IS NOT NULL ORDER BY year ASC")
                years = [r[0] for r in cur.fetchall() if r[0] is not None]
                cur.close()
            except Exception as e:
                conn.rollback()
                years = []
            finally: release_db(conn)
            if not years:
                bot.send_message(message.chat.id, "📑 لا توجد ملفات في المكتبة حالياً.")
                return
            markup = types.InlineKeyboardMarkup()
            for y in years: 
                y_name = YEARS.get(y, f"السنة {y}")
                markup.add(types.InlineKeyboardButton(y_name, callback_data=f"pdfy_{y}"))
            markup.add(types.InlineKeyboardButton("🏠 إغلاق", callback_data="delete_this_message"))
            bot.send_message(message.chat.id, "📚 **المكتبة الأكاديمية:**\nاختر السنة:", parse_mode="Markdown", reply_markup=markup)

        elif text == "🧠 البطاقات التعليمية":
            conn = get_db()
            try:
                cur = conn.cursor()
                cur.execute("SELECT DISTINCT year FROM flashcards WHERE year IS NOT NULL ORDER BY year ASC")
                years = [r[0] for r in cur.fetchall() if r[0] is not None]
                cur.close()
            except Exception as e:
                conn.rollback()
                years = []
            finally: release_db(conn)
            if not years:
                bot.send_message(message.chat.id, "🧠 لا توجد بطاقات تعليمية مضافة حالياً. ترقبها قريباً!")
                return
            markup = types.InlineKeyboardMarkup()
            for y in years: 
                y_name = YEARS.get(y, f"السنة {y}")
                markup.add(types.InlineKeyboardButton(y_name, callback_data=f"fcy_{y}"))
            markup.add(types.InlineKeyboardButton("🏠 إغلاق", callback_data="delete_this_message"))
            bot.send_message(message.chat.id, "🧠 **البطاقات التعليمية (Flashcards):**\nاختر السنة الدراسية لمراجعة المصطلحات:", parse_mode="Markdown", reply_markup=markup)

        elif text == "📈 تقدمي الدراسي":
            markup = types.InlineKeyboardMarkup()
            markup.row(types.InlineKeyboardButton("📂 محفوظاتي", callback_data="show_saved"), types.InlineKeyboardButton("📊 إحصائياتي", callback_data="show_stats"))
            markup.add(types.InlineKeyboardButton("🏠 إغلاق", callback_data="delete_this_message"))
            bot.send_message(message.chat.id, "📈 **تقدمي الدراسي:**\nتتبع أدائك ومحفوظاتك من هنا:", parse_mode="Markdown", reply_markup=markup)

        elif text == "⚙️ إعدادات حسابي":
            markup = types.InlineKeyboardMarkup()
            for y_num, y_name in YEARS.items():
                markup.add(types.InlineKeyboardButton(y_name, callback_data=f"set_y_{y_num}"))
            markup.add(types.InlineKeyboardButton("🏠 إغلاق", callback_data="delete_this_message"))
            bot.send_message(message.chat.id, "⚙️ **إعدادات حسابي:**\nاختر سنتك الدراسية ليتم تخصيص تحدي اليوم بناءً عليها:", parse_mode="Markdown", reply_markup=markup)

        elif text == "💬 الدعم والملاحظات":
            bot.send_message(message.chat.id, "وُلد المشروع ليختصر وقتكم 💙.\nللدعم التقني والمقترحات تواصلوا معي مباشرة:\n👉 @Saqqer10")

        else:
            bot.send_message(message.chat.id, f"🚧 **{text}**\nهذه الميزة قيد البرمجة حالياً ضمن التحديث الاحترافي! ترقبوا إطلاقها قريباً 🚀", parse_mode="Markdown")

    # ==================== التنقل في المحاكاة (الاختبار الشامل) ====================
    @bot.callback_query_handler(func=lambda call: call.data.startswith("exm_yr_"))
    def handle_exm_year(call):
        year_num = int(call.data.split("_")[2])
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT semester FROM questions WHERE year=%s AND semester IS NOT NULL ORDER BY semester ASC", (year_num,))
            semesters = [r[0] for r in cur.fetchall() if r[0] is not None]
            cur.close()
        except Exception as e:
            conn.rollback()
            semesters = []
        finally: release_db(conn)
        markup = types.InlineKeyboardMarkup()
        for s in semesters: 
            s_name = SEMESTERS.get(s, f"الفصل {s}")
            markup.add(types.InlineKeyboardButton(s_name, callback_data=f"exm_sem_{year_num}_{s}"))
        markup.add(types.InlineKeyboardButton("🏠 إغلاق", callback_data="delete_this_message"))
        
        y_name = YEARS.get(year_num, f"السنة {year_num}")
        bot.edit_message_text(f"🎓 **{y_name}**\nاختر الفصل لمحاكاة الامتحان:", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)
        safe_answer_callback(bot, call.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("exm_sem_"))
    def handle_exm_semester(call):
        _, _, year_num, sem_num = call.data.split("_")
        year_num, sem_num = int(year_num), int(sem_num)
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("SELECT subject, COUNT(*) as cnt FROM questions WHERE year=%s AND semester=%s GROUP BY subject ORDER BY subject ASC", (year_num, sem_num))
            subjects = cur.fetchall()
            cur.close()
        except Exception as e:
            conn.rollback()
            subjects = []
        finally: release_db(conn)
        markup = types.InlineKeyboardMarkup()
        for idx, (sub_name, cnt) in enumerate(subjects):
            markup.add(types.InlineKeyboardButton(f"📖 {sub_name} (محاكاة)", callback_data=f"randex_{year_num}_{sem_num}_{idx}"))
        markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data=f"exm_yr_{year_num}"))
        bot.edit_message_text(f"📚 **المواد:**\nاختر المادة لتوليد امتحان شامل عشوائي:", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)
        safe_answer_callback(bot, call.id)

    # ==================== بدء الجلسات ====================
    @bot.callback_query_handler(func=lambda call: call.data.startswith("ss_"))
    def handle_session_selection(call):
        parts = call.data.split("_")
        year_num, sem_num, sub_idx, sess_idx = map(int, parts[1:5])
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("SELECT subject FROM questions WHERE year=%s AND semester=%s GROUP BY subject ORDER BY subject ASC", (year_num, sem_num))
            subjects = cur.fetchall()
            if sub_idx >= len(subjects): return safe_answer_callback(bot, call.id, "❌ خطأ في رقم المادة", show_alert=True)
            subject_name = subjects[sub_idx][0]
            
            cur.execute("SELECT exam_session FROM questions WHERE year=%s AND semester=%s AND subject=%s GROUP BY exam_session ORDER BY MAX(id) DESC", (year_num, sem_num, subject_name))
            sessions = cur.fetchall()
            if sess_idx >= len(sessions): return safe_answer_callback(bot, call.id, "❌ خطأ في رقم الدورة", show_alert=True)
            session_name = sessions[sess_idx][0]
            
            cur.execute("SELECT id FROM questions WHERE year=%s AND semester=%s AND subject=%s AND exam_session=%s ORDER BY id ASC", (year_num, sem_num, subject_name, session_name))
            q_ids = [r[0] for r in cur.fetchall()]
            cur.close()
        except Exception as e:
            conn.rollback()
            return safe_answer_callback(bot, call.id, "❌ خطأ في السيرفر", show_alert=True)
        finally: release_db(conn)

        user_id = call.from_user.id
        save_session_to_db(user_id, {"question_ids": q_ids, "index": 0, "correct_count": 0, "wrong_count": 0, "answered": [], "subject": subject_name, "session_name": session_name, "quiz_type": "training"})
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception: pass
        safe_answer_callback(bot, call.id, "🚀 بدأ التدريب!")
        bot.send_message(call.message.chat.id, f"🚀 **بدء التدريب: {md(subject_name)}**\nالأسئلة: {len(q_ids)}", parse_mode="Markdown", reply_markup=get_exam_control_keyboard())
        
        from handlers.exam_handler import send_current_question
        send_current_question(bot, call.message.chat.id, user_id, load_session_from_db(user_id))

    @bot.callback_query_handler(func=lambda call: call.data.startswith("randex_"))
    def handle_random_exam(call):
        parts = call.data.split("_")
        year_num, sem_num, sub_idx = map(int, parts[1:4])
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("SELECT subject FROM questions WHERE year=%s AND semester=%s GROUP BY subject ORDER BY subject ASC", (year_num, sem_num))
            subjects = cur.fetchall()
            if sub_idx >= len(subjects): return safe_answer_callback(bot, call.id, "❌ خطأ، يرجى تحديث القائمة.", show_alert=True)
            subject_name = subjects[sub_idx][0]
            
            cur.execute("SELECT id FROM questions WHERE year=%s AND semester=%s AND subject=%s ORDER BY RANDOM() LIMIT 50", (year_num, sem_num, subject_name))
            q_ids = [r[0] for r in cur.fetchall()]
            cur.close()
        except Exception as e:
            conn.rollback()
            return safe_answer_callback(bot, call.id, "❌ خطأ في السيرفر", show_alert=True)
        finally: release_db(conn)

        user_id = call.from_user.id
        if not q_ids: return safe_answer_callback(bot, call.id, "⚠️ لا توجد أسئلة كافية.", show_alert=True)
        
        save_session_to_db(user_id, {"question_ids": q_ids, "index": 0, "correct_count": 0, "wrong_count": 0, "answered": [], "subject": subject_name, "session_name": "محاكاة امتحان شامل", "quiz_type": "exam", "answered_dict": {}})
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception: pass
        
        safe_answer_callback(bot, call.id, "⏱️ بدأ الامتحان الشامل!")
        bot.send_message(call.message.chat.id, f"⏱️ **محاكاة امتحان شامل: {md(subject_name)}**\nالأسئلة: {len(q_ids)}\nلا يوجد كشف للإجابات أو مساعدة. ركز جيداً!", parse_mode="Markdown", reply_markup=get_real_exam_control_keyboard())
        
        from handlers.exam_handler import send_current_question
        send_current_question(bot, call.message.chat.id, user_id, load_session_from_db(user_id))

    # ==================== الإعدادات وتحديث بيانات الطالب ====================
    @bot.callback_query_handler(func=lambda call: call.data.startswith("set_y_"))
    def handle_set_year(call):
        year = int(call.data.split("_")[2])
        markup = types.InlineKeyboardMarkup()
        for s_num, s_name in SEMESTERS.items():
            markup.add(types.InlineKeyboardButton(s_name, callback_data=f"set_s_{year}_{s_num}"))
        markup.add(types.InlineKeyboardButton("🏠 إغلاق", callback_data="delete_this_message"))
        
        y_name = YEARS.get(year, f"السنة {year}")
        bot.edit_message_text(f"🎓 **{y_name}**\nالآن اختر الفصل الدراسي الخاص بك:", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)
        safe_answer_callback(bot, call.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("set_s_"))
    def handle_set_sem(call):
        _, _, year, sem = call.data.split("_")
        year, sem = int(year), int(sem)
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE users SET academic_year=%s, academic_semester=%s WHERE user_id=%s", (year, sem, call.from_user.id))
            conn.commit()
            cur.close()
        except Exception as e:
            conn.rollback()
        finally: release_db(conn)
        
        y_name = YEARS.get(year, f"السنة {year}")
        s_name = SEMESTERS.get(sem, f"الفصل {sem}")
        bot.edit_message_text(f"✅ **تم ضبط إعداداتك بنجاح!**\nسنتك الدراسية: {y_name} - {s_name}", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
        safe_answer_callback(bot, call.id, "✅ تم تحديث بياناتك!", show_alert=True)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("dc_ans_"))
    def handle_daily_challenge_answer(call):
        _, _, q_id_str, selected_letter = call.data.split("_")
        user_id = call.from_user.id
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("SELECT question_text, correct_option FROM questions WHERE id=%s", (int(q_id_str),))
            row = cur.fetchone()
            if not row: return safe_answer_callback(bot, call.id, "السؤال لم يعد موجوداً.", show_alert=True)
            q_text, correct_letter = row[0], str(row[1]).strip()
            if selected_letter.lower() == correct_letter.lower():
                msg = f"🎉 **إجابة صحيحة بطل!**\nلقد كسبت 20 نقطة XP ✨\n\n❓ {md(q_text)}\n\n✅ الجواب: ({correct_letter})"
                cur.execute("UPDATE users SET xp_points = xp_points + 20 WHERE user_id = %s", (user_id,))
                conn.commit()
                safe_answer_callback(bot, call.id, "إجابة صحيحة! +20 XP", show_alert=True)
            else:
                msg = f"❌ **إجابة خاطئة!**\nلا بأس، الخطأ يعلمنا.\n\n❓ {md(q_text)}\n\n✅ الجواب الصحيح كان: ({correct_letter})"
                safe_answer_callback(bot, call.id, "إجابة خاطئة!", show_alert=True)
        except Exception as e:
            conn.rollback()
            return safe_answer_callback(bot, call.id, "❌ خطأ في السيرفر", show_alert=True)
        finally: release_db(conn)
        try: bot.edit_message_text(msg, chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
        except Exception: pass

    # ==================== الإحصائيات والمحفوظات الشاملة الذكية ====================
    @bot.callback_query_handler(func=lambda call: call.data == "show_stats")
    def handle_show_stats(call):
        user_id = call.from_user.id
        bot.send_chat_action(call.message.chat.id, 'typing')
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*), AVG(percent) FROM quiz_results WHERE user_id=%s", (user_id,))
            res = cur.fetchone()
            total_quizzes, avg_percent = res if res and res[0] else (0, 0)
            
            cur.execute("SELECT xp_points, level FROM users WHERE user_id=%s", (user_id,))
            user_data = cur.fetchone()
            xp, lvl = user_data if user_data else (0, 1)

            cur.execute("SELECT subject, AVG(percent) FROM quiz_results WHERE user_id=%s GROUP BY subject", (user_id,))
            subject_stats = cur.fetchall()
            cur.close()
        except Exception as e:
            conn.rollback()
            print("DB ERROR in show_stats:", e)
            total_quizzes, avg_percent, subject_stats, xp, lvl = 0, 0, [], 0, 1
        finally: release_db(conn)

        markup = types.InlineKeyboardMarkup(row_width=1)

        if not total_quizzes or total_quizzes == 0:
            markup.add(types.InlineKeyboardButton("🏠 إغلاق", callback_data="delete_this_message"))
            bot.edit_message_text("📊 لا توجد إحصائيات مسجلة لك بعد. قم بإجراء أول تدريب لك لتبدأ المنصة بتحليل مستواك!", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)
            return safe_answer_callback(bot, call.id)

        avg_str = f"{round(avg_percent, 1)}%" if avg_percent else "0%"
        msg = f"📈 **تحليل الأداء الذكي:**\n\n🏆 المستوى: **{lvl}** | ✨ النقاط (XP): **{xp}**\n🔢 إجمالي الاختبارات: **{total_quizzes}**\n💯 المتوسط العام: **{avg_str}**\n\n📊 **مؤشر الجاهزية للمواد:**\n"

        weak_subjects = []
        for sub, sub_avg in subject_stats:
            sub_avg = round(sub_avg, 1) if sub_avg else 0
            progress_count = int((sub_avg / 100) * 10)
            progress = "▓" * progress_count + "░" * (10 - progress_count)
            
            if sub_avg < 60:
                status = "⚠️ نقطة ضعف"
                if sub: weak_subjects.append(sub)
            elif sub_avg < 80:
                status = "👍 جيد"
            else:
                status = "🌟 ممتاز"

            safe_sub = md(sub) if sub else "مادة غير معروفة"
            msg += f"📘 **{safe_sub}**: {sub_avg}%\n   {progress} ({status})\n\n"

        for w_sub in weak_subjects:
            markup.add(types.InlineKeyboardButton(f"🏋️ تدرب الآن: {w_sub}", callback_data=f"trainow_{w_sub}"))

        markup.add(types.InlineKeyboardButton("🔥 شعلة المواظبة (قريباً)", callback_data="ignore"))
        markup.add(types.InlineKeyboardButton("🏆 ترتيب الدفعة (قريباً)", callback_data="ignore"))
        markup.add(types.InlineKeyboardButton("🏠 إغلاق", callback_data="delete_this_message"))

        try: bot.edit_message_text(msg, chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)
        except Exception: pass
        safe_answer_callback(bot, call.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("trainow_"))
    def handle_train_now(call):
        subject_name = call.data.split("_", 1)[1]
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("SELECT year, semester FROM questions WHERE subject=%s LIMIT 1", (subject_name,))
            res = cur.fetchone()
            if not res: return safe_answer_callback(bot, call.id, "❌ خطأ", show_alert=True)
            year_num, sem_num = res

            cur.execute("SELECT subject FROM questions WHERE year=%s AND semester=%s GROUP BY subject ORDER BY subject ASC", (year_num, sem_num))
            all_subs = [r[0] for r in cur.fetchall()]
            sub_idx = all_subs.index(subject_name) if subject_name in all_subs else 0

            cur.execute("SELECT exam_session FROM questions WHERE year=%s AND semester=%s AND subject=%s GROUP BY exam_session ORDER BY MAX(id) DESC", (year_num, sem_num, subject_name))
            sessions = [r[0] for r in cur.fetchall()]
            cur.close()
        except Exception as e:
            conn.rollback()
            return safe_answer_callback(bot, call.id, "❌ خطأ في السيرفر", show_alert=True)
        finally: release_db(conn)

        markup = types.InlineKeyboardMarkup()
        for s_idx, sess in enumerate(sessions):
            markup.add(types.InlineKeyboardButton(f"🗓️ {sess}", callback_data=f"ss_{year_num}_{sem_num}_{sub_idx}_{s_idx}"))
        markup.add(types.InlineKeyboardButton("🔙 رجوع للإحصائيات", callback_data="show_stats"))

        bot.edit_message_text(f"🏋️ **تدريب مكثف (معالجة الضعف):**\n📖 المادة: **{md(subject_name)}**\nاختر الدورة للبدء بتقوية نقطة ضعفك ورفع نسبتك:", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)
        safe_answer_callback(bot, call.id)

    @bot.callback_query_handler(func=lambda call: call.data == "show_saved")
    def handle_saved_menu(call):
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("📝 الأسئلة المحفوظة", callback_data="saved_qs"),
            types.InlineKeyboardButton("🧠 البطاقات المحفوظة", callback_data="saved_fcs"),
            types.InlineKeyboardButton("📄 ملفات PDF المحفوظة", callback_data="saved_pdfs"),
            types.InlineKeyboardButton("🏠 إغلاق", callback_data="delete_this_message")
        )
        bot.edit_message_text("📂 **قسم المحفوظات:**\nاختر القسم:", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)
        safe_answer_callback(bot, call.id)

    @bot.callback_query_handler(func=lambda call: call.data == "saved_qs")
    def handle_saved_qs(call):
        user_id = call.from_user.id
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("""SELECT q.id, q.subject, q.exam_session, q.question_text, q.option_a, q.option_b, q.option_c, q.option_d, q.correct_option FROM questions q JOIN saved_questions s ON q.id = s.question_id WHERE s.user_id = %s""", (user_id,))
            saved_qs = cur.fetchall()
            cur.close()
        except Exception as e:
            conn.rollback()
            saved_qs = []
        finally: release_db(conn)
        if not saved_qs: return safe_answer_callback(bot, call.id, "📂 ليس لديك أسئلة محفوظة.", show_alert=True)
        bot.send_message(call.message.chat.id, f"📝 **الأسئلة المحفوظة ({len(saved_qs)}):**", parse_mode="Markdown")
        for q in saved_qs:
            q_id, sub, sess, q_text, a, b, c, d, correct = q
            marks = {"أ": a, "ب": b, "ج": c, "د": d}
            lines = [f"{let}) {marks[let]}{' ✅' if let == correct else ''}" for let in OPTION_LETTERS]
            msg_text = f"📌 **مادة:** {md(sub)} ({md(sess)})\n\n❓ **السؤال:** {md(q_text)}\n\n" + "\n".join(md(l) for l in lines)
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🗑️ إزالة", callback_data=f"unsave_{q_id}"))
            bot.send_message(call.message.chat.id, msg_text, parse_mode="Markdown", reply_markup=markup)
        safe_answer_callback(bot, call.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("unsave_"))
    def handle_unsave(call):
        q_id = int(call.data.split("_")[1])
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM saved_questions WHERE user_id=%s AND question_id=%s", (call.from_user.id, q_id))
            conn.commit()
            cur.close()
        except Exception as e:
            conn.rollback()
        finally: release_db(conn)
        safe_answer_callback(bot, call.id, "🗑️ تمت الإزالة.")
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception: pass

    @bot.callback_query_handler(func=lambda call: call.data == "saved_pdfs")
    def handle_saved_pdfs(call):
        user_id = call.from_user.id
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("SELECT p.id, p.title FROM pdf_files p JOIN saved_pdfs s ON p.id = s.pdf_id WHERE s.user_id = %s ORDER BY p.id DESC", (user_id,))
            pdfs = cur.fetchall()
            cur.close()
        except Exception as e:
            conn.rollback()
            pdfs = []
        finally: release_db(conn)
        if not pdfs: return safe_answer_callback(bot, call.id, "📂 ليس لديك ملفات محفوظة.", show_alert=True)
        markup = types.InlineKeyboardMarkup()
        for pdf_id, title in pdfs:
            markup.row(types.InlineKeyboardButton(f"📄 {title}", callback_data=f"getpdf_{pdf_id}"), types.InlineKeyboardButton("🗑️", callback_data=f"unsavepdf_{pdf_id}"))
        markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="show_saved"))
        bot.edit_message_text("📂 **ملفات PDF المحفوظة:**", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)
        safe_answer_callback(bot, call.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("savepdf_"))
    def handle_save_pdf(call):
        pdf_id = int(call.data.split("_")[1])
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("INSERT INTO saved_pdfs (user_id, pdf_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (call.from_user.id, pdf_id))
            conn.commit()
            cur.close()
        except Exception as e:
            conn.rollback()
        finally: release_db(conn)
        safe_answer_callback(bot, call.id, "✅ تم حفظ الملف في المحفوظات!", show_alert=True)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("unsavepdf_"))
    def handle_unsave_pdf(call):
        pdf_id = int(call.data.split("_")[1])
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM saved_pdfs WHERE user_id=%s AND pdf_id=%s", (call.from_user.id, pdf_id))
            conn.commit()
            cur.close()
        except Exception as e:
            conn.rollback()
        finally: release_db(conn)
        safe_answer_callback(bot, call.id, "🗑️ تمت الإزالة.")
        call.data = "saved_pdfs"
        handle_saved_pdfs(call)

    @bot.callback_query_handler(func=lambda call: call.data == "saved_fcs")
    def handle_saved_fcs(call):
        user_id = call.from_user.id
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("SELECT f.id, f.front_text, f.back_text FROM flashcards f JOIN saved_flashcards s ON f.id = s.flashcard_id WHERE s.user_id = %s ORDER BY f.id ASC", (user_id,))
            cards = cur.fetchall()
            cur.close()
        except Exception as e:
            conn.rollback()
            cards = []
        finally: release_db(conn)
        if not cards: return safe_answer_callback(bot, call.id, "📂 ليس لديك بطاقات محفوظة.", show_alert=True)
        from handlers.student_handler import send_flashcard
        send_flashcard(bot, call.message.chat.id, user_id, cards, 0, False, call.message.message_id, "البطاقات المحفوظة")
        safe_answer_callback(bot, call.id, "🚀 بدء مراجعة البطاقات المحفوظة!")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("savefc_"))
    def handle_save_fc(call):
        card_id = int(call.data.split("_")[1])
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("INSERT INTO saved_flashcards (user_id, flashcard_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (call.from_user.id, card_id))
            conn.commit()
            cur.close()
        except Exception as e:
            conn.rollback()
        finally: release_db(conn)
        safe_answer_callback(bot, call.id, "✅ تم الحفظ في قسم المحفوظات!", show_alert=True)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("unsavefc_"))
    def handle_unsave_fc(call):
        parts = call.data.split("_")
        card_id, index = int(parts[1]), int(parts[2])
        user_id = call.from_user.id
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM saved_flashcards WHERE user_id=%s AND flashcard_id=%s", (user_id, card_id))
            conn.commit()
            cur.execute("SELECT f.id, f.front_text, f.back_text FROM flashcards f JOIN saved_flashcards s ON f.id = s.flashcard_id WHERE s.user_id = %s ORDER BY f.id ASC", (user_id,))
            cards = cur.fetchall()
            cur.close()
        except Exception as e:
            conn.rollback()
            cards = []
        finally: release_db(conn)
        safe_answer_callback(bot, call.id, "🗑️ تمت الإزالة من المحفوظات.", show_alert=True)
        if not cards:
            try: bot.edit_message_text("📂 لا توجد بطاقات محفوظة متبقية.", chat_id=call.message.chat.id, message_id=call.message.message_id)
            except Exception: pass
            return
        if index >= len(cards): index = len(cards) - 1
        send_flashcard(bot, call.message.chat.id, user_id, cards, index, False, call.message.message_id, "البطاقات المحفوظة")

    @bot.callback_query_handler(func=lambda call: call.data == "delete_this_message")
    def handle_delete_msg(call):
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception: pass
        safe_answer_callback(bot, call.id)

    # ==================== التنقل العام (مواد، دورات، مكتبة) ====================
    @bot.callback_query_handler(func=lambda call: call.data.startswith("yr_"))
    def handle_year_selection(call):
        year_num = int(call.data.split("_")[1])
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT semester FROM questions WHERE year=%s AND semester IS NOT NULL ORDER BY semester ASC", (year_num,))
            semesters = [r[0] for r in cur.fetchall() if r[0] is not None]
            cur.close()
        except Exception as e:
            conn.rollback()
            semesters = []
        finally: release_db(conn)
        markup = types.InlineKeyboardMarkup()
        for s in semesters: 
            s_name = SEMESTERS.get(s, f"الفصل {s}")
            markup.add(types.InlineKeyboardButton(s_name, callback_data=f"sem_{year_num}_{s}"))
        markup.add(types.InlineKeyboardButton("🏠 إغلاق", callback_data="delete_this_message"))
        
        y_name = YEARS.get(year_num, f"السنة {year_num}")
        bot.edit_message_text(f"🎓 **{y_name}**\nاختر الفصل:", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)
        safe_answer_callback(bot, call.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("sem_"))
    def handle_semester_selection(call):
        _, year_num, sem_num = call.data.split("_")
        year_num, sem_num = int(year_num), int(sem_num)
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("SELECT subject, COUNT(*) as cnt FROM questions WHERE year=%s AND semester=%s GROUP BY subject ORDER BY subject ASC", (year_num, sem_num))
            subjects = cur.fetchall()
            cur.close()
        except Exception as e:
            conn.rollback()
            subjects = []
        finally: release_db(conn)
        markup = types.InlineKeyboardMarkup()
        for idx, (sub_name, cnt) in enumerate(subjects):
            markup.add(types.InlineKeyboardButton(f"📖 {sub_name} ({cnt})", callback_data=f"sb_{year_num}_{sem_num}_{idx}"))
        markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data=f"yr_{year_num}"))
        bot.edit_message_text(f"📚 **المواد:**\nاختر المادة المطلوب اختبارها:", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)
        safe_answer_callback(bot, call.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("sb_"))
    def handle_subject_selection(call):
        parts = call.data.split("_")
        year_num, sem_num, sub_idx = map(int, parts[1:4])
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("SELECT subject FROM questions WHERE year=%s AND semester=%s GROUP BY subject ORDER BY subject ASC", (year_num, sem_num))
            subjects = cur.fetchall()
            if sub_idx >= len(subjects): return safe_answer_callback(bot, call.id, "❌ خطأ في التحديد", show_alert=True)
            subject_name = subjects[sub_idx][0]
            
            cur.execute("SELECT exam_session FROM questions WHERE year=%s AND semester=%s AND subject=%s GROUP BY exam_session ORDER BY MAX(id) DESC", (year_num, sem_num, subject_name))
            sessions = [r[0] for r in cur.fetchall()]
            cur.close()
        except Exception as e:
            conn.rollback()
            return safe_answer_callback(bot, call.id, "❌ خطأ في قاعدة البيانات", show_alert=True)
        finally: release_db(conn)
        markup = types.InlineKeyboardMarkup()
        for s_idx, sess in enumerate(sessions):
            markup.add(types.InlineKeyboardButton(f"🗓️ {sess}", callback_data=f"ss_{year_num}_{sem_num}_{sub_idx}_{s_idx}"))
        markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data=f"sem_{year_num}_{sem_num}"))
        bot.edit_message_text(f"📖 **مادة: {md(subject_name)}**\nاختر الدورة:", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)
        safe_answer_callback(bot, call.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("pdfy_"))
    def handle_pdf_year(call):
        year_num = int(call.data.split("_")[1])
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT semester FROM pdf_files WHERE year=%s AND semester IS NOT NULL ORDER BY semester ASC", (year_num,))
            semesters = [r[0] for r in cur.fetchall() if r[0] is not None]
            cur.close()
        except Exception as e:
            conn.rollback()
            semesters = []
        finally: release_db(conn)
        markup = types.InlineKeyboardMarkup()
        for s in semesters: 
            s_name = SEMESTERS.get(s, f"الفصل {s}")
            markup.add(types.InlineKeyboardButton(s_name, callback_data=f"pdfs_{year_num}_{s}"))
        markup.add(types.InlineKeyboardButton("🏠 إغلاق", callback_data="delete_this_message"))
        
        y_name = YEARS.get(year_num, f"السنة {year_num}")
        bot.edit_message_text(f"🎓 **{y_name}**\nاختر الفصل:", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)
        safe_answer_callback(bot, call.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("pdfs_"))
    def handle_pdf_semester(call):
        _, year_num, sem_num = call.data.split("_")
        year_num, sem_num = int(year_num), int(sem_num)
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("SELECT subject, COUNT(*) FROM pdf_files WHERE year=%s AND semester=%s GROUP BY subject ORDER BY subject ASC", (year_num, sem_num))
            subjects = cur.fetchall()
            cur.close()
        except Exception as e:
            conn.rollback()
            subjects = []
        finally: release_db(conn)
        markup = types.InlineKeyboardMarkup()
        for idx, (sub, cnt) in enumerate(subjects): markup.add(types.InlineKeyboardButton(f"📖 {sub} ({cnt})", callback_data=f"pdfb_{year_num}_{sem_num}_{idx}"))
        markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data=f"pdfy_{year_num}"))
        
        y_name = YEARS.get(year_num, f"السنة {year_num}")
        s_name = SEMESTERS.get(sem_num, f"الفصل {sem_num}")
        bot.edit_message_text(f"📚 **{y_name} - {s_name}**\nاختر المادة:", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)
        safe_answer_callback(bot, call.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("pdfb_"))
    def handle_pdf_subject(call):
        parts = call.data.split("_")
        year_num, sem_num, sub_idx = map(int, parts[1:4])
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT subject FROM pdf_files WHERE year=%s AND semester=%s ORDER BY subject ASC", (year_num, sem_num))
            subjects = cur.fetchall()
            if sub_idx >= len(subjects): return safe_answer_callback(bot, call.id, "❌ خطأ في الاختيار", show_alert=True)
            subject_name = subjects[sub_idx][0]
            
            cur.execute("SELECT id, title FROM pdf_files WHERE year=%s AND semester=%s AND subject=%s ORDER BY id DESC", (year_num, sem_num, subject_name))
            pdfs = cur.fetchall()
            cur.close()
        except Exception as e:
            conn.rollback()
            return safe_answer_callback(bot, call.id, "❌ خطأ في قاعدة البيانات", show_alert=True)
        finally: release_db(conn)
        markup = types.InlineKeyboardMarkup()
                for pdf_id, title in pdfs:
            row = [
                types.InlineKeyboardButton(f"📄 {title}", callback_data=f"getpdf_{pdf_id}"),
                types.InlineKeyboardButton("🔖 حفظ", callback_data=f"savepdf_{pdf_id}")
            ]
            if is_admin(call.from_user.id): 
                row.append(types.InlineKeyboardButton("🗑️", callback_data=f"delpdf_{pdf_id}_{year_num}_{sem_num}_{sub_idx}"))
            markup.row(*row)

        markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data=f"pdfs_{year_num}_{sem_num}"))
        bot.edit_message_text(f"📄 **{subject_name}:**", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)
        safe_answer_callback(bot, call.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("getpdf_"))
    def handle_get_pdf(call):
        pdf_id = int(call.data.split("_")[1])
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("SELECT title, file_id FROM pdf_files WHERE id=%s", (pdf_id,))
            res = cur.fetchone()
            cur.close()
        except Exception as e:
            conn.rollback()
            res = None
        finally: release_db(conn)
        if res:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔖 حفظ الملف في المحفوظات", callback_data=f"savepdf_{pdf_id}"))
            bot.send_document(call.message.chat.id, res[1], caption=f"📄 **{md(res[0])}**", parse_mode="Markdown", reply_markup=markup)
            safe_answer_callback(bot, call.id, "تم الإرسال!")
        else: safe_answer_callback(bot, call.id, "❌ غير موجود.", show_alert=True)

    # ==================== البطاقات التعليمية التفاعلية ====================
    @bot.callback_query_handler(func=lambda call: call.data.startswith("fcy_"))
    def handle_fc_year(call):
        year_num = int(call.data.split("_")[1])
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT semester FROM flashcards WHERE year=%s AND semester IS NOT NULL ORDER BY semester ASC", (year_num,))
            semesters = [r[0] for r in cur.fetchall() if r[0] is not None]
            cur.close()
        except Exception as e:
            conn.rollback()
            semesters = []
        finally: release_db(conn)
        markup = types.InlineKeyboardMarkup()
        for s in semesters: 
            s_name = SEMESTERS.get(s, f"الفصل {s}")
            markup.add(types.InlineKeyboardButton(s_name, callback_data=f"fcs_{year_num}_{s}"))
        markup.add(types.InlineKeyboardButton("🏠 إغلاق", callback_data="delete_this_message"))
        
        y_name = YEARS.get(year_num, f"السنة {year_num}")
        bot.edit_message_text(f"🧠 **{y_name}**\nاختر الفصل للبطاقات:", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)
        safe_answer_callback(bot, call.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("fcs_"))
    def handle_fc_semester(call):
        _, year_num, sem_num = call.data.split("_")
        year_num, sem_num = int(year_num), int(sem_num)
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("SELECT subject, COUNT(*) FROM flashcards WHERE year=%s AND semester=%s GROUP BY subject ORDER BY subject ASC", (year_num, sem_num))
            subjects = cur.fetchall()
            cur.close()
        except Exception as e:
            conn.rollback()
            subjects = []
        finally: release_db(conn)
        markup = types.InlineKeyboardMarkup()
        for idx, (sub, cnt) in enumerate(subjects): markup.add(types.InlineKeyboardButton(f"📖 {sub} ({cnt} بطاقة)", callback_data=f"fcb_{year_num}_{sem_num}_{idx}"))
        markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data=f"fcy_{year_num}"))
        bot.edit_message_text(f"🧠 **اختر المادة للمراجعة السريعة:**", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)
        safe_answer_callback(bot, call.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("fcb_"))
    def handle_fc_start(call):
        parts = call.data.split("_")
        year_num, sem_num, sub_idx = map(int, parts[1:4])
        user_id = call.from_user.id
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT subject FROM flashcards WHERE year=%s AND semester=%s ORDER BY subject ASC", (year_num, sem_num))
            subjects = cur.fetchall()
            if sub_idx >= len(subjects): return safe_answer_callback(bot, call.id, "❌ خطأ في القائمة", show_alert=True)
            subject_name = subjects[sub_idx][0]
            
            cur.execute("SELECT id, front_text, back_text FROM flashcards WHERE year=%s AND semester=%s AND subject=%s ORDER BY id ASC", (year_num, sem_num, subject_name))
            cards = cur.fetchall()
            cur.close()
        except Exception as e:
            conn.rollback()
            return safe_answer_callback(bot, call.id, "❌ خطأ في قاعدة البيانات", show_alert=True)
        finally: release_db(conn)
        if not cards: return safe_answer_callback(bot, call.id, "لا توجد بطاقات.", show_alert=True)
        send_flashcard(bot, call.message.chat.id, user_id, cards, 0, show_back=False, message_id=call.message.message_id, subject=subject_name)
        safe_answer_callback(bot, call.id, "🚀 بدأت المراجعة!")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("fcact_"))
    def handle_fc_action(call):
        parts = call.data.split("_")
        idx = int(parts[1])
        show_back = int(parts[2]) == 1
        subject_name = "_".join(parts[3:])
        user_id = call.from_user.id
        conn = get_db()
        try:
            cur = conn.cursor()
            if subject_name == "البطاقات المحفوظة":
                cur.execute("SELECT f.id, f.front_text, f.back_text FROM flashcards f JOIN saved_flashcards s ON f.id = s.flashcard_id WHERE s.user_id = %s ORDER BY f.id ASC", (user_id,))
            else:
                cur.execute("SELECT id, front_text, back_text FROM flashcards WHERE subject=%s ORDER BY id ASC", (subject_name,))
            cards = cur.fetchall()
            cur.close()
        except Exception as e:
            conn.rollback()
            cards = []
        finally: release_db(conn)
        if not cards or idx >= len(cards) or idx < 0: return safe_answer_callback(bot, call.id, "انتهت البطاقات.", show_alert=True)
        send_flashcard(bot, call.message.chat.id, user_id, cards, idx, show_back, message_id=call.message.message_id, subject=subject_name)
        safe_answer_callback(bot, call.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("fcdel_"))
    def handle_fc_delete(call):
        if not is_admin(call.from_user.id): 
            return safe_answer_callback(bot, call.id, "⚠️ مخصص للمشرف فقط.", show_alert=True)
        parts = call.data.split("_")
        card_id, index = int(parts[1]), int(parts[2])
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("SELECT subject FROM flashcards WHERE id=%s", (card_id,))
            res = cur.fetchone()
            if not res: return safe_answer_callback(bot, call.id, "❌ البطاقة غير موجودة أصلاً.", show_alert=True)
            subject_name = res[0]
            cur.execute("DELETE FROM flashcards WHERE id=%s", (card_id,))
            conn.commit()
            cur.execute("SELECT id, front_text, back_text FROM flashcards WHERE subject=%s ORDER BY id ASC", (subject_name,))
            cards = cur.fetchall()
            cur.close()
        except Exception as e:
            conn.rollback()
            return safe_answer_callback(bot, call.id, "❌ خطأ في السيرفر", show_alert=True)
        finally: release_db(conn)
        safe_answer_callback(bot, call.id, "✅ تم حذف البطاقة بنجاح!", show_alert=True)
        if not cards:
            try: bot.edit_message_text("🗑️ تم حذف جميع البطاقات الخاصة بهذه المادة.", chat_id=call.message.chat.id, message_id=call.message.message_id)
            except Exception: pass
            return
        if index >= len(cards): index = len(cards) - 1
        send_flashcard(bot, call.message.chat.id, call.from_user.id, cards, index, False, call.message.message_id, subject_name)

def send_flashcard(bot, chat_id, user_id, cards, index, show_back, message_id, subject):
    total = len(cards)
    card = cards[index]
    text = f"🧠 **مراجعة: {md(subject)}** ({index + 1}/{total})\n\n"
    if not show_back:
        text += f"❓ **المصطلح / السؤال:**\n{md(card[1])}"
    else:
        text += f"✅ **التعريف / الجواب:**\n{md(card[2])}"
    markup = types.InlineKeyboardMarkup(row_width=2)
    if not show_back:
        markup.add(types.InlineKeyboardButton("🔄 تقليب البطاقة", callback_data=f"fcact_{index}_1_{subject}"))
    else:
        markup.add(types.InlineKeyboardButton("🔙 العودة للوجه الأول", callback_data=f"fcact_{index}_0_{subject}"))
    nav = []
    if index > 0: nav.append(types.InlineKeyboardButton("⬅️ السابق", callback_data=f"fcact_{index-1}_0_{subject}"))
    if index < total - 1: nav.append(types.InlineKeyboardButton("التالي ➡️", callback_data=f"fcact_{index+1}_0_{subject}"))
    if nav: markup.row(*nav)
    if subject == "البطاقات المحفوظة":
        markup.add(types.InlineKeyboardButton("🗑️ إزالة من المحفوظات", callback_data=f"unsavefc_{card[0]}_{index}"))
    else:
        markup.add(types.InlineKeyboardButton("🔖 حفظ البطاقة للمراجعة", callback_data=f"savefc_{card[0]}"))
    if is_admin(user_id) and subject != "البطاقات المحفوظة":
        markup.add(types.InlineKeyboardButton("🗑️ حذف هذه البطاقة (للأدمن)", callback_data=f"fcdel_{card[0]}_{index}"))
    markup.add(types.InlineKeyboardButton("🏠 خروج من المراجعة", callback_data="delete_this_message"))
    if message_id:
        try: bot.edit_message_text(text, chat_id, message_id, parse_mode="Markdown", reply_markup=markup)
        except Exception: pass
    else: bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)
