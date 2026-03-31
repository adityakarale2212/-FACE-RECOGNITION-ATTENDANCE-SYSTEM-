from flask import Flask, render_template, request, jsonify
import cv2
import face_recognition
import sqlite3
import numpy as np
import pickle
import datetime
import base64

app = Flask(__name__)

# Constants
EAR_THRESHOLD = 0.2
COOLDOWN_SECONDS = 12 * 3600  # 12 hours
RESIZE_FACTOR = 0.5  # Slightly larger for better accuracy via web

def get_db_connection():
    conn = sqlite3.connect('attendance.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_known_encodings():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT student_id, name, encoding FROM students WHERE encoding IS NOT NULL")
    rows = c.fetchall()
    conn.close()
    
    known_ids = []
    known_names = []
    known_encodings = []
    
    for r in rows:
        known_ids.append(r['student_id'])
        known_names.append(r['name'])
        known_encodings.append(pickle.loads(r['encoding']))
        
    return known_ids, known_names, known_encodings

# Initialize encodings in memory to prevent loading per frame
known_ids, known_names, known_encodings = get_known_encodings()

def log_attendance(student_id, name):
    conn = get_db_connection()
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
        last_time = datetime.datetime.strptime(row['timestamp'], "%Y-%m-%d %H:%M:%S.%f") if '.' in row['timestamp'] else datetime.datetime.strptime(row['timestamp'], "%Y-%m-%d %H:%M:%S")
        if (now - last_time).total_seconds() < COOLDOWN_SECONDS:
            conn.close()
            return False, "Already marked recently"
            
    c.execute("INSERT INTO attendance_logs (student_id, timestamp, status) VALUES (?, ?, ?)", 
              (student_id, now.strftime("%Y-%m-%d %H:%M:%S.%f"), 'PRESENT'))
    conn.commit()
    conn.close()
    return True, "Marked Successfully"

def calculate_ear(eye_landmarks):
    # eye_landmarks is a list of 6 (x, y) tuples
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

def decode_base64_image(base64_string):
    if ',' in base64_string:
        base64_string = base64_string.split(',')[1]
    img_data = base64.b64decode(base64_string)
    nparr = np.frombuffer(img_data, np.uint8)
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/enroll_view')
def enroll_view():
    return render_template('enroll.html')

@app.route('/admin')
def admin():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Get students info
    c.execute("""
        SELECT student_id, name, 
               CASE WHEN encoding IS NOT NULL THEN 1 ELSE 0 END as is_registered 
        FROM students 
        ORDER BY student_id
    """)
    students = c.fetchall()
    
    # Get recent attendance
    c.execute("""
        SELECT a.timestamp, s.student_id, s.name, a.status 
        FROM attendance_logs a 
        JOIN students s ON a.student_id = s.student_id 
        ORDER BY a.timestamp DESC 
        LIMIT 200
    """)
    logs = c.fetchall()
    
    conn.close()
    return render_template('admin.html', students=students, logs=logs)

@app.route('/api/process_frame', methods=['POST'])
def process_frame():
    data = request.json
    if not data or 'image' not in data:
        return jsonify({'error': 'No image provided'}), 400

    frame = decode_base64_image(data['image'])
    blink_counted = data.get('blink_counted', 0)
    blink_detected = data.get('blink_detected', False)

    # Resize for speed
    small_frame = cv2.resize(frame, (0, 0), fx=RESIZE_FACTOR, fy=RESIZE_FACTOR)
    rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

    face_locations = face_recognition.face_locations(rgb_small_frame)
    face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
    face_landmarks_list = face_recognition.face_landmarks(rgb_small_frame, face_locations)

    ear_value = 0
    is_blinking = False
    
    status = "Waiting for Face"
    identified_name = "Unknown"
    logged = False

    if face_landmarks_list:
        landmarks = face_landmarks_list[0]
        left_ear = calculate_ear(landmarks['left_eye'])
        right_ear = calculate_ear(landmarks['right_eye'])
        ear_value = (left_ear + right_ear) / 2.0
        
        if ear_value < EAR_THRESHOLD:
            blink_detected = True # Client should maintain this state
        else:
            if blink_detected:
                blink_counted += 1
                blink_detected = False

    if face_encodings:
        face_encoding = face_encodings[0]
        matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=0.55)
        
        face_distances = face_recognition.face_distance(known_encodings, face_encoding)
        if len(face_distances) > 0:
            best_match_index = np.argmin(face_distances)
            if matches[best_match_index]:
                identified_name = known_names[best_match_index]
                student_id = known_ids[best_match_index]
                
                if blink_counted >= 1:
                    allowed, msg = log_attendance(student_id, identified_name)
                    status = f"Verified: {identified_name}" if allowed else f"{identified_name}: {msg}"
                    logged = allowed
                else:
                    status = "Blink to Verify"
            else:
                 status = "Unknown Subject"
                 
    return jsonify({
        'status': status,
        'ear': ear_value,
        'blinks': blink_counted,
        'blink_detected': blink_detected,
        'name': identified_name,
        'logged': logged
    })

@app.route('/api/enroll_frame', methods=['POST'])
def enroll_frame():
    data = request.json
    student_id = data.get('student_id')
    image_b64 = data.get('image')
    
    if not student_id or not image_b64:
        return jsonify({'error': 'Missing ID or Image'}), 400
        
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT name, encoding FROM students WHERE student_id=?", (student_id,))
    row = c.fetchone()
    
    if not row:
         conn.close()
         return jsonify({'error': f"ID '{student_id}' not found. Preload first."}), 404
         
    frame = decode_base64_image(image_b64)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    boxes = face_recognition.face_locations(rgb_frame)
    
    if len(boxes) == 0:
         conn.close()
         return jsonify({'error': 'No face detected'}), 400
    elif len(boxes) > 1:
         conn.close()
         return jsonify({'error': 'Multiple faces detected'}), 400
         
    encodings = face_recognition.face_encodings(rgb_frame, boxes)
    if not encodings:
         conn.close()
         return jsonify({'error': 'Could not extract face encoding'}), 400
         
    blob_data = pickle.dumps(encodings[0])
    c.execute("UPDATE students SET encoding=? WHERE student_id=?", (blob_data, student_id))
    conn.commit()
    conn.close()
    
    # Reload encodings in memory
    global known_ids, known_names, known_encodings
    known_ids, known_names, known_encodings = get_known_encodings()
    
    return jsonify({'success': f"Successfully saved face for {row['name']}!"})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
