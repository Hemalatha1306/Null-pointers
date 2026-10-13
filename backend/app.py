
import os
import re
import cv2
import time
import sqlite3
import threading
import mediapipe as mp

from flask import Flask, Response, jsonify, request, session
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

# ==================================================
# NULL POINTERS - SPACECRAFT CONTROL BACKEND
# ==================================================

app = Flask(__name__)

# Change this to a private, random secret before deployment.
app.config["SECRET_KEY"] = os.environ.get(
    "FLASK_SECRET_KEY",
    "null-pointers-local-development-key-change-me"
)

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# Supports frontend running on VS Code Live Server.
CORS(
    app,
    origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:5501",
        "http://localhost:5501"
    ],
    supports_credentials=True
)

# ==================================================
# DATABASE
# ==================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "users.db")


def get_db():
    connection = sqlite3.connect(DATABASE, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with get_db() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

    print("User database initialized.")


# ==================================================
# CAMERA AND FINGER DETECTION
# ==================================================

camera = None
camera_lock = threading.Lock()

detection_enabled = True
hand_detected = False
finger_count = 0
gesture_name = "NO HAND DETECTED"
last_error = None

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    model_complexity=0,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.6
)


# ==================================================
# COUNT RAISED FINGERS
# ==================================================

def count_fingers(hand_landmarks, handedness_label):
    landmarks = hand_landmarks.landmark
    count = 0

    # Thumb
    thumb_tip = landmarks[4]
    thumb_ip = landmarks[3]

    if handedness_label == "Right":
        if thumb_tip.x < thumb_ip.x:
            count += 1
    else:
        if thumb_tip.x > thumb_ip.x:
            count += 1

    # Index, middle, ring and little fingers
    finger_pairs = [
        (8, 6),
        (12, 10),
        (16, 14),
        (20, 18)
    ]

    for tip_id, pip_id in finger_pairs:
        if landmarks[tip_id].y < landmarks[pip_id].y:
            count += 1

    return max(0, min(count, 5))


# ==================================================
# CAMERA HELPERS
# ==================================================

def open_camera():
    global camera, last_error

    with camera_lock:
        if camera is not None and camera.isOpened():
            return True

        for index in (0, 1, 2):
            cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)

            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                cap.set(cv2.CAP_PROP_FPS, 30)

                camera = cap
                last_error = None
                print(f"Camera opened: index {index}")
                return True

            cap.release()

        camera = None
        last_error = "Could not open camera. Check camera permissions."
        print(last_error)
        return False


def read_camera_frame():
    with camera_lock:
        if camera is None or not camera.isOpened():
            return None, False

        return camera.read()


def release_camera():
    global camera

    with camera_lock:
        if camera is not None:
            camera.release()
            camera = None


# ==================================================
# VIDEO STREAM AND HAND DETECTION
# ==================================================

def generate_frames():
    global hand_detected, finger_count, gesture_name, last_error

    while True:
        if camera is None or not camera.isOpened():
            if not open_camera():
                time.sleep(1)
                continue

        success, frame = read_camera_frame()

        if not success or frame is None:
            last_error = "Unable to read a frame from the camera."
            time.sleep(0.1)
            continue

        frame = cv2.flip(frame, 1)

        if detection_enabled:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb_frame)

            if results.multi_hand_landmarks:
                hand_detected = True

                hand = results.multi_hand_landmarks[0]
                handedness_label = "Right"

                if results.multi_handedness:
                    handedness_label = (
                        results.multi_handedness[0]
                        .classification[0].label
                    )

                finger_count = count_fingers(hand, handedness_label)

                gesture_name = (
                    "NO FINGERS"
                    if finger_count == 0
                    else f"{finger_count} FINGER(S)"
                )

                mp_drawing.draw_landmarks(
                    frame,
                    hand,
                    mp_hands.HAND_CONNECTIONS
                )

                cv2.putText(
                    frame,
                    f"Fingers: {finger_count}",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 255, 255),
                    2
                )

            else:
                hand_detected = False
                finger_count = 0
                gesture_name = "NO HAND DETECTED"

        else:
            hand_detected = False
            finger_count = 0
            gesture_name = "DETECTION PAUSED"

        encoded, buffer = cv2.imencode(".jpg", frame)

        if not encoded:
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + buffer.tobytes()
            + b"\r\n"
        )


# ==================================================
# API: REGISTER ACCOUNT
# ==================================================

@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}

    username = str(data.get("username", "")).strip()
    password = data.get("password", "")

    if not isinstance(password, str):
        return jsonify({
            "success": False,
            "message": "Invalid password."
        }), 400

    if not re.fullmatch(r"[A-Za-z0-9_]{3,30}", username):
        return jsonify({
            "success": False,
            "message": "Username must contain 3-30 letters, numbers, or underscores."
        }), 400

    if not 8 <= len(password) <= 128:
        return jsonify({
            "success": False,
            "message": "Password must be 8-128 characters long."
        }), 400

    password_hash = generate_password_hash(password)

    try:
        with get_db() as connection:
            connection.execute(
                """
                INSERT INTO users (username, password_hash)
                VALUES (?, ?)
                """,
                (username, password_hash)
            )

        session.clear()
        session["username"] = username

        return jsonify({
            "success": True,
            "message": "Account created successfully.",
            "username": username
        }), 201

    except sqlite3.IntegrityError:
        return jsonify({
            "success": False,
            "message": "That username already exists. Please log in."
        }), 409

    except sqlite3.Error:
        app.logger.exception("Database error during registration")
        return jsonify({
            "success": False,
            "message": "Database error. Please try again."
        }), 500


# ==================================================
# API: LOGIN
# ==================================================

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    username = str(data.get("username", "")).strip()
    password = data.get("password", "")

    if not username or not isinstance(password, str) or not password:
        return jsonify({
            "success": False,
            "message": "Enter your username and password."
        }), 400

    try:
        with get_db() as connection:
            user = connection.execute(
                """
                SELECT username, password_hash
                FROM users
                WHERE username = ? COLLATE NOCASE
                """,
                (username,)
            ).fetchone()

        if user is None or not check_password_hash(
            user["password_hash"], password
        ):
            return jsonify({
                "success": False,
                "message": "Incorrect username or password."
            }), 401

        session.clear()
        session["username"] = user["username"]

        return jsonify({
            "success": True,
            "message": "Login successful.",
            "username": user["username"]
        }), 200

    except sqlite3.Error:
        app.logger.exception("Database error during login")
        return jsonify({
            "success": False,
            "message": "Database error. Please try again."
        }), 500


# ==================================================
# API: CURRENT USER
# ==================================================

@app.route("/api/me", methods=["GET"])
def current_user():
    username = session.get("username")

    if not username:
        return jsonify({
            "authenticated": False,
            "message": "Please log in."
        }), 401

    return jsonify({
        "authenticated": True,
        "username": username
    })


# ==================================================
# API: LOGOUT
# ==================================================

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()

    return jsonify({
        "success": True,
        "message": "Logged out successfully."
    })


# ==================================================
# API: VIDEO FEED
# ==================================================

@app.route("/video_feed", methods=["GET"])
def video_feed():
    return Response(
        generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


# ==================================================
# API: STATUS
# ==================================================

@app.route("/api/status", methods=["GET"])
def api_status():
    return jsonify({
        "connected": True,
        "status": "online",
        "detection_enabled": detection_enabled,
        "hand_detected": hand_detected,
        "finger_count": finger_count,
        "gesture": gesture_name,
        "gesture_name": gesture_name,
        "username": session.get("username", "Crew Member"),
        "timestamp": time.time(),
        "error": last_error
    })


# ==================================================
# API: TOGGLE DETECTION
# ==================================================

@app.route("/api/toggle_detection", methods=["POST"])
def toggle_detection():
    global detection_enabled
    global hand_detected, finger_count, gesture_name

    detection_enabled = not detection_enabled

    if not detection_enabled:
        hand_detected = False
        finger_count = 0
        gesture_name = "DETECTION PAUSED"

    return jsonify({
        "success": True,
        "detection_enabled": detection_enabled,
        "message": (
            "Detection enabled"
            if detection_enabled
            else "Detection paused"
        )
    })


# ==================================================
# HEALTH CHECK
# ==================================================

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "project": "NULL POINTERS",
        "status": "online",
        "message": "Spacecraft control backend is running."
    })


# ==================================================
# START SERVER
# ==================================================

if __name__ == "__main__":
    print("=" * 48)
    print("       NULL POINTERS BACKEND")
    print("=" * 48)

    initialize_database()

    print("Backend: http://127.0.0.1:5000")
    print("Status:  http://127.0.0.1:5000/api/status")
    print("Camera:  http://127.0.0.1:5000/video_feed")
    print("Press CTRL+C to stop.")

    try:
        open_camera()

        app.run(
            host="127.0.0.1",
            port=5000,
            debug=False,
            threaded=True,
            use_reloader=False
        )
    finally:
        release_camera()
        hands.close()
