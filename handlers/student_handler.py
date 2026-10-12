from telebot import types
from config import YEARS, SEMESTERS, OPTION_LETTERS
from database import get_db, release_db
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
                years = [r[0] for r in cur.fetchall()]
                cur.close()
            finally: release_db(conn)
            if not years:
                bot.send_message(message.chat.id, "📑 لا توجد ملفات في المكتبة حالياً.")
                return
            markup = types.InlineKeyboardMarkup()
            for y in years: markup.add(types.InlineKeyboardButton(YEARS[y], callback_data=f"pdfy_{y}"))
            markup.add(types.InlineKeyboardButton("🏠 إغلاق", callback_data="delete_this_message"))
            bot.send_message(message.chat.id, "📚 **المكتبة الأكاديمية:**\nاختر السنة:", parse_mode="Markdown", reply_markup=markup)

        elif text == "🧠 البطاقات التعليمية":
            conn = get_db()
            try:
                cur = conn.cursor()
                cur.execute("SELECT DISTINCT year FROM flashcards ORDER BY year ASC")
                years = [r[0] for r in cur.fetchall()]
                cur.close()
            finally: release_db(conn)
            if not years:
                bot.send_message(message.chat.id, "🧠 لا توجد بطاقات تعليمية مضافة حالياً. ترقبها قريباً!")
                return
            markup = types.InlineKeyboardMarkup()
            for y in years: markup.add(types.InlineKeyboardButton(YEARS[y], callback_data=f"fcy_{y}"))
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
            cur.execute("SELECT DISTINCT semester FROM questions WHERE year=%s ORDER BY semester ASC", (year_num,))
            semesters = [r[0] for r in cur.fetchall()]
            cur.close()
        finally: release_db(conn)
        markup = types.InlineKeyboardMarkup()
        for s in semesters: markup.add(types.InlineKeyboardButton(SEMESTERS[s], callback_data=f"exm_sem_{year_num}_{s}"))
        markup.add(types.InlineKeyboardButton("🏠 إغلاق", callback_data="delete_this_message"))
        bot.edit_message_text(f"🎓 **{YEARS[year_num]}**\nاختر الفصل لمحاكاة الامتحان:", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)
        safe_answer_callback(bot, call.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("exm_sem_"))
    def handle_exm_semester(call):
        _, _, year_num, sem_num = call.data.split("_")
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("SELECT subject, COUNT(*) as cnt FROM questions WHERE year=%s AND semester=%s GROUP BY subject ORDER BY subject ASC", (int(year_num), int(sem_num)))
            subjects = cur.fetchall()
            cur.close()
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
            subject_name = cur.fetchall()[sub_idx][0]
            cur.execute("SELECT exam_session FROM questions WHERE year=%s AND semester=%s AND subject=%s GROUP BY exam_session ORDER BY MAX(id) DESC", (year_num, sem_num, subject_name))
            session_name = cur.fetchall()[sess_idx][0]
            cur.execute("SELECT id FROM questions WHERE year=%s AND semester=%s AND subject=%s AND exam_session=%s ORDER BY id ASC", (year_num, sem_num, subject_name, session_name))
            q_ids = [r[0] for r in cur.fetchall()]
            cur.close()
        finally: release_db(conn)

        user_id = call.from_user.id
        # تم تحديد quiz_type = training
        save_session_to_db(user_id, {"question_ids": q_ids, "index": 0, "correct_count": 0, "wrong_count": 0, "answered": [], "subject": subject_name, "session_name": session_name, "quiz_type": "training"})
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception: pass
        safe_answer_callback(bot, call.id, "🚀 بدأ التدريب!")
        bot.send_message(call.message.chat.id, f"🚀 **بدء التدريب: {md(subject_name)}**\nالأسئلة: {len(q_ids)}", parse_mode="Markdown", reply_markup=get_exam_control_keyboard())
        
        from handlers.exam_handler import send_current_question
        send_current_question(call.message.chat.id, user_id, load_session_from_db(user_id))

    @bot.callback_query_handler(func=lambda call: call.data.startswith("randex_"))
    def handle_random_exam(call):
        parts = call.data.split("_")
        year_num, sem_num, sub_idx = map(int, parts[1:4])
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("SELECT subject FROM questions WHERE year=%s AND semester=%s GROUP BY subject ORDER BY subject ASC", (year_num, sem_num))
            subject_name = cur.fetchall()[sub_idx][0]
            cur.execute("SELECT id FROM questions WHERE year=%s AND semester=%s AND subject=%s ORDER BY RANDOM() LIMIT 50", (year_num, sem_num, subject_name))
            q_ids = [r[0] for r in cur.fetchall()]
            cur.close()
        finally: release_db(conn)

        user_id = call.from_user.id
        if not q_ids: return safe_answer_callback(bot, call.id, "⚠️ لا توجد أسئلة كافية.", show_alert=True)
        
        # تم تحديد quiz_type = exam وتجهيز قاموس الإجابات
        save_session_to_db(user_id, {"question_ids": q_ids, "index": 0, "correct_count": 0, "wrong_count": 0, "answered": [], "subject": subject_name, "session_name": "محاكاة امتحان شامل", "quiz_type": "exam", "answered_dict": {}})
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception: pass
        
        safe_answer_callback(bot, call.id, "⏱️ بدأ الامتحان الشامل!")
        bot.send_message(call.message.chat.id, f"⏱️ **محاكاة امتحان شامل: {md(subject_name)}**\nالأسئلة: {len(q_ids)}\nلا يوجد كشف للإجابات أو مساعدة. ركز جيداً!", parse_mode="Markdown", reply_markup=get_real_exam_control_keyboard())
        
        from handlers.exam_handler import send_current_question
        send_current_question(call.message.chat.id, user_id, load_session_from_db(user_id))

    # ==================== الإعدادات وإحصائيات الطالب (نفس الكود السابق يعمل بكفاءة) ====================
    @bot.callback_query_handler(func=lambda call: call.data.startswith("set_y_"))
    def handle_set_year(call):
        year = int(call.data.split("_")[2])
        markup = types.InlineKeyboardMarkup()
        for s_num, s_name in SEMESTERS.items():
            markup.add(types.InlineKeyboardButton(s_name, callback_data=f"set_s_{year}_{s_num}"))
        markup.add(types.InlineKeyboardButton("🏠 إغلاق", callback_data="delete_this_message"))
        bot.edit_message_text(f"🎓 **{YEARS[year]}**\nالآن اختر الفصل الدراسي الخاص بك:", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)
        safe_answer_callback(bot, call.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("set_s_"))
    def handle_set_sem(call):
        _, _, year, sem = call.data.split("_")
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE users SET academic_year=%s, academic_semester=%s WHERE user_id=%s", (int(year), int(sem), call.from_user.id))
            conn.commit()
            cur.close()
        finally: release_db(conn)
        bot.edit_message_text(f"✅ **تم ضبط إعداداتك بنجاح!**\nسنتك الدراسية: {YEARS[int(year)]} - {SEMESTERS[int(sem)]}", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
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
            # جلب الإحصائيات العامة
            cur.execute("SELECT COUNT(*), AVG(percent) FROM quiz_results WHERE user_id=%s", (user_id,))
            res = cur.fetchone()
            total_quizzes, avg_percent = res if res and res[0] else (0, 0)
            
            cur.execute("SELECT xp_points, level FROM users WHERE user_id=%s", (user_id,))
            user_data = cur.fetchone()
            xp, lvl = user_data if user_data else (0, 1)

            # تحليل مستوى الطالب في كل مادة
            cur.execute("SELECT subject, AVG(percent) FROM quiz_results WHERE user_id=%s GROUP BY subject", (user_id,))
            subject_stats = cur.fetchall()
            cur.close()
        except Exception:
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
                weak_subjects.append(sub)
            elif sub_avg < 80:
                status = "👍 جيد"
            else:
                status = "🌟 ممتاز"

            msg += f"📘 **{md(sub)}**: {sub_avg}%\n   {progress} ({status})\n\n"

        # إضافة زر (تدرب الآن) للمواد الضعيفة
        for w_sub in weak_subjects:
            markup.add(types.InlineKeyboardButton(f"🏋️ تدرب الآن: {w_sub}", callback_data=f"trainow_{w_sub}"))

        # أزرار قادمة للتشويق
        markup.add(types.InlineKeyboardButton("🔥 شعلة المواظبة (قريباً)", callback_data="ignore"))
        markup.add(types.InlineKeyboardButton("🏆 ترتيب الدفعة (قريباً)", callback_data="ignore"))
        markup.add(types.InlineKeyboardButton("🏠 إغلاق", callback_data="delete_this_message"))

        try: bot.edit_message_text(msg, chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)
        except Exception: pass
        safe_answer_callback(bot, call.id)

    # معالجة زر (تدرب الآن) للمواد الضعيفة
    @bot.callback_query_handler(func=lambda call: call.data.startswith("trainow_"))
    def handle_train_now(call):
        subject_name = call.data.split("_", 1)[1]
        conn = get_db()
        try:
            cur = conn.cursor()
            # استخراج معلومات المادة لتوجيه الطالب لدوراتها
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
        finally: release_db(conn)
        if not cards: return safe_answer_callback(bot, call.id, "📂 ليس لديك بطاقات محفوظة.", show_alert=True)
        from handlers.student_handler import send_flashcard
        send_flashcard(bot, call.message.chat.id, user_id, cards, 0, False, call.message.message_id, "البطاقات المحفوظة")
        safe_answer_callback(bot, call.id, "🚀 بدء مراجعة البطاقات المحفوظة!")

    @bot.callback_query_handler(func=lambda call: call.data == "delete_this_message")
    def handle_delete_msg(call):
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception: pass
        safe_answer_callback(bot, call.id)
