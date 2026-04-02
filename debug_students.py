import sqlite3
import os

db_path = 'attendance.db'
if not os.path.exists(db_path):
    print(f"Error: {db_path} not found")
else:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT student_id, name FROM students WHERE student_id IN ('A65', 'B13')")
    print("Students:", c.fetchall())
    c.execute("SELECT * FROM attendance_logs WHERE student_id IN ('A65', 'B13')")
    print("Logs:", c.fetchall())
    conn.close()
