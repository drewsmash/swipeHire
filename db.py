"""Database access for SwipeHire.

Every helper opens its own connection, runs one job and closes it again.
Simple, and safe to use from several web requests at the same time.
Credentials come from environment variables (.env / docker-compose.yml).
"""
import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))


def settings():
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", "swipehire_app"),
        "password": os.getenv("DB_PASSWORD", ""),
        "database": os.getenv("DB_NAME", "swipehire"),
    }


def get_connection():
    return mysql.connector.connect(**settings(), time_zone="+00:00",
                                   autocommit=False, connection_timeout=5)


def fetch_all(sql, params=()):
    """Run a SELECT and return a list of dictionaries."""
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute(sql, params)
            return cur.fetchall()
        finally:
            cur.close()
    finally:
        conn.close()


def fetch_one(sql, params=()):
    rows = fetch_all(sql, params)
    return rows[0] if rows else None


def execute(sql, params=()):
    """Run one INSERT/UPDATE/DELETE in a transaction; return the new row id."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        try:
            cur.execute(sql, params)
            conn.commit()
            return cur.lastrowid
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
    finally:
        conn.close()


def transaction(statements):
    """Run several (sql, params) pairs as one transaction. Returns the last row id."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        try:
            last_id = None
            for sql, params in statements:
                cur.execute(sql, params)
                last_id = cur.lastrowid or last_id
            conn.commit()
            return last_id
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
    finally:
        conn.close()


def check_connection():
    try:
        fetch_one("SELECT 1 AS ok")
        return True
    except Exception:
        return False
