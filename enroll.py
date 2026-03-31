import cv2
import face_recognition
import sqlite3
import numpy as np
import pickle
import sys

def register_student():
    student_id = input("Enter Student ID to scan face for: ").strip()

    if not student_id:
        print("Error: Student ID cannot be empty.")
        return

    # Check if exists
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute("SELECT name, encoding FROM students WHERE student_id=?", (student_id,))
    row = c.fetchone()
    
    if not row:
        print(f"Error: Student ID '{student_id}' not found in database. Please preload them first.")
        conn.close()
        return
        
    name, existing_encoding = row
    if existing_encoding is not None:
        print(f"Note: {name} already has a face registered. This will overwrite it.")
        
    conn.close()

    print("Opening webcam... Press 's' to capture, 'q' to quit.")
    cap = cv2.VideoCapture(0)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break

        # Display query
        display_frame = frame.copy()
        cv2.putText(display_frame, "Press 's' to Save Face", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.imshow('Enrollment', display_frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            # Detect face
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            boxes = face_recognition.face_locations(rgb_frame)
            
            if len(boxes) == 0:
                print("No face detected! Try again.")
                continue
            elif len(boxes) > 1:
                print("Multiple faces detected! Please ensure only one person is in frame.")
                continue

            print("Face detected. Encoding...")
            encodings = face_recognition.face_encodings(rgb_frame, boxes)
            
            if encodings:
                encoding = encodings[0]
                blob_data = pickle.dumps(encoding)

                # Save to DB (Update instead of Insert)
                try:
                    conn = sqlite3.connect('attendance.db')
                    c = conn.cursor()
                    c.execute("UPDATE students SET encoding=? WHERE student_id=?", 
                              (blob_data, student_id))
                    conn.commit()
                    conn.close()
                    print(f"Successfully saved face for {name} ({student_id})!")
                    break
                except Exception as e:
                    print(f"Database error: {e}")
            else:
                print("Could not encode face. Try adjusting lighting.")

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    register_student()
