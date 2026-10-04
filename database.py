from psycopg2.pool import ThreadedConnectionPool
from config import DATABASE_URL

db_pool = None

def init_pool():
    global db_pool

    if db_pool is None:
        db_pool = ThreadedConnectionPool(
            1,
            20,
            DATABASE_URL
        )

def get_db():
    return db_pool.getconn()

def release_db(conn):
    if conn:
        db_pool.putconn(conn)
