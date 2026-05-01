import sqlite3
from config import Config

def get_connection():
    conn = sqlite3.connect(Config.DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        public_key TEXT,
        private_key TEXT
    )
    """)

    cur.execute("""
CREATE TABLE IF NOT EXISTS messages(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender TEXT,
    receiver TEXT,

    wrapped_key_sender BLOB,
    wrapped_key_receiver BLOB,

    nonce BLOB,
    ciphertext BLOB,
    tag BLOB,

    signature BLOB,
    timestamp TEXT
)
""")

    conn.commit()
    conn.close()