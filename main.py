import cv2
import face_recognition
import sqlite3
import numpy as np
import pickle
import datetime

# Constants
EAR_THRESHOLD = 0.2
RESIZE_FACTOR = 0.25
FACE_TOLERANCE = 0.55  # Stricter than default 0.6 to reduce false positives

def get_known_encodings():
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute("SELECT student_id, name, encoding FROM students WHERE encoding IS NOT NULL")
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
    """
    Logs attendance only ONCE per calendar day.
    Uses date-based check (not 12-hr cooldown) to stay in sync with dashboard.
    """
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    
    now = datetime.datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    # Strictly check: has this student already been marked TODAY?
    c.execute("""
        SELECT 1 FROM attendance_logs 
        WHERE student_id=? AND date(timestamp)=?
    """, (student_id, today_str))
    row = c.fetchone()
    
    if row:
        conn.close()
        return False, "Already marked today"
            
    c.execute("INSERT INTO attendance_logs (student_id, timestamp, status) VALUES (?, ?, ?)", 
              (student_id, now.strftime("%Y-%m-%d %H:%M:%S.%f"), 'PRESENT'))
    conn.commit()
    conn.close()
    print(f"[LOG] {name} ({student_id}) marked PRESENT at {now.strftime('%H:%M:%S')}")
    return True, "Marked Successfully"

def calculate_ear(eye_landmarks):
    p1 = np.array(eye_landmarks[0])
    p2 = np.array(eye_landmarks[1])
    p3 = np.array(eye_landmarks[2])
    p4 = np.array(eye_landmarks[3])
    p5 = np.array(eye_landmarks[4])
    p6 = np.array(eye_landmarks[5])

    v1 = np.linalg.norm(p2 - p6)
    v2 = np.linalg.norm(p3 - p5)
    h = np.linalg.norm(p1 - p4)

    return (v1 + v2) / (2.0 * h)

def main():
    known_ids, known_names, known_encodings = get_known_encodings()
    print(f"[SYSTEM] Loaded {len(known_ids)} enrolled students.")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERROR] Could not open webcam.")
        return

    # --- PER-STUDENT state tracking ---
    # Each student gets their own blink counter and blink_detected flag.
    # This prevents one student's blink from triggering another student's log.
    student_blink_counters = {}   # { student_id: int }
    student_blink_detected = {}   # { student_id: bool }
    last_seen_id = None           # Track which student is currently in frame

    current_status = "Waiting for Face"
    ear_value = 0.0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        small_frame = cv2.resize(frame, (0, 0), fx=RESIZE_FACTOR, fy=RESIZE_FACTOR)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
        face_landmarks_list = face_recognition.face_landmarks(rgb_small_frame, face_locations)

        ear_value = 0.0

        if not face_locations:
            current_status = "Waiting for Face"
            last_seen_id = None

        for idx, (face_loc, face_encoding) in enumerate(zip(face_locations, face_encodings)):
            top, right, bottom, left = face_loc

            # --- Identify the student ---
            matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=FACE_TOLERANCE)
            face_distances = face_recognition.face_distance(known_encodings, face_encoding)

            identified_name = "Unknown"
            student_id = None
            color = (0, 0, 255)  # Red for unknown

            if len(face_distances) > 0:
                best_idx = np.argmin(face_distances)
                if matches[best_idx]:
                    identified_name = known_names[best_idx]
                    student_id = known_ids[best_idx]

            # --- Per-student blink tracking ---
            if student_id:
                # Initialize counters for new students
                if student_id not in student_blink_counters:
                    student_blink_counters[student_id] = 0
                    student_blink_detected[student_id] = False

                # Calculate EAR for this face (use landmarks if available)
                if idx < len(face_landmarks_list):
                    landmarks = face_landmarks_list[idx]
                    left_ear = calculate_ear(landmarks['left_eye'])
                    right_ear = calculate_ear(landmarks['right_eye'])
                    ear_value = (left_ear + right_ear) / 2.0

                    if ear_value < EAR_THRESHOLD:
                        student_blink_detected[student_id] = True
                    else:
                        if student_blink_detected[student_id]:
                            student_blink_counters[student_id] += 1
                            student_blink_detected[student_id] = False

                blinks = student_blink_counters[student_id]

                # --- Log only if THIS student has blinked at least once ---
                if blinks >= 1:
                    allowed, msg = log_attendance(student_id, identified_name)
                    if allowed:
                        current_status = f"Verified: {identified_name}"
                        color = (0, 200, 0)
                        # Reset blink counter so they need to blink again if re-detected
                        student_blink_counters[student_id] = 0
                    else:
                        current_status = f"{identified_name}: {msg}"
                        color = (0, 200, 0)
                else:
                    current_status = f"{identified_name}: Blink to Verify"
                    color = (0, 165, 255)  # Orange — recognized but waiting for blink
            else:
                current_status = "Unknown Subject"
                color = (0, 0, 255)

            # Scale face box back up
            scale = int(1 / RESIZE_FACTOR)
            top *= scale; right *= scale; bottom *= scale; left *= scale

            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
            cv2.putText(frame, identified_name, (left + 6, bottom - 6),
                        cv2.FONT_HERSHEY_DUPLEX, 0.7, (255, 255, 255), 1)

        # --- Display overlay ---
        blinks_display = student_blink_counters.get(last_seen_id, 0)
        cv2.putText(frame, f"EAR: {ear_value:.2f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 0), 2)
        cv2.putText(frame, f"Status: {current_status}", (10, 65),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)

        cv2.imshow('Face Attendance System', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
