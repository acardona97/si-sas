# -*- coding: utf-8 -*-
"""
Sí S.A.S. — Auth module
Gestión de usuarios con SQLite + werkzeug password hashing.
"""
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))   # .../src/
PROJECT_DIR = os.path.dirname(BASE_DIR)                  # .../si_sas_proyecto/
DATA_DIR = os.path.join(PROJECT_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "users.db")

PLAN_LABELS = {
    "basic":       "Básico",
    "standard":    "Estándar",
    "abogado":     "Abogado",
    "premium":     "Premium",
    "corporativo": "Corporativo",
    "admin":       "Administrador",
}

PLAN_PRICES = {
    "basic":       "$ 350.000",
    "standard":    "$ 750.000",
    "abogado":     "$1.000.000",
    "premium":     "$1.600.000",
    "corporativo": "$1.800.000",
    "admin":       "—",
}


def get_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Crea tablas si no existen."""
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            email        TEXT    UNIQUE NOT NULL,
            password_hash TEXT   NOT NULL,
            nombre       TEXT    DEFAULT '',
            plan         TEXT    DEFAULT 'basic',
            active       INTEGER DEFAULT 1,
            generaciones_disponibles INTEGER DEFAULT 0,
            created_at   TEXT    DEFAULT (datetime('now'))
        )
    """)
    # Migración: agregar columna si la tabla ya existía sin ella
    try:
        conn.execute("ALTER TABLE users ADD COLUMN generaciones_disponibles INTEGER DEFAULT 0")
    except Exception:
        pass
    conn.commit()
    conn.close()


def seed_admin(email, password):
    """Crea o actualiza el usuario administrador desde env vars."""
    if not email or not password:
        return
    conn = get_db()
    ph = generate_password_hash(password)
    existing = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
    if existing:
        conn.execute(
            "UPDATE users SET password_hash=?, plan='admin', active=1, generaciones_disponibles=NULL WHERE email=?",
            (ph, email)
        )
    else:
        conn.execute(
            "INSERT INTO users (email, password_hash, nombre, plan, generaciones_disponibles) "
            "VALUES (?, ?, 'Administrador', 'admin', NULL)",
            (email, ph)
        )
    conn.commit()
    conn.close()


def seed_staff_user(email, password, nombre=""):
    """Crea o actualiza usuario staff interno (ilimitado, plan admin)."""
    if not email or not password:
        return
    conn = get_db()
    ph = generate_password_hash(password)
    nombre_default = nombre or email.split("@")[0]
    existing = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
    if existing:
        conn.execute(
            "UPDATE users SET password_hash=?, plan='admin', active=1, generaciones_disponibles=NULL WHERE email=?",
            (ph, email)
        )
    else:
        conn.execute(
            "INSERT INTO users (email, password_hash, nombre, plan, generaciones_disponibles) "
            "VALUES (?, ?, ?, 'admin', NULL)",
            (email, ph, nombre_default)
        )
    conn.commit()
    conn.close()


def get_user_by_id(user_id):
    conn = get_db()
    u = conn.execute("SELECT * FROM users WHERE id=?", (int(user_id),)).fetchone()
    conn.close()
    return dict(u) if u else None


def get_user_by_email(email):
    conn = get_db()
    u = conn.execute("SELECT * FROM users WHERE email=?", (email.strip().lower(),)).fetchone()
    conn.close()
    return dict(u) if u else None


def verify_password(email, password):
    """Autentica usuario. Devuelve dict del usuario o None."""
    user = get_user_by_email(email)
    if not user or not user["active"]:
        return None
    if check_password_hash(user["password_hash"], password):
        return user
    return None


def create_user(email, password, nombre="", plan="basic"):
    """Registra nuevo usuario. Devuelve dict o None si email ya existe."""
    try:
        conn = get_db()
        ph = generate_password_hash(password)
        conn.execute(
            "INSERT INTO users (email, password_hash, nombre, plan) VALUES (?, ?, ?, ?)",
            (email.strip().lower(), ph, nombre, plan)
        )
        conn.commit()
        u = conn.execute("SELECT * FROM users WHERE email=?", (email.strip().lower(),)).fetchone()
        conn.close()
        return dict(u)
    except sqlite3.IntegrityError:
        return None


def get_all_users():
    conn = get_db()
    rows = conn.execute(
        "SELECT id, email, nombre, plan, active, generaciones_disponibles, created_at "
        "FROM users ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_user_plan(user_id, plan):
    conn = get_db()
    conn.execute("UPDATE users SET plan=? WHERE id=?", (plan, int(user_id)))
    conn.commit()
    conn.close()


def set_user_active(user_id, active):
    conn = get_db()
    conn.execute("UPDATE users SET active=? WHERE id=?", (int(active), int(user_id)))
    conn.commit()
    conn.close()


def check_puede_generar(user_id):
    """True si puede generar: NULL = ilimitado, N > 0 = tiene créditos."""
    user = get_user_by_id(user_id)
    if not user:
        return False
    gen = user.get("generaciones_disponibles")
    return gen is None or gen > 0


def decrement_generacion(user_id):
    """Resta 1 generación. No afecta si es NULL (ilimitado)."""
    conn = get_db()
    conn.execute(
        "UPDATE users SET generaciones_disponibles = generaciones_disponibles - 1 "
        "WHERE id=? AND generaciones_disponibles IS NOT NULL AND generaciones_disponibles > 0",
        (int(user_id),)
    )
    conn.commit()
    conn.close()


def set_generaciones(user_id, n):
    """Asigna generaciones disponibles. n=None → ilimitado."""
    conn = get_db()
    conn.execute("UPDATE users SET generaciones_disponibles=? WHERE id=?", (n, int(user_id)))
    conn.commit()
    conn.close()
