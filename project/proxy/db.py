import mysql.connector
import os
from contextlib import contextmanager

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        user=os.getenv("MYSQL_USER", "anonkorea4869"),
        password=os.getenv("MYSQL_PASSWORD", "anonkorea4869"),
        database=os.getenv("MYSQL_DATABASE", "proxy")
    )

@contextmanager
def get_cursor():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        yield cursor
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def get_db():
    return type('DB', (), {
        'get_cursor': get_cursor,
        'get_connection': get_db_connection
    }) 