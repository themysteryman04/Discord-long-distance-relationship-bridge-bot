import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Heroku automatically sets this env variable
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_connection():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

async def init_db():
    """Initializes tables in PostgreSQL."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 1. Table for Daily Questions
            cur.execute("""
                CREATE TABLE IF NOT EXISTS answers (
                    question_id TEXT,
                    user_id BIGINT,
                    username TEXT,
                    content TEXT,
                    PRIMARY KEY (question_id, user_id)
                )
            """)
            
            # 2. Table for Us-Bucks (Wallet)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    balance INTEGER DEFAULT 0
                )
            """)
            
            # 3. Table for Bounties
            cur.execute("""
                CREATE TABLE IF NOT EXISTS bounties (
                    message_id BIGSERIAL PRIMARY KEY,
                    description TEXT,
                    reward INTEGER,
                    status TEXT DEFAULT 'OPEN',
                    claimed_by TEXT
                )
            """)

            # 4. Table for Truth or Dare
            cur.execute("""
                CREATE TABLE IF NOT EXISTS dares (
                    dare_id TEXT PRIMARY KEY,
                    challenger_id BIGINT,
                    victim_id BIGINT,
                    task TEXT,
                    reward INTEGER,
                    status TEXT DEFAULT 'PENDING' 
                )
            """)

            # 5. Table for Wiki (Memory System)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS wiki (
                    key_name TEXT PRIMARY KEY,
                    content TEXT,
                    attachment_data TEXT,
                    added_by TEXT
                )
            """)

            # 6. Table for Moments (Time Capsule)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS moments (
                    moment_id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT,
                    caption TEXT,
                    attachment_data TEXT,
                    timestamp TEXT,
                    source TEXT
                )
            """)

            # 7. Audio Capsules Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS audio_capsules (
                    id BIGSERIAL PRIMARY KEY,
                    sender_id BIGINT,
                    attachment_url TEXT,
                    label TEXT,
                    deliver_at TEXT,
                    status TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        conn.commit()
    finally:
        conn.close()

# --- DAILY QUESTION FUNCTIONS ---

async def save_answer(q_id, user_id, username, content):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Save the text answer
            cur.execute("""
                INSERT INTO answers (question_id, user_id, username, content)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (question_id, user_id) 
                DO UPDATE SET content = EXCLUDED.content, username = EXCLUDED.username
            """, (q_id, user_id, username, content))
            
            # Add 10 Us-Bucks reward
            cur.execute("""
                INSERT INTO users (user_id, balance) VALUES (%s, 10)
                ON CONFLICT (user_id) DO UPDATE SET balance = users.balance + 10
            """, (user_id,))
        conn.commit()
    finally:
        conn.close()

async def get_answers(q_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT username, content FROM answers WHERE question_id = %s", (q_id,))
            return cur.fetchall()
    finally:
        conn.close()

# --- ECONOMY FUNCTIONS ---

async def get_balance(user_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT balance FROM users WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            return row[0] if row else 0
    finally:
        conn.close()

async def purchase_item(user_id, cost):
    """Safely attempts to buy an item."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Check balance
            cur.execute("SELECT balance FROM users WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            current_balance = row[0] if row else 0
        
            if current_balance < cost:
                return False
            
            # Deduct balance
            new_balance = current_balance - cost
            cur.execute("UPDATE users SET balance = %s WHERE user_id = %s", (new_balance, user_id))
        conn.commit()
        return True
    finally:
        conn.close()

async def add_money(user_id, amount):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (user_id, balance) VALUES (%s, %s)
                ON CONFLICT (user_id) DO UPDATE SET balance = users.balance + %s
            """, (user_id, amount, amount))
        conn.commit()
    finally:
        conn.close()

# --- WIKI FUNCTIONS ---

async def set_wiki_entry(key, content, attachment_data, user_name):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO wiki (key_name, content, attachment_data, added_by) 
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (key_name) DO UPDATE SET 
                    content=EXCLUDED.content, 
                    attachment_data=EXCLUDED.attachment_data,
                    added_by=EXCLUDED.added_by
            """, (key.lower(), content, attachment_data, user_name))
        conn.commit()
    finally:
        conn.close()

async def get_wiki_entry(key):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT content, attachment_data FROM wiki WHERE key_name = %s", (key.lower(),))
            return cur.fetchone()
    finally:
        conn.close()

async def get_all_wiki_keys():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT key_name FROM wiki ORDER BY key_name ASC")
            rows = cur.fetchall()
            return [row[0] for row in rows]
    finally:
        conn.close()

# --- TRUTH OR DARE FUNCTIONS ---

async def create_dare(d_id, challenger_id, task, reward):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO dares (dare_id, challenger_id, task, reward)
                VALUES (%s, %s, %s, %s)
            """, (d_id, challenger_id, task, reward))
        conn.commit()
    finally:
        conn.close()

async def update_dare_status(d_id, status, victim_id=None):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = "UPDATE dares SET status = %s"
            params = [status]
            
            if victim_id:
                sql += ", victim_id = %s"
                params.append(victim_id)
                
            sql += " WHERE dare_id = %s"
            params.append(d_id)
            
            cur.execute(sql, tuple(params))
        conn.commit()
    finally:
        conn.close()

# --- MOMENTS (BeReal) FUNCTIONS ---

async def add_moment(user_id, caption, attachment_data, timestamp, source):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO moments (user_id, caption, attachment_data, timestamp, source)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, caption, attachment_data, timestamp, source))
        conn.commit()
    finally:
        conn.close()

async def get_random_moment():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id, caption, attachment_data, timestamp FROM moments ORDER BY RANDOM() LIMIT 1")
            return cur.fetchone()
    finally:
        conn.close()

# --- AUDIO CAPSULE FUNCTIONs ---
async def add_capsule(sender_id, url, label, deliver_at, status):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO audio_capsules (sender_id, attachment_url, label, deliver_at, status, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
                RETURNING id
            """, (sender_id, url, label, deliver_at, status))
            new_id = cur.fetchone()[0]
        conn.commit()
        return new_id
    finally:
        conn.close()

async def get_pending_capsules():
    """For restoring scheduled jobs on bot restart."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, sender_id, attachment_url, deliver_at FROM audio_capsules WHERE status = 'PENDING'")
            return cur.fetchall()
    finally:
        conn.close()

async def get_open_when_capsule(label):
    """Finds an undelivered capsule with a specific label."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, sender_id, attachment_url FROM audio_capsules 
                WHERE label = %s AND status = 'OPEN_WHEN'
                ORDER BY created_at ASC LIMIT 1
            """, (label,))
            return cur.fetchone()
    finally:
        conn.close()

async def mark_capsule_delivered(c_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE audio_capsules SET status = 'ARCHIVED' WHERE id = %s", (c_id,))
        conn.commit()
    finally:
        conn.close()

async def get_mixtape_list():
    """Returns list of archived/delivered messages."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT sender_id, label, created_at FROM audio_capsules WHERE status = 'ARCHIVED' ORDER BY created_at DESC LIMIT 10")
            return cur.fetchall()
    finally:
        conn.close()

# --- STATS FUNCTIONS ---

async def get_dashboard_stats(todays_date_str):
    """
    Returns a dictionary of all stats needed for the dashboard.
    todays_date_str format: "YYYY-MM-DD" (to find today's question)
    """
    stats = {}
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 1. Active Dares (In Progress or Waiting Approval)
            cur.execute("SELECT COUNT(*) FROM dares WHERE status IN ('IN_PROGRESS', 'WAITING_APPROVAL')")
            stats['active_dares'] = cur.fetchone()[0]

            # 2. Open Bounties
            cur.execute("SELECT COUNT(*) FROM bounties WHERE status = 'OPEN'")
            stats['open_bounties'] = cur.fetchone()[0]

            # 3. Buried Treasure (Pending Capsules)
            cur.execute("SELECT COUNT(*) FROM audio_capsules WHERE status = 'PENDING'")
            stats['buried_capsules'] = cur.fetchone()[0]

            # 4. Daily Question Status
            # question_id format is "YYYY-MM-DD_HH-MM-SS"
            query_pattern = f"{todays_date_str}%"
            cur.execute("SELECT COUNT(DISTINCT user_id) FROM answers WHERE question_id LIKE %s", (query_pattern,))
            stats['daily_q_count'] = cur.fetchone()[0]
            
    finally:
        conn.close()

    return stats