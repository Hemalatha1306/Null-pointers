
import cv2
import mediapipe as mp

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("ERROR: Camera could not open")
    raise SystemExit

hands = mp.solutions.hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.3,
    model_complexity=1,
    min_tracking_confidence=0.3
)

print("Show your full hand to the camera. Press Q to quit.")

while True:
    success, frame = camera.read()

    if not success:
        print("ERROR: Cannot read camera frame")
        break

    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)

    count = len(results.multi_hand_landmarks or [])
    print("Landmarks:", count)

    if results.multi_hand_landmarks:
        for hand in results.multi_hand_landmarks:
            mp.solutions.drawing_utils.draw_landmarks(
                frame, hand, mp.solutions.hands.HAND_CONNECTIONS
            )

    cv2.imshow("MediaPipe Hand Test", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

hands.close()
camera.release()
cv2.destroyAllWindows()
