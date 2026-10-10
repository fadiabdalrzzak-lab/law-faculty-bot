import io
import time
import math
import pandas as pd
from telebot import types, apihelper
from config import YEARS, SEMESTERS, OPTION_LETTERS, OPTION_MAP, admin_states, MNG_Q_PER_PAGE, ADMIN_IDS
from database import get_db, release_db
from keyboards import get_admin_main_keyboard, get_years_keyboard, get_semesters_keyboard, get_correct_option_keyboard, get_student_main_keyboard, get_cancel_keyboard
from utils import md, safe_answer_callback, is_admin

def show_mng_questions_page(bot, chat_id, year_num, sem_num, sub_idx, page=1, message_id=None):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT subject FROM questions WHERE year=%s AND semester=%s ORDER BY subject", (year_num, sem_num))
        subjects = [r[0] for r in cur.fetchall()]
        if sub_idx >= len(subjects): return
        subject_name = subjects[sub_idx]
        cur.execute("SELECT id, exam_session, question_text, correct_option FROM questions WHERE year=%s AND semester=%s AND subject=%s ORDER BY id ASC", (year_num, sem_num, subject_name))
        questions = cur.fetchall()
        cur.close()
    finally: release_db(conn)

    if not questions:
        bot.send_message(chat_id, f"لا توجد أسئلة لمادة ({subject_name}).")
        return

    total_pages = math.ceil(len(questions) / MNG_Q_PER_PAGE)
    page = max(1, min(page, total_pages))
    start = (page - 1) * MNG_Q_PER_PAGE
    current_qs = questions[start:start + MNG_Q_PER_PAGE]

    text = f"📋 **({subject_name}) - صفحة {page}/{total_pages}:**\n\n"
    markup = types.InlineKeyboardMarkup()
    for idx, q in enumerate(current_qs, start=start + 1):
        text += f"**{idx}.** 🗓️ {q[1]} | ✔️ ({q[3]})\n❓ {md(q[2])}\n\n"
        markup.add(types.InlineKeyboardButton(f"🗑️ حذف رقم {idx}", callback_data=f"delq_{q[0]}_{year_num}_{sem_num}_{sub_idx}_{page}"))

    nav = []
    if page > 1: nav.append(types.InlineKeyboardButton("⬅️", callback_data=f"mngp_{year_num}_{sem_num}_{sub_idx}_{page-1}"))
    nav.append(types.InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="ignore"))
    if page < total_pages: nav.append(types.InlineKeyboardButton("➡️", callback_data=f"mngp_{year_num}_{sem_num}_{sub_idx}_{page+1}"))
    markup.row(*nav)
    markup.add(types.InlineKeyboardButton("🏠 إغلاق", callback_data="delete_this_message"))

    if message_id:
        try: bot.edit_message_text(text, chat_id, message_id, parse_mode="Markdown", reply_markup=markup)
        except Exception: pass
    else: bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)

def register_admin_handlers(bot):

    @bot.message_handler(func=lambda msg: is_admin(msg.from_user.id) and msg.text in ["❌ إلغاء العملية", "🏠 القائمة الرئيسية"])
    def cancel_admin_action(message):
        admin_states.pop(message.from_user.id, None)
        bot.send_message(message.chat.id, "تمت العودة بنجاح 🛡️.", reply_markup=get_admin_main_keyboard())

    @bot.message_handler(commands=['fix'])
    def fix_question_answer(message):
        if not is_admin(message.from_user.id): return
        try:
            args = message.text.split()
            if len(args) < 3:
                return bot.reply_to(message, "⚠️ **الاستخدام:**\n`/fix [رقم_السؤال] [الحرف_الصحيح]`", parse_mode="Markdown")
            q_id, new_corr = int(args[1]), args[2].strip()
            if new_corr not in ['أ', 'ب', 'ج', 'د']:
                return bot.reply_to(message, "⚠️ الخيار يجب أن يكون: أ، ب، ج، د")
            conn = get_db()
            try:
                cur = conn.cursor()
                cur.execute("UPDATE questions SET correct_option = %s WHERE id = %s;", (new_corr, q_id))
                conn.commit()
                cur.close()
                bot.reply_to(message, f"✅ تم التحديث لتكون الإجابة: (**{new_corr}**)", parse_mode="Markdown")
            finally: release_db(conn)
        except Exception as e: bot.reply_to(message, f"❌ خطأ: {e}")

    @bot.message_handler(func=lambda msg: is_admin(msg.from_user.id) and msg.text in [
        "📥 رفع أسئلة (Excel/CSV)", "📝 إضافة سؤال فردي", "📊 إحصائيات البوت", 
        "🗑️ إدارة/حذف الأسئلة", "🗂️ حذف دورة كاملة", "📄 رفع ملف PDF جديد", 
        "📢 إذاعة للجميع", "📤 تصدير الأسئلة (Excel)", "📚 قائمة سنوات الحقوق",
        "📇 إدارة البطاقات"
    ])
    def admin_main_menus(message):
        user_id = message.from_user.id
        text = message.text

        if text == "📥 رفع أسئلة (Excel/CSV)":
            admin_states[user_id] = {"step": "EXCEL_ASK_SESSION"}
            bot.send_message(message.chat.id, "📥 **رفع أسئلة**\n✏️ **أرسل اسم الدورة** لتعميمه، أو أرسل الملف مباشرة.", parse_mode="Markdown", reply_markup=get_cancel_keyboard())
        elif text == "📝 إضافة سؤال فردي":
            admin_states[user_id] = {"step": "SELECT_YEAR"}
            bot.send_message(message.chat.id, "📝 اختر السنة:", reply_markup=get_years_keyboard())
        elif text == "📄 رفع ملف PDF جديد":
            admin_states[user_id] = {"step": "PDF_SELECT_YEAR"}
            bot.send_message(message.chat.id, "📄 اختر سنة الملف:", reply_markup=get_years_keyboard())
        elif text == "📇 إدارة البطاقات":
            admin_states[user_id] = {"step": "FC_SELECT_YEAR"}
            bot.send_message(message.chat.id, "📇 **إضافة بطاقات تعليمية:**\nاختر السنة:", reply_markup=get_years_keyboard())
        elif text == "📢 إذاعة للجميع":
            admin_states[user_id] = {"step": "BROADCAST"}
            bot.send_message(message.chat.id, "📢 أرسل الرسالة التي تود إذاعتها:", reply_markup=get_cancel_keyboard())
        elif text == "📊 إحصائيات البوت":
            conn = get_db()
            try:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM users")
                u_count = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM questions")
                q_count = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM pdf_files")
                p_count = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM flashcards")
                fc_count = cur.fetchone()[0]
                cur.close()
            finally: release_db(conn)
            bot.send_message(message.chat.id, f"📊 **الإحصائيات:**\n👥 الطلاب: {u_count}\n📚 الأسئلة: {q_count}\n📄 الملفات: {p_count}\n📇 البطاقات: {fc_count}", parse_mode="Markdown")
        elif text == "📤 تصدير الأسئلة (Excel)":
            bot.send_message(message.chat.id, "🔄 جاري التصدير...")
            conn = get_db()
            try:
                df = pd.read_sql("SELECT year, semester, subject, exam_session, question_text, option_a, option_b, option_c, option_d, correct_option FROM questions ORDER BY year, semester, subject", conn)
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer: df.to_excel(writer, index=False, sheet_name='Questions')
                output.seek(0)
                bot.send_document(message.chat.id, (f"questions_backup.xlsx", output), caption="📤 **ملف الأسئلة**", parse_mode="Markdown")
            except Exception as e: bot.send_message(message.chat.id, f"❌ خطأ: `{e}`", parse_mode="Markdown")
            finally: release_db(conn)
        elif text == "📚 قائمة سنوات الحقوق":
            bot.send_message(message.chat.id, "تم عرض القائمة السفلية للطلاب:", reply_markup=get_student_main_keyboard())
        elif text == "🗑️ إدارة/حذف الأسئلة":
            markup = types.InlineKeyboardMarkup()
            for y in YEARS: markup.add(types.InlineKeyboardButton(YEARS[y], callback_data=f"mngyr_{y}"))
            markup.add(types.InlineKeyboardButton("🏠 إغلاق", callback_data="delete_this_message"))
            bot.send_message(message.chat.id, "🗑️ **إدارة الأسئلة:** اختر السنة:", parse_mode="Markdown", reply_markup=markup)
        elif text == "🗂️ حذف دورة كاملة":
            markup = types.InlineKeyboardMarkup()
            for y_num, y_name in YEARS.items(): markup.add(types.InlineKeyboardButton(y_name, callback_data=f"ds_y_{y_num}"))
            markup.add(types.InlineKeyboardButton("🏠 إغلاق", callback_data="delete_this_message"))
            bot.send_message(message.chat.id, "🗂️ **حذف دورة:** اختر السنة:", parse_mode="Markdown", reply_markup=markup)

    @bot.message_handler(content_types=['document'], func=lambda msg: is_admin(msg.from_user.id))
    def handle_admin_docs(message):
        user_id = message.from_user.id
        state = admin_states.get(user_id, {})
        step = state.get("step")

        if step in ["EXCEL_ASK_SESSION", "EXCEL_QUESTIONS_UPLOAD"]:
            file_name = message.document.file_name.lower()
            if not file_name.endswith(('.xlsx', '.xls', '.csv')):
                return bot.send_message(message.chat.id, "⚠️ أرسل صيغة `.xlsx` أو `.csv` فقط.")
            bot.send_message(message.chat.id, "🔄 جاري القراءة...")
            try:
                file_info = bot.get_file(message.document.file_id)
                downloaded_file = bot.download_file(file_info.file_path)
                df = pd.read_excel(io.BytesIO(downloaded_file)) if file_name.endswith(('.xlsx', '.xls')) else pd.read_csv(io.BytesIO(downloaded_file))
                df.fillna('', inplace=True)
                df.columns = df.columns.str.strip().str.lower()
                
                override_session = state.get("session_name")
                conn, inserted = get_db(), 0
                try:
                    cur = conn.cursor()
                    for idx, row in df.iterrows():
                        raw_opt = str(row.get('correct_option', '')).strip().upper()
                        norm_opt = OPTION_MAP.get(raw_opt, raw_opt)
                        if norm_opt not in OPTION_LETTERS: continue
                        sess_val = override_session if override_session else str(row.get('exam_session', '')).strip()
                        cur.execute("""INSERT INTO questions (year, semester, subject, exam_session, question_text, option_a, option_b, option_c, option_d, correct_option) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""", (int(row.get('year', 1)), int(row.get('semester', 1)), str(row.get('subject', '')).strip(), sess_val, str(row.get('question_text', '')).strip(), str(row.get('option_a', '')).strip(), str(row.get('option_b', '')).strip(), str(row.get('option_c', '')).strip(), str(row.get('option_d', '')).strip(), norm_opt))
                        inserted += 1
                    conn.commit()
                    cur.close()
                finally: release_db(conn)
                admin_states.pop(user_id, None)
                bot.send_message(message.chat.id, f"✅ تم إدخال **{inserted}** سؤال!", parse_mode="Markdown", reply_markup=get_admin_main_keyboard())
            except Exception as e:
                bot.send_message(message.chat.id, f"❌ خطأ: `{e}`\nتأكد من تنسيق الأعمدة.", parse_mode="Markdown")
        
        elif step == "ADD_PDF_FILE":
            conn = get_db()
            try:
                cur = conn.cursor()
                cur.execute("INSERT INTO pdf_files (title, file_id, year, semester, subject) VALUES (%s,%s,%s,%s,%s)", (message.document.file_name, message.document.file_id, state["year"], state["semester"], state["subject"]))
                conn.commit()
                cur.close()
            finally: release_db(conn)
            admin_states.pop(user_id, None)
            bot.send_message(message.chat.id, f"✅ تم إضافة **{message.document.file_name}**!", parse_mode="Markdown", reply_markup=get_admin_main_keyboard())
            
        elif step == "FC_FRONT":
            # خيار رفع البطاقات عبر Excel
            file_name = message.document.file_name.lower()
            if not file_name.endswith(('.xlsx', '.xls', '.csv')):
                return bot.send_message(message.chat.id, "⚠️ يرجى إرسال ملف Excel بصيغة `.xlsx`.")
            bot.send_message(message.chat.id, "🔄 جاري قراءة ملف البطاقات...")
            try:
                file_info = bot.get_file(message.document.file_id)
                downloaded_file = bot.download_file(file_info.file_path)
                df = pd.read_excel(io.BytesIO(downloaded_file)) if file_name.endswith(('.xlsx', '.xls')) else pd.read_csv(io.BytesIO(downloaded_file))
                df.fillna('', inplace=True)
                
                if len(df.columns) < 2:
                    return bot.send_message(message.chat.id, "❌ الملف يجب أن يحتوي على عمودين على الأقل (المصطلح، التعريف).")
                    
                conn = get_db()
                inserted = 0
                try:
                    cur = conn.cursor()
                    for idx, row in df.iterrows():
                        front = str(row.iloc[0]).strip()
                        back = str(row.iloc[1]).strip()
                        if front and back:
                            cur.execute("INSERT INTO flashcards (year, semester, subject, front_text, back_text) VALUES (%s, %s, %s, %s, %s)", (state["year"], state["semester"], state["subject"], front, back))
                            inserted += 1
                    conn.commit()
                    cur.close()
                finally: release_db(conn)
                admin_states.pop(user_id, None)
                bot.send_message(message.chat.id, f"✅ تم إدخال **{inserted}** بطاقة تعليمية بنجاح!", parse_mode="Markdown", reply_markup=get_admin_main_keyboard())
            except Exception as e:
                bot.send_message(message.chat.id, f"❌ خطأ: `{e}`", parse_mode="Markdown")

    @bot.message_handler(func=lambda msg: is_admin(msg.from_user.id) and msg.from_user.id in admin_states)
    def handle_admin_states(message):
        user_id = message.from_user.id
        state = admin_states[user_id]
        step = state.get("step")
        text = message.text

        if step == "EXCEL_ASK_SESSION":
            admin_states[user_id] = {"step": "EXCEL_QUESTIONS_UPLOAD", "session_name": text}
            bot.send_message(message.chat.id, f"✅ الدورة: **{text}**\n📥 **أرسل ملف الإكسل:**", parse_mode="Markdown")
        elif step == "BROADCAST":
            admin_states[user_id] = {"step": "CONFIRM_BROADCAST", "msg_id": message.message_id}
            markup = types.InlineKeyboardMarkup()
            markup.row(types.InlineKeyboardButton("✅ نعم، أرسل", callback_data="confirm_bcast"), types.InlineKeyboardButton("❌ إلغاء", callback_data="cancel_bcast"))
            bot.send_message(message.chat.id, "⚠️ **تأكيد الإذاعة لجميع الطلاب؟**", parse_mode="Markdown", reply_markup=markup, reply_to_message_id=message.message_id)
        elif step == "SELECT_YEAR":
            year_map = {v: k for k, v in YEARS.items()}
            if text in year_map:
                state["year"], state["step"] = year_map[text], "SELECT_SEMESTER"
                bot.send_message(message.chat.id, f"📌 **{text}**\nاختر الفصل:", reply_markup=get_semesters_keyboard())
        elif step == "SELECT_SEMESTER":
            sem_map = {v: k for k, v in SEMESTERS.items()}
            if text in sem_map:
                state["semester"], state["step"] = sem_map[text], "ENTER_SUBJECT"
                bot.send_message(message.chat.id, f"📅 **{text}**\nاكتب المادة:", reply_markup=get_cancel_keyboard())
        elif step == "ENTER_SUBJECT":
            state["subject"], state["step"] = text, "ENTER_SESSION"
            bot.send_message(message.chat.id, f"✅ **المادة:** {text}\nاكتب الدورة:")
        elif step == "ENTER_SESSION":
            state["session"], state["step"] = text, "ENTER_QUESTION"
            bot.send_message(message.chat.id, f"🗓️ **الدورة:** {text}\nاكتب نص السؤال:")
        elif step == "ENTER_QUESTION":
            state["question_text"], state["step"] = text, "ENTER_OPT_A"
            bot.send_message(message.chat.id, "اكتب الخيار (أ):")
        elif step == "ENTER_OPT_A":
            state["option_a"], state["step"] = text, "ENTER_OPT_B"
            bot.send_message(message.chat.id, "اكتب الخيار (ب):")
        elif step == "ENTER_OPT_B":
            state["option_b"], state["step"] = text, "ENTER_OPT_C"
            bot.send_message(message.chat.id, "اكتب الخيار (ج):")
        elif step == "ENTER_OPT_C":
            state["option_c"], state["step"] = text, "ENTER_OPT_D"
            bot.send_message(message.chat.id, "اكتب الخيار (د):")
        elif step == "ENTER_OPT_D":
            state["option_d"], state["step"] = text, "ENTER_CORRECT"
            bot.send_message(message.chat.id, "اختر الإجابة الصحيحة:", reply_markup=get_correct_option_keyboard())
        elif step == "ENTER_CORRECT":
            if text not in OPTION_LETTERS: return bot.send_message(message.chat.id, "⚠️ اضغط (أ/ب/ج/د).")
            conn = get_db()
            try:
                cur = conn.cursor()
                cur.execute("""INSERT INTO questions (year, semester, subject, exam_session, question_text, option_a, option_b, option_c, option_d, correct_option) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", (state["year"], state["semester"], state["subject"], state["session"], state["question_text"], state["option_a"], state["option_b"], state["option_c"], state["option_d"], text))
                conn.commit()
                cur.close()
            finally: release_db(conn)
            bot.send_message(message.chat.id, f"✅ **تمت الإضافة!** الجواب: ({text})", parse_mode="Markdown", reply_markup=get_cancel_keyboard())
            state["step"] = "ENTER_QUESTION"
            bot.send_message(message.chat.id, "➕ اكتب نص السؤال التالي:")
        elif step == "PDF_SELECT_YEAR":
            year_map = {v: k for k, v in YEARS.items()}
            if text in year_map:
                state["year"], state["step"] = year_map[text], "PDF_SELECT_SEMESTER"
                bot.send_message(message.chat.id, f"📌 **{text}**\nاختر الفصل:", reply_markup=get_semesters_keyboard())
        elif step == "PDF_SELECT_SEMESTER":
            sem_map = {v: k for k, v in SEMESTERS.items()}
            if text in sem_map:
                state["semester"], state["step"] = sem_map[text], "PDF_ENTER_SUBJECT"
                bot.send_message(message.chat.id, f"📅 **{text}**\nاكتب مادة الملف:", reply_markup=get_cancel_keyboard())
        elif step == "PDF_ENTER_SUBJECT":
            state["subject"], state["step"] = text, "ADD_PDF_FILE"
            bot.send_message(message.chat.id, f"✅ **المادة:** {text}\nأرسل ملف PDF:")
        elif step == "FC_SELECT_YEAR":
            year_map = {v: k for k, v in YEARS.items()}
            if text in year_map:
                state["year"], state["step"] = year_map[text], "FC_SELECT_SEMESTER"
                bot.send_message(message.chat.id, f"📌 **{text}**\nاختر الفصل:", reply_markup=get_semesters_keyboard())
        elif step == "FC_SELECT_SEMESTER":
            sem_map = {v: k for k, v in SEMESTERS.items()}
            if text in sem_map:
                state["semester"], state["step"] = sem_map[text], "FC_ENTER_SUBJECT"
                bot.send_message(message.chat.id, f"📅 **{text}**\nاكتب اسم المادة للبطاقة:", reply_markup=get_cancel_keyboard())
        elif step == "FC_ENTER_SUBJECT":
            state["subject"], state["step"] = text, "FC_FRONT"
            bot.send_message(message.chat.id, f"✅ **المادة:** {text}\n\n📝 **لإضافة البطاقات لديك خياران:**\n1️⃣ أرسل **ملف Excel** يحتوي على عمودين (المصطلح، التعريف) لرفعها دفعة واحدة.\n2️⃣ أو أرسل **الوجه الأول** للبطاقة الآن لإضافتها يدوياً:", parse_mode="Markdown")
        elif step == "FC_FRONT":
            state["front"], state["step"] = text, "FC_BACK"
            bot.send_message(message.chat.id, "🔄 أرسل الآن **الوجه الثاني** للبطاقة (التعريف أو الجواب):")
        elif step == "FC_BACK":
            conn = get_db()
            try:
                cur = conn.cursor()
                cur.execute("INSERT INTO flashcards (year, semester, subject, front_text, back_text) VALUES (%s, %s, %s, %s, %s)", (state["year"], state["semester"], state["subject"], state["front"], text))
                conn.commit()
                cur.close()
            finally: release_db(conn)
            bot.send_message(message.chat.id, "✅ **تم حفظ البطاقة بنجاح!**\n\n📝 أرسل **الوجه الأول** للبطاقة التالية (لنفس المادة):", parse_mode="Markdown")
            state["step"] = "FC_FRONT"

    @bot.callback_query_handler(func=lambda call: call.data in ["confirm_bcast", "cancel_bcast"])
    def handle_broadcast_confirmation(call):
        if not is_admin(call.from_user.id): return
        if call.data == "cancel_bcast":
            admin_states.pop(call.from_user.id, None)
            bot.edit_message_text("❌ تم الإلغاء.", chat_id=call.message.chat.id, message_id=call.message.message_id)
            return safe_answer_callback(bot, call.id)
        if call.data == "confirm_bcast":
            state = admin_states.get(call.from_user.id, {})
            if state.get("step") != "CONFIRM_BROADCAST": return safe_answer_callback(bot, call.id, "⚠️ الجلسة منتهية.", show_alert=True)
            msg_id_to_broadcast = state.get("msg_id")
            admin_states.pop(call.from_user.id, None)
            bot.edit_message_text("🔄 جاري الإذاعة...", chat_id=call.message.chat.id, message_id=call.message.message_id)
            conn = get_db()
            try:
                cur = conn.cursor()
                cur.execute("SELECT user_id FROM users")
                users = [u[0] for u in cur.fetchall()]
                cur.close()
            finally: release_db(conn)
            success, failed, blocked = 0, 0, []
            for u_id in users:
                try:
                    bot.copy_message(u_id, call.message.chat.id, msg_id_to_broadcast)
                    success += 1
                    time.sleep(0.04)
                except apihelper.ApiTelegramException as e:
                    failed += 1
                    if e.error_code in [403, 400]: blocked.append(u_id)
                except Exception: failed += 1
            if blocked:
                conn = get_db()
                try:
                    cur = conn.cursor()
                    cur.executemany("DELETE FROM users WHERE user_id = %s", [(uid,) for uid in blocked])
                    conn.commit()
                    cur.close()
                finally: release_db(conn)
            bot.send_message(call.message.chat.id, f"📊 **تقرير الإذاعة:**\n✅ تم بنجاح: {success}\n❌ فشل: {failed}\n🧹 حسابات محذوفة: {len(blocked)}", parse_mode="Markdown")
            safe_answer_callback(bot, call.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("mngyr_"))
    def handle_mng_year(call):
        year_num = int(call.data.split("_")[1])
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT semester FROM questions WHERE year=%s ORDER BY semester", (year_num,))
            semesters = [r[0] for r in cur.fetchall()]
            cur.close()
        finally: release_db(conn)
        markup = types.InlineKeyboardMarkup()
        for s in semesters: markup.add(types.InlineKeyboardButton(SEMESTERS[s], callback_data=f"mngsm_{year_num}_{s}"))
        markup.add(types.InlineKeyboardButton("🏠 إغلاق", callback_data="delete_this_message"))
        bot.edit_message_text(f"🗑️ **{YEARS[year_num]}:** اختر الفصل:", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)
        safe_answer_callback(bot, call.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("mngsm_"))
    def handle_mng_semester(call):
        _, year_num, sem_num = call.data.split("_")
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT subject FROM questions WHERE year=%s AND semester=%s ORDER BY subject", (int(year_num), int(sem_num)))
            subjects = [r[0] for r in cur.fetchall()]
            cur.close()
        finally: release_db(conn)
        markup = types.InlineKeyboardMarkup()
        for idx, sub in enumerate(subjects): markup.add(types.InlineKeyboardButton(sub, callback_data=f"mngsb_{year_num}_{sem_num}_{idx}"))
        markup.add(types.InlineKeyboardButton("🏠 إغلاق", callback_data="delete_this_message"))
        bot.edit_message_text("🗑️ اختر المادة:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)
        safe_answer_callback(bot, call.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("mngsb_"))
    def handle_mng_subject(call):
        _, year_num, sem_num, sub_idx = call.data.split("_")
        show_mng_questions_page(bot, call.message.chat.id, int(year_num), int(sem_num), int(sub_idx), page=1, message_id=call.message.message_id)
        safe_answer_callback(bot, call.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("mngp_"))
    def handle_mng_page(call):
        _, year_num, sem_num, sub_idx, page = call.data.split("_")
        show_mng_questions_page(bot, call.message.chat.id, int(year_num), int(sem_num), int(sub_idx), page=int(page), message_id=call.message.message_id)
        safe_answer_callback(bot, call.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("delq_"))
    def handle_delete_question_bulk(call):
        if not is_admin(call.from_user.id): return
        parts = call.data.split("_")
        q_id = int(parts[1])
        ctx = parts[2:] if len(parts) > 2 else []
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM questions WHERE id=%s", (q_id,))
            cur.execute("DELETE FROM saved_questions WHERE question_id=%s", (q_id,))
            conn.commit()
            cur.close()
        finally: release_db(conn)
        safe_answer_callback(bot, call.id, "✅ تم الحذف!", show_alert=True)
        if len(ctx) >= 4:
            year_num, sem_num, sub_idx, page = map(int, ctx)
            show_mng_questions_page(bot, call.message.chat.id, year_num, sem_num, sub_idx, page=page, message_id=call.message.message_id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("ds_"))
    def handle_delete_session_flow(call):
        if not is_admin(call.from_user.id): return
        if call.data.startswith("ds_y_"):
            year_num = int(call.data.split("_")[2])
            markup = types.InlineKeyboardMarkup()
            for s_num in [1, 2]: markup.add(types.InlineKeyboardButton(SEMESTERS[s_num], callback_data=f"ds_s_{year_num}_{s_num}"))
            markup.add(types.InlineKeyboardButton("🏠 إغلاق", callback_data="delete_this_message"))
            bot.edit_message_text(f"🎓 **{YEARS[year_num]}:** اختر الفصل:", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)
            safe_answer_callback(bot, call.id)
        elif call.data.startswith("ds_s_"):
            _, _, year_num, sem_num = call.data.split("_")
            year_num, sem_num = int(year_num), int(sem_num)
            conn = get_db()
            try:
                cur = conn.cursor()
                cur.execute("SELECT subject FROM questions WHERE year=%s AND semester=%s GROUP BY subject ORDER BY subject ASC", (year_num, sem_num))
                subjects = [r[0] for r in cur.fetchall()]
                cur.close()
            finally: release_db(conn)
            if not subjects: return safe_answer_callback(bot, call.id, "لا توجد مواد.", show_alert=True)
            markup = types.InlineKeyboardMarkup()
            for idx, sub in enumerate(subjects): markup.add(types.InlineKeyboardButton(f"📘 {sub}", callback_data=f"ds_sub_{year_num}_{sem_num}_{idx}"))
            markup.add(types.InlineKeyboardButton("🏠 إغلاق", callback_data="delete_this_message"))
            bot.edit_message_text("🗑️ اختر المادة:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)
            safe_answer_callback(bot, call.id)
        elif call.data.startswith("ds_sub_"):
            parts = call.data.split("_")
            year_num, sem_num, sub_idx = int(parts[2]), int(parts[3]), int(parts[4])
            conn = get_db()
            try:
                cur = conn.cursor()
                cur.execute("SELECT subject FROM questions WHERE year=%s AND semester=%s GROUP BY subject ORDER BY subject ASC", (year_num, sem_num))
                subject_name = cur.fetchall()[sub_idx][0]
                cur.execute("SELECT exam_session, COUNT(id) FROM questions WHERE year=%s AND semester=%s AND subject=%s GROUP BY exam_session ORDER BY MAX(id) DESC", (year_num, sem_num, subject_name))
                sessions = cur.fetchall()
                cur.close()
            finally: release_db(conn)
            if not sessions: return safe_answer_callback(bot, call.id, "لا توجد دورات.", show_alert=True)
            markup = types.InlineKeyboardMarkup()
            for s_idx, (sess, cnt) in enumerate(sessions): markup.add(types.InlineKeyboardButton(f"🗑️ دورة {sess} ({cnt})", callback_data=f"ds_ask_{year_num}_{sem_num}_{sub_idx}_{s_idx}"))
            markup.add(types.InlineKeyboardButton("🏠 إغلاق", callback_data="delete_this_message"))
            bot.edit_message_text(f"⚠️ **مادة: {md(subject_name)}**\nاختر الدورة للحذف:", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)
            safe_answer_callback(bot, call.id)
        elif call.data.startswith("ds_ask_"):
            parts = call.data.split("_")
            year_num, sem_num, sub_idx, s_idx = int(parts[2]), int(parts[3]), int(parts[4]), int(parts[5])
            conn = get_db()
            try:
                cur = conn.cursor()
                cur.execute("SELECT subject FROM questions WHERE year=%s AND semester=%s GROUP BY subject ORDER BY subject ASC", (year_num, sem_num))
                subject_name = cur.fetchall()[sub_idx][0]
                cur.execute("SELECT exam_session FROM questions WHERE year=%s AND semester=%s AND subject=%s GROUP BY exam_session ORDER BY MAX(id) DESC", (year_num, sem_num, subject_name))
                session_name = cur.fetchall()[s_idx][0]
                cur.close()
            finally: release_db(conn)
            markup = types.InlineKeyboardMarkup()
            markup.row(types.InlineKeyboardButton("✅ نعم، احذفها", callback_data=f"ds_do_{year_num}_{sem_num}_{sub_idx}_{s_idx}"), types.InlineKeyboardButton("❌ تراجع", callback_data=f"ds_sub_{year_num}_{sem_num}_{sub_idx}"))
            bot.edit_message_text(f"🚨 **تأكيد الحذف:**\nهل أنت متأكد من حذف دورة **({md(session_name)})** بالكامل؟", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)
            safe_answer_callback(bot, call.id)
        elif call.data.startswith("ds_do_"):
            parts = call.data.split("_")
            year_num, sem_num, sub_idx, s_idx = int(parts[2]), int(parts[3]), int(parts[4]), int(parts[5])
            conn = get_db()
            try:
                cur = conn.cursor()
                cur.execute("SELECT subject FROM questions WHERE year=%s AND semester=%s GROUP BY subject ORDER BY subject ASC", (year_num, sem_num))
                subject_name = cur.fetchall()[sub_idx][0]
                cur.execute("SELECT exam_session FROM questions WHERE year=%s AND semester=%s AND subject=%s GROUP BY exam_session ORDER BY MAX(id) DESC", (year_num, sem_num, subject_name))
                session_name = cur.fetchall()[s_idx][0]
                cur.execute("DELETE FROM saved_questions WHERE question_id IN (SELECT id FROM questions WHERE year=%s AND semester=%s AND subject=%s AND exam_session=%s)", (year_num, sem_num, subject_name, session_name))
                cur.execute("DELETE FROM questions WHERE year=%s AND semester=%s AND subject=%s AND exam_session=%s", (year_num, sem_num, subject_name, session_name))
                count = cur.rowcount
                conn.commit()
                cur.close()
            finally: release_db(conn)
            safe_answer_callback(bot, call.id, "✅ تم حذف الدورة بنجاح!", show_alert=True)
            bot.edit_message_text(f"🗑️ تم الحذف: **({md(session_name)})** - {count} سؤال.", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")
