import sqlite3
import os

def preload_students(data):
    """Inserts a list of (student_id, name) into the database."""
    db_path = 'attendance.db'
    if not os.path.exists(db_path):
        print("Database not found. Please run setup_db.py first.")
        return

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    
    success_count = 0
    error_count = 0
    
    for student_id, name in data:
        try:
            c.execute("INSERT INTO students (student_id, name) VALUES (?, ?)", (student_id, name))
            success_count += 1
        except sqlite3.IntegrityError:
            print(f"Error: Student ID '{student_id}' already exists.")
            error_count += 1
            
    conn.commit()
    conn.close()
    print(f"\nSuccessfully added {success_count} students. ({error_count} failed to add)")

if __name__ == "__main__":
    print("--- Preload Classroom Roster ---")
    print("Enter student details. Type 'done' or 'q' when finished.")
    
    students_to_add = []
    while True:
        entry = input("Enter Student ID and Name separated by a comma (e.g. 101,John Doe): ").strip()
        if entry.lower() in ['done', 'q', 'quit', 'exit']:
            break
        
        parts = entry.split(',', 1)
        if len(parts) == 2:
            student_id = parts[0].strip()
            name = parts[1].strip()
            students_to_add.append((student_id, name))
        else:
            print("Invalid format. Please use: ID,Name")
            
    if students_to_add:
        preload_students(students_to_add)
    else:
        print("No students provided.")
