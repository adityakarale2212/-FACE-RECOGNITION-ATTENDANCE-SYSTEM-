import sqlite3

try:
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute("SELECT count(*) FROM students")
    count = c.fetchone()[0]
    print(f"OUTPUT_COUNT_IS:{count}")
    
    c.execute("SELECT student_id, name FROM students LIMIT 5")
    print(f"OUTPUT_ROWS_ARE:{c.fetchall()}")
except Exception as e:
    print(f"OUTPUT_ERR:{e}")
