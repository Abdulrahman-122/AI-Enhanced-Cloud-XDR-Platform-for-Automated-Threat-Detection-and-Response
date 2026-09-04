import requests
import sqlite3
import json
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:8000"

# 1. Register a test user via API
user_data = {
    "username": "fouad_live",
    "email": "fouad_live@example.com",
    "full_name": "Fouad Live Test",
    "password": "StrongPassword123!"
}

print("=== 1. إرسال طلب تسجيل مستخدم جديد عبر الـ API (POST /api/auth/register) ===")
try:
    resp = requests.post(f"{BASE_URL}/api/auth/register", json=user_data)
    print(f"حالة الاستجابة (Status Code): {resp.status_code}")
    print("بيانات الاستجابة (Response):", json.dumps(resp.json(), indent=2, ensure_ascii=False))
except Exception as e:
    print("خطأ في الاتصال بالـ API:", e)

# 2. Inspect the database directly using sqlite3
print("\n=== 2. فحص ملف قاعدة البيانات مباشرة بدون الـ API (portal.db) ===")
conn = sqlite3.connect("portal.db")
cursor = conn.cursor()

# Get table names
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [t[0] for t in cursor.fetchall()]
print(f"الجداول الموجودة في قاعدة البيانات: {tables}")

# Query users table
cursor.execute("SELECT id, username, email, full_name, hashed_password, is_active, created_at FROM users;")
rows = cursor.fetchall()

print(f"\nعدد السجلات المحفوظة في جدول users: {len(rows)}")
for row in rows:
    print("--------------------------------------------------")
    print(f"ID              : {row[0]}")
    print(f"Username        : {row[1]}")
    print(f"Email           : {row[2]}")
    print(f"Full Name       : {row[3]}")
    print(f"Hashed Password : {row[4][:30]}... (تشفير Bcrypt آمن)")
    print(f"Is Active       : {bool(row[5])}")
    print(f"Created At      : {row[6]}")

conn.close()
