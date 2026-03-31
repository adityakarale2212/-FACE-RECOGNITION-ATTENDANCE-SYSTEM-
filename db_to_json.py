import sqlite3
import json

try:
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute("SELECT count(*) FROM students")
    count = c.fetchone()[0]
    
    with open("data_count.json", "w") as f:
        json.dump({"count": count}, f)
except Exception as e:
    with open("data_count.json", "w") as f:
        json.dump({"error": str(e)}, f)
