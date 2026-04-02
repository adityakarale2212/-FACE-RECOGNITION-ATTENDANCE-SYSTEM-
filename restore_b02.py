import sqlite3

def restore_b02():
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO students (student_id, name, encoding) VALUES ('B02', 'KESUR KARINA AJAY RACHANA', NULL)")
        conn.commit()
        print("Restored B02 with NULL face encoding.")
    except sqlite3.IntegrityError:
        print("B02 already exists. Resetting encoding to NULL.")
        c.execute("UPDATE students SET encoding=NULL WHERE student_id='B02'")
        conn.commit()
    finally:
        conn.close()

if __name__ == "__main__":
    restore_b02()
