    # ==================== استقبال أزرار التحكم بالاختبار (الكيبورد السفلي) ====================
    @bot.message_handler(func=lambda msg: msg.text in [
        "➡️ السؤال التالي", "⬅️ السؤال السابق", "🔄 إعادة الاختبار", 
        "🏁 إنهاء وعرض النتيجة", "💾 حفظ السؤال للمراجعة", 
        "⚠️ الإبلاغ عن خطأ", "📚 الانتقال إلى مادة أخرى", "🏠 القائمة الرئيسية"
    ])
    def handle_exam_control_buttons(message):
        user_id = message.from_user.id
        text = message.text
        session = load_session_from_db(user_id)

        # الخروج من الاختبار والعودة
        if text in ["🏠 القائمة الرئيسية", "📚 الانتقال إلى مادة أخرى"]:
            delete_session(user_id)
            bot.send_message(message.chat.id, "🏠 تمت العودة للرئيسية.", reply_markup=get_student_main_keyboard())
            try: bot.delete_message(message.chat.id, message.message_id)
            except Exception: pass
            return

        if not session:
            bot.send_message(message.chat.id, "⚠️ لا يوجد اختبار نشط حالياً.", reply_markup=get_student_main_keyboard())
            return

        if text == "➡️ السؤال التالي":
            if session["index"] < len(session["question_ids"]) - 1:
                session["index"] += 1
                save_session_to_db(user_id, session)
                send_current_question(message.chat.id, user_id, session)
            else: finish_exam(message.chat.id, user_id, session)
            try: bot.delete_message(message.chat.id, message.message_id)
            except Exception: pass

        elif text == "⬅️ السؤال السابق":
            if session["index"] > 0:
                session["index"] -= 1
                save_session_to_db(user_id, session)
                send_current_question(message.chat.id, user_id, session)
            try: bot.delete_message(message.chat.id, message.message_id)
            except Exception: pass

        elif text == "🔄 إعادة الاختبار":
            session.update({"index": 0, "correct_count": 0, "wrong_count": 0, "answered": []})
            if "wrong_ids" in session: del session["wrong_ids"]
            save_session_to_db(user_id, session)
            bot.send_message(message.chat.id, "🔄 **بداية جديدة! ركز جيداً.**", parse_mode="Markdown")
            send_current_question(message.chat.id, user_id, session)
            try: bot.delete_message(message.chat.id, message.message_id)
            except Exception: pass

        elif text == "🏁 إنهاء وعرض النتيجة":
            q_msg_id = session.get("q_msg_id")
            if q_msg_id:
                try: bot.edit_message_reply_markup(message.chat.id, q_msg_id, reply_markup=None)
                except Exception: pass
            finish_exam(message.chat.id, user_id, session)
            try: bot.delete_message(message.chat.id, message.message_id)
            except Exception: pass

        elif text == "💾 حفظ السؤال للمراجعة":
            q_id = session["question_ids"][session["index"]]
            conn = get_db()
            try:
                cur = conn.cursor()
                cur.execute("""INSERT INTO saved_questions (user_id, question_id) VALUES (%s, %s) ON CONFLICT DO NOTHING""", (user_id, q_id))
                conn.commit()
                cur.close()
            finally: release_db(conn)
            bot.reply_to(message, "✅ **تم حفظ السؤال بنجاح في ملفاتك!**", parse_mode="Markdown")

        elif text == "⚠️ الإبلاغ عن خطأ":
            q_id = session["question_ids"][session["index"]]
            conn = get_db()
            try:
                cur = conn.cursor()
                cur.execute("SELECT subject, exam_session, question_text FROM questions WHERE id = %s;", (q_id,))
                q_data = cur.fetchone()
                cur.close()
            finally: release_db(conn)
            if q_data:
                sub, sess, q_text = q_data
                report_msg = f"⚠️ **بلاغ عن خطأ!**\n👤 **الطالب:** `{user_id}`\n📚 **المادة:** {md(sub)} ({md(sess)})\n🔖 **رقم السؤال:** `{q_id}`\n❓ **النص:**\n{md(q_text)}"
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("⚙️ لوحة التعديل", callback_data=f"admin_menu_{q_id}"))
                for admin_id in ADMIN_IDS:
                    try: bot.send_message(admin_id, report_msg, parse_mode="Markdown", reply_markup=markup)
                    except Exception: pass
                bot.reply_to(message, "📩 تم الإرسال للمراجعة. شكراً لك!")
