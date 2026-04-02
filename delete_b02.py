import sqlite3

def remove_b02():
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    
    # Check if exists
    c.execute("SELECT * FROM students WHERE student_id=?", ('B02',))
    student = c.fetchone()
    
    if student:
        print(f"Found student: {student[1]} - {student[2]}")
        # Delete faces (encoding) or the whole record?
        # The user says "remove a face from the data base rollno B02"
        # I will set the encoding to NULL (meaning face removed), or delete the whole student.
        # It's better to just delete the student since "remove a face from the data base rollno B02" usually implies deleting the unneeded student data.
        c.execute("DELETE FROM students WHERE student_id=?", ('B02',))
        conn.commit()
        print("Successfully removed B02 from the database.")
    else:
        print("Student B02 not found in the database.")
        
    conn.close()

if __name__ == "__main__":
    remove_b02()
