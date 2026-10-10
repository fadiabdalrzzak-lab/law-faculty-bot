from telebot import types
from config import YEARS, SEMESTERS
from database import get_db, release_db, load_session_from_db, save_session_to_db
from keyboards import get_student_main_keyboard, get_exam_control_keyboard
from utils import md, safe_answer_callback, check_subscription, send_sub_required_msg

def register_student_handlers(bot):

    # ==================== استجابة القائمة الرئيسية الجديدة ====================
    # التعديل الأول هنا في قائمة استقبال الرسائل
    @bot.message_handler(func=lambda msg: msg.text in [
        "🏛 تدريب الدورات المؤتمتة", "📝 الاختبارات", "📚 المكتبة", 
        "🧠 البطاقات التعليمية", "📅 خطة الدراسة", "📈 تقدمي الدراسي", 
        "🏆 الإنجازات", "🤖 المساعد الذكي", "💬 الدعم والملاحظات"
    ])
    def handle_student_menus(message):
        user_id = message.from_user.id
        if not check_subscription(bot, user_id):
            return send_sub_required_msg(bot, message.chat.id)
        
        text = message.text
        try: bot.delete_message(message.chat.id, message.message_id)
        except Exception: pass

        # التعديل الثاني هنا في شرط التحقق
        if text == "🏛 تدريب الدورات المؤتمتة":
            markup = types.InlineKeyboardMarkup()
            for y_num, y_name in YEARS.items():
                markup.add(types.InlineKeyboardButton(y_name, callback_data=f"yr_{y_num}"))
            markup.add(types.InlineKeyboardButton("🏠 إغلاق", callback_data="delete_this_message"))
            bot.send_message(message.chat.id, "🏛 **تدريب الدورات المؤتمتة:**\nاختر السنة الدراسية للبدء:", parse_mode="Markdown", reply_markup=markup)

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

        elif text == "📈 تقدمي الدراسي":
            markup = types.InlineKeyboardMarkup()
            markup.row(types.InlineKeyboardButton("🔖 أسئلتي المحفوظة", callback_data="show_saved"), types.InlineKeyboardButton("📊 إحصائياتي", callback_data="show_stats"))
            markup.add(types.InlineKeyboardButton("🏠 إغلاق", callback_data="delete_this_message"))
            bot.send_message(message.chat.id, "📈 **تقدمي الدراسي:**\nتتبع أدائك ومحفوظاتك من هنا:", parse_mode="Markdown", reply_markup=markup)

        elif text == "💬 الدعم والملاحظات":
            bot.send_message(message.chat.id, "وُلد المشروع ليختصر وقتكم 💙.\nللدعم التقني والمقترحات تواصلوا معي مباشرة:\n👉 @Saqqer10")

        else:
            bot.send_message(message.chat.id, f"🚧 **{text}**\nهذه الميزة قيد البرمجة حالياً ضمن التحديث الاحترافي! ترقبوا إطلاقها قريباً 🚀", parse_mode="Markdown")

    # ==================== التنقل في المواد والدورات ====================
    @bot.callback_query_handler(func=lambda call: call.data == "delete_this_message")
    def handle_delete_msg(call):
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception: pass
        safe_answer_callback(bot, call.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("yr_"))
    def handle_year_selection(call):
        year_num = int(call.data.split("_")[1])
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT semester FROM questions WHERE year=%s ORDER BY semester ASC", (year_num,))
            semesters = [r[0] for r in cur.fetchall()]
            cur.close()
        finally: release_db(conn)

        markup = types.InlineKeyboardMarkup()
        for s in semesters: markup.add(types.InlineKeyboardButton(SEMESTERS[s], callback_data=f"sem_{year_num}_{s}"))
        markup.add(types.InlineKeyboardButton("🏠 إغلاق", callback_data="delete_this_message"))
        bot.edit_message_text(f"🎓 **{YEARS[year_num]}**\nاختر الفصل:", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)
        safe_answer_callback(bot, call.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("sem_"))
    def handle_semester_selection(call):
        _, year_num, sem_num = call.data.split("_")
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("SELECT subject, COUNT(*) as cnt FROM questions WHERE year=%s AND semester=%s GROUP BY subject ORDER BY subject ASC", (int(year_num), int(sem_num)))
            subjects = cur.fetchall()
            cur.close()
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
        year_num, sem_num, sub_idx = int(parts[1]), int(parts[2]), int(parts[3])
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("SELECT subject FROM questions WHERE year=%s AND semester=%s GROUP BY subject ORDER BY subject ASC", (year_num, sem_num))
            subjects = [r[0] for r in cur.fetchall()]
            if sub_idx >= len(subjects): return
            subject_name = subjects[sub_idx]
            cur.execute("SELECT exam_session FROM questions WHERE year=%s AND semester=%s AND subject=%s GROUP BY exam_session ORDER BY MAX(id) DESC", (year_num, sem_num, subject_name))
            sessions = [r[0] for r in cur.fetchall()]
            cur.close()
        finally: release_db(conn)

        markup = types.InlineKeyboardMarkup()
        for s_idx, sess in enumerate(sessions):
            markup.add(types.InlineKeyboardButton(f"🗓️ {sess}", callback_data=f"ss_{year_num}_{sem_num}_{sub_idx}_{s_idx}"))
        markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data=f"sem_{year_num}_{sem_num}"))
        bot.edit_message_text(f"📖 **مادة: {md(subject_name)}**\nاختر الدورة:", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)
        safe_answer_callback(bot, call.id)

    # (بقية مسارات المكتبة pdfy_، pdfs_، pdfb_، getpdf_ ستكون مشابهة تماماً وتعمل بشكل نظيف)
