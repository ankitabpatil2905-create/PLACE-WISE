import os
import pymysql
import pymysql.cursors
from dotenv import load_dotenv

load_dotenv()

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "root123")
MYSQL_DB = os.getenv("MYSQL_DB", "student_placement_db")


def get_connection(database=MYSQL_DB):
    """Establishes and returns a new MySQL connection with DictCursor."""
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )


def check_mysql_health():
    """Checks MySQL connection and returns status dict."""
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT VERSION() AS version;")
            row = cur.fetchone()
            version = row["version"] if row else "Unknown"
            cur.execute("SHOW TABLES;")
            tables = [list(r.values())[0] for r in cur.fetchall()]
        conn.close()
        return {
            "status": "connected",
            "database": MYSQL_DB,
            "version": version,
            "tables": tables,
            "table_count": len(tables)
        }
    except Exception as e:
        return {
            "status": "error",
            "database": MYSQL_DB,
            "error": str(e)
        }


def query_all(sql, params=None):
    """Executes a SELECT query and returns all matching rows as dictionaries."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()
    finally:
        conn.close()


def query_one(sql, params=None):
    """Executes a SELECT query and returns a single row as dictionary, or None."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchone()
    finally:
        conn.close()


def execute_sql(sql, params=None):
    """
    Executes an INSERT, UPDATE, or DELETE query.
    Returns a dict with 'last_insert_id' and 'rowcount'.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            affected = cur.execute(sql, params or ())
            last_id = cur.lastrowid
            return {"last_insert_id": last_id, "rowcount": affected}
    finally:
        conn.close()
