import sqlite3
try:
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute("SELECT student_id, name FROM students LIMIT 5")
    print("Students in DB:", c.fetchall())
    c.execute("SELECT count(*) FROM students")
    print("Total students:", c.fetchone()[0])
    
    # Check if encoding allows null
    c.execute("PRAGMA table_info(students)")
    print("Schema:", c.fetchall())
except Exception as e:
    print("Error:", e)
