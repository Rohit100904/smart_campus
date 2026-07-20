# ==========================================================
# SMART CAMPUS
# Face Recognition Engine
# Part 1
# ==========================================================

import os
import cv2
import pickle
import sqlite3
import numpy as np
import face_recognition
from datetime import datetime

# ==========================================================
# Paths
# ==========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ENCODE_FILE = os.path.join(BASE_DIR, "EncodeFile.p")

IMAGE_FOLDER = os.path.join(BASE_DIR, "Images")

DATABASE = os.path.join(
    os.path.dirname(BASE_DIR),
    "students.db"
)

# ==========================================================
# Load Face Encodings
# ==========================================================

print("Loading face encodings...")

if not os.path.exists(ENCODE_FILE):
    raise FileNotFoundError(
        f"Encoding file not found: {ENCODE_FILE}"
    )

with open(ENCODE_FILE, "rb") as file:

    encodeListKnown, studentIds = pickle.load(file)

print(f"Loaded {len(studentIds)} students.")

# ==========================================================
# Database
# ==========================================================

def get_db():

    conn = sqlite3.connect(DATABASE)

    conn.row_factory = sqlite3.Row

    return conn

# ==========================================================
# Camera
# ==========================================================

camera = None

def start_camera():

    global camera

    if camera is None:

        camera = cv2.VideoCapture(0)

        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)

        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    return camera

def stop_camera():

    global camera

    if camera is not None:

        camera.release()

        camera = None

# ==========================================================
# Globals
# ==========================================================

current_student = None

last_student = None

last_detection_time = None
# ==========================================================
# Student Database Helper Functions
# ==========================================================

def get_student(student_id):
    """
    Return one student record from the database.
    """

    conn = get_db()

    student = conn.execute(

        """
        SELECT *

        FROM students

        WHERE student_id = ?

        """,

        (student_id,)

    ).fetchone()

    conn.close()

    return student


# ==========================================================
# Attendance Helper
# ==========================================================

def mark_attendance(student_id):

    conn = get_db()

    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%H:%M:%S")

    print("Recognized:", student_id)

    already_marked = conn.execute("""
        SELECT 1
        FROM attendance
        WHERE student_id=?
        AND date=?
    """, (student_id, today)).fetchone()

    if already_marked is None:

        conn.execute("""
            INSERT INTO attendance(
                student_id,
                date,
                time,
                status
            )
            VALUES(?,?,?,?)
        """,
        (
            student_id,
            today,
            now,
            "Present"
        ))

        conn.commit()

        print("Inserted into database")

    else:

        print("Already marked today")

    conn.close()


# ==========================================================
# Draw Face Box
# ==========================================================

def draw_box(frame, location, name):

    top, right, bottom, left = location

    cv2.rectangle(

        frame,

        (left, top),

        (right, bottom),

        (0,255,0),

        3

    )

    cv2.rectangle(

        frame,

        (left, bottom-35),

        (right, bottom),

        (0,255,0),

        cv2.FILLED

    )

    cv2.putText(

        frame,

        name,

        (left+6, bottom-8),

        cv2.FONT_HERSHEY_SIMPLEX,

        0.6,

        (255,255,255),

        2

    )

    # ==========================================================
# Face Recognition
# ==========================================================

def process_frame(frame):

    global current_student

    small = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
    rgbSmall = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

    faceLocations = face_recognition.face_locations(rgbSmall)
    faceEncodings = face_recognition.face_encodings(
        rgbSmall,
        faceLocations
    )

    current_student = None

    for encodeFace, faceLoc in zip(faceEncodings, faceLocations):

        matches = face_recognition.compare_faces(
            encodeListKnown,
            encodeFace,
            tolerance=0.50
        )

        faceDistance = face_recognition.face_distance(
            encodeListKnown,
            encodeFace
        )

        if len(faceDistance) == 0:
            continue

        matchIndex = np.argmin(faceDistance)

        top, right, bottom, left = faceLoc

        top *= 4
        right *= 4
        bottom *= 4
        left *= 4

        best_distance = faceDistance[matchIndex]

        print("Distances:", faceDistance)
        print("Best:", studentIds[matchIndex], best_distance)

    if matches[matchIndex] and best_distance < 0.45:

        student_id = studentIds[matchIndex]

        student = get_student(student_id)

        if student:

            current_student = student

            mark_attendance(student_id)

            draw_box(
                frame,
                (top, right, bottom, left),
                student["name"]
            )

    else:

        draw_unknown(
            frame,
            (top, right, bottom, left)
        )

        return frame


# ==========================================================
# Frame Generator
# ==========================================================

def generate_frames():

    camera = start_camera()

    while True:

        success, frame = camera.read()

        if not success:
            break

        frame = process_frame(frame)

        ret, buffer = cv2.imencode(".jpg", frame)

        if not ret:
            continue

        frameBytes = buffer.tobytes()

        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' +
            frameBytes +
            b'\r\n'
        )


# ==========================================================
# Current Student
# ==========================================================

def get_current_student():

    return current_student


# ==========================================================
# Close Camera
# ==========================================================

def shutdown():

    stop_camera()


# ==========================================================
# Standalone Testing
# ==========================================================

if __name__ == "__main__":

    camera = start_camera()

    while True:

        success, frame = camera.read()

        if not success:
            break

        frame = process_frame(frame)

        cv2.imshow(
            "Smart Campus Face Recognition",
            frame
        )

        key = cv2.waitKey(1)

        if key == ord("q"):
            break

    stop_camera()

    cv2.destroyAllWindows()


# ==========================================================
# Unknown Face Box
# ==========================================================

def draw_unknown(frame, location):

    top, right, bottom, left = location

    cv2.rectangle(

        frame,

        (left, top),

        (right, bottom),

        (0,0,255),

        3

    )

    cv2.rectangle(

        frame,

        (left, bottom-35),

        (right, bottom),

        (0,0,255),

        cv2.FILLED

    )

    cv2.putText(

        frame,

        "Unknown",

        (left+6, bottom-8),

        cv2.FONT_HERSHEY_SIMPLEX,

        0.6,

        (255,255,255),

        2

    )
    