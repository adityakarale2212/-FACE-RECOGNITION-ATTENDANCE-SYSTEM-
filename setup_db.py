import sqlite3
import os

def init_db():
    db_path = 'attendance.db'
    if os.path.exists(db_path):
        print(f"Database {db_path} already exists.")
        return

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Create students table
    c.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            encoding BLOB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create attendance_logs table
    c.execute('''
        CREATE TABLE IF NOT EXISTS attendance_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'PRESENT',
            FOREIGN KEY(student_id) REFERENCES students(student_id)
        )
    ''')

    conn.commit()
    conn.close()
    print(f"Database {db_path} initialized successfully.")

if __name__ == "__main__":
    init_db()
