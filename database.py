import json
from psycopg2.pool import ThreadedConnectionPool
from config import DATABASE_URL

db_pool = None

def init_pool():
    global db_pool
    if db_pool is None:
        db_pool = ThreadedConnectionPool(1, 10, DATABASE_URL)

def get_db(): return db_pool.getconn()

def release_db(conn):
    try: db_pool.putconn(conn)
    except Exception: pass

def init_db():
    conn = get_db()
    try:
        cur = conn.cursor()
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username TEXT, first_name TEXT,
                xp_points INTEGER DEFAULT 0, level INTEGER DEFAULT 1,
                join_date TIMESTAMP DEFAULT NOW()
            );
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id SERIAL PRIMARY KEY, year INTEGER NOT NULL, semester INTEGER NOT NULL DEFAULT 1,
                subject TEXT NOT NULL, exam_session TEXT NOT NULL, question_text TEXT NOT NULL,
                option_a TEXT NOT NULL, option_b TEXT NOT NULL, option_c TEXT NOT NULL, option_d TEXT NOT NULL,
                correct_option TEXT NOT NULL, explanation TEXT
            );
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pdf_files (
                id SERIAL PRIMARY KEY, title TEXT NOT NULL, file_id TEXT NOT NULL,
                year INTEGER, semester INTEGER, subject TEXT, doc_type TEXT DEFAULT 'ملف'
            );
        """)

        cur.execute("CREATE TABLE IF NOT EXISTS saved_questions (user_id BIGINT, question_id INTEGER, PRIMARY KEY (user_id, question_id));")
        cur.execute("CREATE TABLE IF NOT EXISTS quiz_sessions (user_id BIGINT PRIMARY KEY, data JSONB NOT NULL, updated_at TIMESTAMP DEFAULT NOW());")
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS quiz_results (
                id SERIAL PRIMARY KEY, user_id BIGINT, subject TEXT, session_name TEXT,
                score INTEGER, total INTEGER, percent REAL, quiz_type TEXT DEFAULT 'دورة_كاملة',
                taken_at TIMESTAMP DEFAULT NOW()
            );
        """)

        # جدول البطاقات التعليمية المحدث لدعم الفرز حسب السنة والفصل
        cur.execute("""
            CREATE TABLE IF NOT EXISTS flashcards (
                id SERIAL PRIMARY KEY,
                year INTEGER DEFAULT 1,
                semester INTEGER DEFAULT 1,
                subject TEXT NOT NULL,
                front_text TEXT NOT NULL,
                back_text TEXT NOT NULL
            );
        """)
        cur.execute("ALTER TABLE flashcards ADD COLUMN IF NOT EXISTS year INTEGER DEFAULT 1;")
        cur.execute("ALTER TABLE flashcards ADD COLUMN IF NOT EXISTS semester INTEGER DEFAULT 1;")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS study_plans (
                user_id BIGINT PRIMARY KEY, plan_data JSONB NOT NULL, created_at TIMESTAMP DEFAULT NOW()
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS achievements (
                user_id BIGINT, achievement_name TEXT, earned_at TIMESTAMP DEFAULT NOW(),
                PRIMARY KEY (user_id, achievement_name)
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id SERIAL PRIMARY KEY, user_id BIGINT, report_type TEXT, description TEXT,
                status TEXT DEFAULT 'pending', created_at TIMESTAMP DEFAULT NOW()
            );
        """)

        conn.commit()
        cur.close()
    finally:
        release_db(conn)

def save_session_to_db(user_id, data):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("""INSERT INTO quiz_sessions (user_id, data, updated_at) VALUES (%s, %s::jsonb, NOW()) ON CONFLICT (user_id) DO UPDATE SET data=%s::jsonb, updated_at=NOW()""", (user_id, json.dumps(data), json.dumps(data)))
        conn.commit()
        cur.close()
    finally: release_db(conn)

def load_session_from_db(user_id):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT data FROM quiz_sessions WHERE user_id=%s", (user_id,))
        row = cur.fetchone()
        cur.close()
        if not row: return None
        d = row[0]
        if isinstance(d, str): d = json.loads(d)
        return d
    finally: release_db(conn)

def delete_session(user_id):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM quiz_sessions WHERE user_id=%s", (user_id,))
        conn.commit()
        cur.close()
    finally: release_db(conn)
