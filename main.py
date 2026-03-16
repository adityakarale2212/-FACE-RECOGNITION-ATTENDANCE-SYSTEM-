import cv2
import face_recognition
import sqlite3
import numpy as np
import pickle
import datetime
import time

# Constants
EAR_THRESHOLD = 0.2
COOLDOWN_SECONDS = 12 * 3600  # 12 hours
RESIZE_FACTOR = 0.25

# Database Setup
def get_known_encodings():
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute("SELECT student_id, name, encoding FROM students")
    rows = c.fetchall()
    conn.close()
    
    known_ids = []
    known_names = []
    known_encodings = []
    
    for r in rows:
        known_ids.append(r[0])
        known_names.append(r[1])
        known_encodings.append(pickle.loads(r[2]))
        
    return known_ids, known_names, known_encodings

def log_attendance(student_id, name):
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    
    # Check last log
    c.execute("""
        SELECT timestamp FROM attendance_logs 
        WHERE student_id=? 
        ORDER BY timestamp DESC LIMIT 1
    """, (student_id,))
    row = c.fetchone()
    
    now = datetime.datetime.now()
    
    if row:
        last_time = datetime.datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S.%f") if '.' in row[0] else datetime.datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
        if (now - last_time).total_seconds() < COOLDOWN_SECONDS:
            conn.close()
            return False, "Already marked recently"
            
    c.execute("INSERT INTO attendance_logs (student_id, timestamp, status) VALUES (?, ?, ?)", 
              (student_id, now.strftime("%Y-%m-%d %H:%M:%S.%f"), 'PRESENT'))
    conn.commit()
    conn.close()
    print(f"Logged {name} at {now}")
    return True, "Marked Successfully"

# Blink Detection (using face_recognition / dlib landmarks)
def calculate_ear(eye_landmarks):
    # eye_landmarks is a list of 6 (x, y) tuples
    # p1, p2, p3, p4, p5, p6
    p1 = np.array(eye_landmarks[0])
    p2 = np.array(eye_landmarks[1])
    p3 = np.array(eye_landmarks[2])
    p4 = np.array(eye_landmarks[3])
    p5 = np.array(eye_landmarks[4])
    p6 = np.array(eye_landmarks[5])

    # Vertical distances
    v1 = np.linalg.norm(p2 - p6)
    v2 = np.linalg.norm(p3 - p5)
    # Horizontal distance
    h = np.linalg.norm(p1 - p4)

    ear = (v1 + v2) / (2.0 * h)
    return ear

def main():
    known_ids, known_names, known_encodings = get_known_encodings()
    print(f"Loaded {len(known_ids)} students.")

    cap = cv2.VideoCapture(0)
    
    blink_counter = 0
    blink_detected = False
    last_log_time = 0
    
    current_status = "Waiting for Face"
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        height, width, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Face Recognition & Landmarks (Resized)
        small_frame = cv2.resize(frame, (0, 0), fx=RESIZE_FACTOR, fy=RESIZE_FACTOR)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
        
        # Get landmarks for blink detection (using small frame for speed)
        face_landmarks_list = face_recognition.face_landmarks(rgb_small_frame, face_locations)

        ear_value = 0
        is_blinking = False

        if face_landmarks_list:
            # We process only the first face for blink counting simplicity
            landmarks = face_landmarks_list[0]
            left_eye = landmarks['left_eye']
            right_eye = landmarks['right_eye']
            
            left_ear = calculate_ear(left_eye)
            right_ear = calculate_ear(right_eye)
            ear_value = (left_ear + right_ear) / 2.0
            
            if ear_value < EAR_THRESHOLD:
                blink_detected = True # Latch blink
            else:
                if blink_detected: # Eye opened after blink
                    blink_counter += 1
                    blink_detected = False

        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            # Scale back up
            top *= int(1/RESIZE_FACTOR)
            right *= int(1/RESIZE_FACTOR)
            bottom *= int(1/RESIZE_FACTOR)
            left *= int(1/RESIZE_FACTOR)
            
            matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=0.6)
            name = "Unknown"
            student_id = None
            color = (0, 0, 255) # Red

            face_distances = face_recognition.face_distance(known_encodings, face_encoding)
            if len(face_distances) > 0:
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    name = known_names[best_match_index]
                    student_id = known_ids[best_match_index]
            
            # Logic: If Blink Count >= 1 and Face Recognized -> Verify
            if name != "Unknown":
                if blink_counter >= 1:
                    allowed, msg = log_attendance(student_id, name)
                    if allowed:
                        current_status = f"Verified: {name}"
                        color = (0, 255, 0) # Green
                        # Blink count reset after success? Usually good idea to require new blink sequence for next log?
                        # Or just leave it running. Since cooldown handles re-logging.
                        # I'll leave blink_counter running for "Total Blinks".
                    else:
                        current_status = f"{name}: {msg}"
                        color = (0, 255, 0) # Green (because verified, just not logged)
                else:
                    current_status = "Blink to Verify"
                    color = (0, 0, 255) # Red (Liveness failed)
            else:
                current_status = "Unknown Subject"
                color = (0, 0, 255)

            # Draw Box
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
            cv2.putText(frame, name, (left + 6, bottom - 6), cv2.FONT_HERSHEY_DUPLEX, 0.8, (255, 255, 255), 1)

        # UI Overlay
        cv2.putText(frame, f"Blinks: {blink_counter}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        cv2.putText(frame, f"EAR: {ear_value:.2f}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        cv2.putText(frame, f"Status: {current_status}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        cv2.imshow('Face Attendance System', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
