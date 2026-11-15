import mysql.connector
from config import Config

def get_db_connection():
    """Return a new MySQL connection."""
    return mysql.connector.connect(
        host=Config.DB_HOST,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME
    )

def execute_query(query, params=None, fetch=False):
    """
    Execute SQL query.
    - fetch=True   -> returns list of dict rows (for SELECT)
    - fetch=False  -> commits and returns lastrowid (for INSERT/UPDATE)
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, params or ())
        if fetch:
            result = cursor.fetchall()
            return result
        conn.commit()
        return cursor.lastrowid
    finally:
        cursor.close()
        conn.close()