# ==========================================================
# SMART CAMPUS PLATFORM
# Flask Backend
# Part 1
# ==========================================================

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
    Response
)

import sqlite3
import os
import cv2
import csv
import pickle
import numpy as np
import face_recognition
from datetime import datetime
from werkzeug.utils import secure_filename
import os

from FaceRecognition.main import generate_frames, get_current_student

# ==========================================================
# Flask Configuration
# ==========================================================

app = Flask(__name__)

app.secret_key = "SMART_CAMPUS_SECRET_KEY_2026"

DATABASE = "students.db"

UPLOAD_FOLDER = "static/uploads"

PROFILE_FOLDER = "static/images"

FACE_IMAGE_FOLDER = "FaceRecognition/Images"

ENCODE_FILE = "FaceRecognition/EncodeFile.p"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ==========================================================
# Database Connection
# ==========================================================

def get_db():

    conn = sqlite3.connect(DATABASE)

    conn.row_factory = sqlite3.Row

    return conn

# ==========================================================
# Create Tables
# ==========================================================

def create_tables():

    conn = get_db()

    cursor = conn.cursor()

    # ---------------- Students ----------------

    cursor.execute("""

    CREATE TABLE IF NOT EXISTS students(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        student_id TEXT UNIQUE,

        name TEXT,

        department TEXT,

        semester TEXT,

        email TEXT,

        password TEXT,

        attendance INTEGER DEFAULT 0,

        profile_image TEXT

    )

    """)

    # ---------------- Attendance ----------------

    cursor.execute("""

    CREATE TABLE IF NOT EXISTS attendance(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        student_id TEXT,

        date TEXT,

        time TEXT,

        status TEXT

    )

    """)

    # ---------------- Materials ----------------

    cursor.execute("""

    CREATE TABLE IF NOT EXISTS materials(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        title TEXT,

        subject TEXT,

        filename TEXT,

        uploaded_on TEXT

    )

    """)

    # ---------------- Emergency ----------------

    cursor.execute("""

    CREATE TABLE IF NOT EXISTS emergency(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        student_id TEXT,

        emergency_type TEXT,

        description TEXT,

        created_at TEXT

    )

    """)

    conn.commit()

    conn.close()

# ==========================================================
# Create Database
# ==========================================================

create_tables()
# ==========================================================
# Insert Sample Students
# ==========================================================

def seed_database():

    conn = get_db()

    cursor = conn.cursor()

    count = cursor.execute(

        "SELECT COUNT(*) FROM students"

    ).fetchone()[0]

    if count == 0:

        students = [

            (
                "220101001",
                "Arijit Saha",
                "Computer Science",
                "8",
                "arijit@example.com",
                "123456",
                0,
                "220101001.jpg"
            ),

            (
                "220101002",
                "Rahul Das",
                "Computer Science",
                "8",
                "rahul@example.com",
                "123456",
                0,
                "220101002.jpg"
            ),

            (
                "220101003",
                "Priya Roy",
                "Computer Science",
                "8",
                "priya@example.com",
                "123456",
                0,
                "220101003.jpg"
            )

        ]

        cursor.executemany(

            """

            INSERT OR IGNORE INTO students(

                student_id,

                name,

                department,

                semester,

                email,

                password,

                attendance,

                profile_image

            )

            VALUES(?,?,?,?,?,?,?,?)

            """,

            students

        )

        conn.commit()

        print("Sample Students Added.")

    conn.close()


seed_database()


# ==========================================================
# Load Face Encodings
# ==========================================================

print("Loading Face Encodings...")

if os.path.exists(ENCODE_FILE):

    with open(ENCODE_FILE, "rb") as file:

        encodeListKnown, studentIds = pickle.load(file)

else:

    encodeListKnown = []

    studentIds = []

print("Face Encodings Loaded.")

# ==========================================================
# Global Camera Variables
# ==========================================================

camera = None

current_student = None

camera_running = False

# ==========================================================
# Authentication Helper
# ==========================================================

def login_required():

    return "student" in session


# ==========================================================
# Login
# ==========================================================

@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        student_id = request.form.get("username")
        password = request.form.get("password")

        conn = get_db()

        student = conn.execute(

            """
            SELECT *
            FROM students

            WHERE student_id=?

            AND password=?

            """,

            (student_id, password)

        ).fetchone()

        conn.close()

        if student:

            session["student"] = student["student_id"]

            session["student_name"] = student["name"]

            flash("Login Successful", "success")

            return redirect(url_for("dashboard"))

        flash("Invalid Student ID or Password", "danger")

    return render_template("login.html")


# ==========================================================
# Dashboard
# ==========================================================

@app.route("/dashboard")
def dashboard():

    if not login_required():

        return redirect(url_for("login"))

    conn = get_db()

    student = conn.execute(

        """
        SELECT *

        FROM students

        WHERE student_id=?

        """,

        (session["student"],)

    ).fetchone()

    attendance_count = conn.execute(

        """
        SELECT COUNT(*)

        FROM attendance

        WHERE student_id=?

        """,

        (session["student"],)

    ).fetchone()[0]

    total_materials = conn.execute(

        """
        SELECT COUNT(*)

        FROM materials

        """

    ).fetchone()[0]

    emergency_count = conn.execute(

        """
        SELECT COUNT(*)

        FROM emergency

        WHERE student_id=?

        """,

        (session["student"],)

    ).fetchone()[0]

    conn.close()

    stats = get_dashboard_stats()

    stats = get_dashboard_stats()

    stats = get_dashboard_stats()

    print(dict(student))

    return render_template(
    "dashboard.html",
    student=student,
    attendance_count=attendance_count,
    total_materials=total_materials,
    emergency_count=emergency_count,
    stats=stats
)

    return render_template(
        "dashboard.html",
        student=student,
        attendance_count=attendance_count,
        total_materials=total_materials,
        emergency_count=emergency_count,
        stats=stats
    )


# ==========================================================
# Attendance Page
# ==========================================================

@app.route("/attendance")
def attendance():

    if not login_required():
        return redirect(url_for("login"))

    conn = get_db()

    # Logged in student
    student = conn.execute("""
        SELECT *
        FROM students
        WHERE student_id=?
    """, (session["student"],)).fetchone()

    today = datetime.now().strftime("%Y-%m-%d")

    # Today's attendance log with student names
    records = conn.execute("""
        SELECT
            attendance.student_id,
            students.name,
            attendance.date,
            attendance.time,
            attendance.status
        FROM attendance
        INNER JOIN students
        ON attendance.student_id = students.student_id
        WHERE attendance.date = ?
        ORDER BY attendance.time DESC
    """, (today,)).fetchall()

    # Total students
    total_students = conn.execute("""
        SELECT COUNT(*)
        FROM students
    """).fetchone()[0]

    # Present today
    present = conn.execute("""
        SELECT COUNT(DISTINCT student_id)
        FROM attendance
        WHERE date = ?
    """, (today,)).fetchone()[0]

    absent = total_students - present

    percentage = 0
    if total_students > 0:
        percentage = round((present / total_students) * 100)

    stats = {
        "students": total_students,
        "present": present,
        "absent": absent,
        "percentage": percentage
    }

    conn.close()

    return render_template(
        "attendance.html",
        student=student,
        student_name=session["student_name"],
        stats=stats,
        records=records
    )
# ==========================================================
# Attendance Report
# ==========================================================

@app.route("/report")
def report():

    if not login_required():
        return redirect(url_for("login"))

    conn = get_db()

    students = conn.execute("""
        SELECT *
        FROM students
        ORDER BY name
    """).fetchall()

    conn.close()

    return render_template(
        "report.html",
        students=students
    )
# ==========================================================
# Learning Materials
# ==========================================================

@app.route("/materials")
def materials():

    if not login_required():
        return redirect(url_for("login"))

    conn = get_db()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM materials
        ORDER BY id DESC
    """)

    materials = cursor.fetchall()

    conn.close()

    return render_template(
        "materials.html",
        materials=materials,
        student_name=session.get("student_name")
    )



@app.route("/delete_material/<int:id>")
def delete_material(id):

    if "student_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    cursor = conn.cursor()

    cursor.execute(
        "SELECT filename FROM materials WHERE id=?",
        (id,)
    )

    row = cursor.fetchone()

    if row:

        filepath = os.path.join(
            app.config["UPLOAD_FOLDER"],
            row["filename"]
        )

        if os.path.exists(filepath):
            os.remove(filepath)

        cursor.execute(
            "DELETE FROM materials WHERE id=?",
            (id,)
        )

        conn.commit()

    conn.close()

    flash("Material deleted.")

    return redirect(url_for("materials"))



@app.route("/search_material")
def search_material():

    if "student_id" not in session:
        return redirect(url_for("login"))

    keyword = request.args.get("keyword", "")

    conn = get_db()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM materials
        WHERE
        title LIKE ?
        OR subject LIKE ?
        ORDER BY id DESC
    """,
    (
        "%" + keyword + "%",
        "%" + keyword + "%"
    ))

    materials = cursor.fetchall()

    conn.close()

    return render_template(
        "materials.html",
        materials=materials,
        student_name=session.get("student_name")
    )




# ==========================================================
# Dashboard Statistics
# ==========================================================

def get_dashboard_stats():

    conn = get_db()

    stats = {}

    stats["students"] = conn.execute(

        "SELECT COUNT(*) FROM students"

    ).fetchone()[0]

    stats["attendance"] = conn.execute(

        "SELECT COUNT(*) FROM attendance"

    ).fetchone()[0]

    stats["materials"] = conn.execute(

        "SELECT COUNT(*) FROM materials"

    ).fetchone()[0]

    stats["emergency"] = conn.execute(

        "SELECT COUNT(*) FROM emergency"

    ).fetchone()[0]

    conn.close()

    return stats

# ==========================================================
# Upload Learning Material
# ==========================================================

ALLOWED_EXTENSIONS = {
    "pdf",
    "ppt",
    "pptx",
    "doc",
    "docx",
    "zip"
}


def allowed_file(filename):

    return (

        "." in filename

        and

        filename.rsplit(".",1)[1].lower()

        in ALLOWED_EXTENSIONS

    )


@app.route("/upload_material", methods=["POST"])
def upload_material():

    if not login_required():

        return redirect(url_for("login"))

    title = request.form["title"]

    subject = request.form["subject"]

    file = request.files["file"]

    if file.filename == "":

        flash("No file selected")

        return redirect(url_for("materials"))

    if allowed_file(file.filename):

        filename = secure_filename(file.filename)

        filepath = os.path.join(

            app.config["UPLOAD_FOLDER"],

            filename

        )

        file.save(filepath)

        conn = get_db()

        conn.execute(

            """

            INSERT INTO materials(

                title,

                subject,

                filename,

                uploaded_on

            )

            VALUES(?,?,?,?)

            """,

            (

                title,

                subject,

                filename,

                datetime.now().strftime("%Y-%m-%d %H:%M")

            )

        )

        conn.commit()

        conn.close()

        flash("Material uploaded successfully")

    return redirect(url_for("materials"))


# ==========================================================
# Download Material
# ==========================================================

from flask import send_from_directory


@app.route("/download/<filename>")
def download(filename):

    return send_from_directory(

        app.config["UPLOAD_FOLDER"],

        filename,

        as_attachment=True

    )


# ==========================================================
# Emergency Alert
# ==========================================================

@app.route("/submit_emergency", methods=["POST"])
def submit_emergency():

    if not login_required():

        return redirect(url_for("login"))

    emergency_type = request.form["type"]

    description = request.form["description"]

    conn = get_db()

    conn.execute(

        """

        INSERT INTO emergency(

            student_id,

            emergency_type,

            description,

            created_at

        )

        VALUES(?,?,?,?)

        """,

        (

            session["student"],

            emergency_type,

            description,

            datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        )

    )

    conn.commit()

    conn.close()

    flash("Emergency Alert Sent Successfully")

    return redirect(url_for("emergency"))


# ==========================================================
# Update Profile
# ==========================================================

@app.route("/update_profile", methods=["POST"])
def update_profile():

    if not login_required():

        return redirect(url_for("login"))

    name = request.form["name"]

    email = request.form["email"]

    department = request.form["department"]

    semester = request.form["semester"]

    conn = get_db()

    conn.execute(

        """

        UPDATE students

        SET

        name=?,

        email=?,

        department=?,

        semester=?

        WHERE student_id=?

        """,

        (

            name,

            email,

            department,

            semester,

            session["student"]

        )

    )

    conn.commit()

    conn.close()

    flash("Profile Updated Successfully")
    return redirect(url_for("profile"))


# ==========================================================
# Profile
# ==========================================================

@app.route("/profile")
def profile():

    if not login_required():
        return redirect(url_for("login"))

    conn = get_db()

    student = conn.execute(
        """
        SELECT *
        FROM students
        WHERE student_id=?
        """,
        (session["student"],)
    ).fetchone()

    conn.close()

    return render_template(
        "profile.html",
        student=student
    )

# ==========================================================
# Logout
# ==========================================================

@app.route("/logout")
def logout():

    session.clear()

    flash("Logged out successfully.")

    return redirect(url_for("login"))

@app.route("/emergency")
def emergency():

    if not login_required():
        return redirect(url_for("login"))

    conn = get_db()

    alerts = conn.execute("""
        SELECT *
        FROM emergency
        WHERE student_id=?
        ORDER BY id DESC
    """, (session["student"],)).fetchall()

    conn.close()

    return render_template(
        "emergency.html",
        alerts=alerts
    )

def mark_attendance(student_id):

    conn = get_db()

    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%H:%M:%S")

    already_marked = conn.execute("""
    SELECT 1
    FROM attendance
    WHERE student_id=?
    AND date=?
""", (student_id, today)).fetchone()

    if already_marked is None:

        conn.execute(
            """
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
            )
        )

        conn.commit()

        print(f"{student_id} Attendance Marked")

    conn.close()

# ==========================================================
# Live Camera Stream
# ==========================================================

def generate_frames():

    camera = cv2.VideoCapture(0)

    while True:

        success, img = camera.read()

        if not success:
            break

        imgSmall = cv2.resize(img, (0, 0), None, 0.25, 0.25)
        imgSmall = cv2.cvtColor(imgSmall, cv2.COLOR_BGR2RGB)

        faceCurFrame = face_recognition.face_locations(imgSmall)
        encodeCurFrame = face_recognition.face_encodings(imgSmall, faceCurFrame)

        for encodeFace, faceLoc in zip(encodeCurFrame, faceCurFrame):

            matches = face_recognition.compare_faces(
                encodeListKnown,
                encodeFace
            )

            faceDis = face_recognition.face_distance(
                encodeListKnown,
                encodeFace
            )

            matchIndex = np.argmin(faceDis)

            if matches[matchIndex]:

                student_id = studentIds[matchIndex]
                mark_attendance(student_id)

                y1, x2, y2, x1 = faceLoc

                y1 *= 4
                x2 *= 4
                y2 *= 4
                x1 *= 4

                cv2.rectangle(
                    img,
                    (x1, y1),
                    (x2, y2),
                    (0,255,0),
                    2
                )

                conn = get_db()

                student = conn.execute(
                    """
                    SELECT name
                    FROM students
                    WHERE student_id=?
                    """,
                    (student_id,)
                ).fetchone()

                conn.close()

                name = student["name"] if student else student_id

                cv2.putText(
                    img,
                    name,
                    (x1, y1-10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (255,255,255),
                    2
                )

        ret, buffer = cv2.imencode(".jpg", img)

        frame = buffer.tobytes()

        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' +
            frame +
            b'\r\n'
        )

    camera.release()

# ==========================================================
# Video Feed
# ==========================================================

@app.route("/video_feed")
def video_feed():

    if not login_required():
        return redirect(url_for("login"))

    return Response(
        generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )

@app.route("/current_student")
def current_student():

    if not login_required():
        return jsonify({})

    student = get_current_student()

    if student is None:
        return jsonify({})

    return jsonify({
        "student_id": student["student_id"],
        "name": student["name"],
        "department": student["department"],
        "semester": student["semester"],
        "attendance": student["attendance"],
        "profile_image": student["profile_image"]
    })

@app.route("/attendance_log")
def attendance_log():

    conn = get_db()

    today = datetime.now().strftime("%Y-%m-%d")

    rows = conn.execute("""
        SELECT
            attendance.student_id,
            students.name,
            attendance.time,
            attendance.status
        FROM attendance
        INNER JOIN students
        ON attendance.student_id = students.student_id
        WHERE attendance.date = ?
        ORDER BY attendance.time DESC
    """, (today,)).fetchall()

    conn.close()

    return jsonify([
        dict(row) for row in rows
    ])


@app.route("/debug")
def debug():

    conn = get_db()

    rows = conn.execute("""
        SELECT *
        FROM attendance
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return jsonify([dict(r) for r in rows])


@app.route("/reset_attendance")
def reset_attendance():

    conn = get_db()

    conn.execute("DELETE FROM attendance")

    conn.commit()

    conn.close()

    return "Attendance Reset Successfully"

# ==========================================================
# Run Flask
# ==========================================================

if __name__ == "__main__":
    print("Starting Flask Server...")
    app.run(debug=True)