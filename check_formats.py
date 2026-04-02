import sqlite3

conn = sqlite3.connect('attendance.db')
c = conn.cursor()
c.execute("SELECT student_id, name FROM students LIMIT 10")
print("Students:", c.fetchall())

c.execute("SELECT * FROM attendance_logs LIMIT 5")
print("Logs:", c.fetchall())
conn.close()
