
import cv2
import mediapipe as mp
import math

# ==========================================
# MEDIAPIPE SETUP
# ==========================================

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

# Shared status read by app.py
latest_status = {
    "gesture": "Waiting for hand...",
    "command": "NONE",
    "detected": False
}


# ==========================================
# GESTURE RECOGNITION
# ==========================================

def classify_gesture(hand):
    """Recognize five hand gestures from landmarks."""

    points = hand.landmark

    def distance(a, b):
        return math.hypot(
            points[a].x - points[b].x,
            points[a].y - points[b].y
        )

    # Finger tip and joint indices
    fingers = {
        "index": (8, 6),
        "middle": (12, 10),
        "ring": (16, 14),
        "pinky": (20, 18)
    }

    extended = {}

    for name, (tip, joint) in fingers.items():
        tip_distance = distance(tip, 0)
        joint_distance = distance(joint, 0)

        extended[name] = (
            tip_distance > joint_distance * 1.10
        )

    index = extended["index"]
    middle = extended["middle"]
    ring = extended["ring"]
    pinky = extended["pinky"]

    # Estimate whether the thumb is extended
    thumb_extended = (
        distance(4, 5) > distance(3, 5) * 1.15
    )

    # Thumb points upward
    thumb_points_up = (
        points[4].y < points[3].y
        and points[4].y < points[2].y
    )

    # 1. Thumbs Up -> Confirm Selection
    if (
        thumb_extended
        and thumb_points_up
        and not index
        and not middle
        and not ring
        and not pinky
    ):
        return "Thumbs Up", "CONFIRM"

    # 2. Victory Sign -> Life Support
    if index and middle and not ring and not pinky:
        return "Victory Sign", "LIFE_SUPPORT"

    # 3. Pointing Up -> Navigation
    if index and not middle and not ring and not pinky:
        return "Pointing Up", "NAVIGATION"

    # 4. Open Palm -> Mission Overview
    if (
        index
        and middle
        and ring
        and pinky
        and thumb_extended
    ):
        return "Open Palm", "MISSION"

    # 5. Closed Fist -> Home
    if (
        not index
        and not middle
        and not ring
        and not pinky
        and not thumb_extended
    ):
        return "Closed Fist", "HOME"

    return "Unclear Gesture", "NONE"


# ==========================================
# WEBCAM AND VIDEO STREAM
# ==========================================

def generate_frames():
    """Read webcam frames, detect hands, and stream video."""

    global latest_status

    camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        latest_status = {
            "gesture": "Camera unavailable",
            "command": "NONE",
            "detected": False
        }

        camera.release()
        print("ERROR: Could not open camera.")
        return

    try:
        with mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            model_complexity=1,
            min_detection_confidence=0.3,
            min_tracking_confidence=0.3
        ) as hands:

            while True:
                success, frame = camera.read()

                if not success:
                    latest_status = {
                        "gesture": "Camera read failed",
                        "command": "NONE",
                        "detected": False
                    }

                    print("ERROR: Could not read camera frame.")
                    break

                # Mirror the webcam image
                frame = cv2.flip(frame, 1)

                # Convert BGR to RGB
                rgb_frame = cv2.cvtColor(
                    frame,
                    cv2.COLOR_BGR2RGB
                )

                # Detect hand landmarks
                results = hands.process(rgb_frame)

                hand_count = len(
                    results.multi_hand_landmarks or []
                )

                print("Backend hands detected:", hand_count)

                if results.multi_hand_landmarks:

                    for hand_landmarks in results.multi_hand_landmarks:

                        # Debug: print number of points
                        print(
                            "Landmark points:",
                            len(hand_landmarks.landmark)
                        )

                        # Draw landmarks and connections
                        mp_draw.draw_landmarks(
                            frame,
                            hand_landmarks,
                            mp_hands.HAND_CONNECTIONS
                        )

                        # Recognize the gesture
                        gesture_name, command = classify_gesture(
                            hand_landmarks
                        )

                        # Update API status
                        latest_status = {
                            "gesture": gesture_name,
                            "command": command,
                            "detected": True
                        }

                        print("UPDATED STATUS:", latest_status)

                        # Display gesture name
                        cv2.putText(
                            frame,
                            gesture_name,
                            (20, 45),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.9,
                            (0, 255, 100),
                            2,
                            cv2.LINE_AA
                        )

                        # Display command
                        cv2.putText(
                            frame,
                            "Command: " + command,
                            (20, 80),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.7,
                            (255, 255, 0),
                            2,
                            cv2.LINE_AA
                        )

                else:
                    latest_status = {
                        "gesture": "No hand detected",
                        "command": "NONE",
                        "detected": False
                    }

                    cv2.putText(
                        frame,
                        "Show your hand to the camera",
                        (20, 45),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 165, 255),
                        2,
                        cv2.LINE_AA
                    )

                # Encode frame as JPEG
                success, buffer = cv2.imencode(".jpg", frame)

                if not success:
                    continue

                frame_bytes = buffer.tobytes()

                # Send frame to browser
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n"
                    + frame_bytes
                    + b"\r\n"
                )

    except Exception as error:
        print("Gesture processing error:", error)

        latest_status = {
            "gesture": "Processing error",
            "command": "NONE",
            "detected": False
        }

    finally:
        camera.release()
        print("Camera released.")
