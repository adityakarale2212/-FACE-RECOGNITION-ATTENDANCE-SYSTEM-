import sqlite3
import traceback

with open("output.txt", "w") as f:
    try:
        conn = sqlite3.connect('attendance.db')
        c = conn.cursor()
        c.execute("SELECT count(*) FROM students")
        f.write(f"Count: {c.fetchone()[0]}\n")
        
        c.execute("SELECT student_id, name FROM students LIMIT 5")
        rows = c.fetchall()
        for r in rows:
            f.write(f"{r}\n")
            
        c.execute("PRAGMA table_info(students)")
        f.write(f"Schema: {c.fetchall()}\n")
    except Exception as e:
        f.write("Error: " + str(e) + "\n")
        f.write(traceback.format_exc())
