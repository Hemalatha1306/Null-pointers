# AstroGesture 🚀
### Camera-Based Hand Gesture Recognition System for Astronauts

**AstroGesture** is a contactless spacecraft interface that allows astronauts to interact with simulated spacecraft systems using hand gestures detected through a camera.

## 🎯 Problem Statement
Touchscreens can be difficult to operate in spacesuits or confined spacecraft environments. AstroGesture explores a hands-free alternative for interacting with spacecraft information.

## ✨ Key Features
- Real-time hand gesture recognition using a camera
- Contactless interaction with a spacecraft dashboard
- Gesture-based navigation between system panels
- Simulated spacecraft monitoring information
- Live gesture feedback and activity logging

## 🛰️ Spacecraft Parameters
The dashboard can display simulated information related to:
- Cabin pressure and temperature
- Oxygen and carbon dioxide levels
- Engine status
- Passenger and crew safety
- Navigation and mission information

## 🛠️ Technologies Used
- **Frontend:** HTML, CSS, JavaScript
- **Backend:** Python and Flask
- **Computer Vision:** OpenCV and MediaPipe
- **Version Control:** Git and GitHub

## ⚙️ How It Works
1. The camera captures the user's hand.
2. MediaPipe detects hand landmarks.
3. Python processes the detected hand and recognizes supported gestures.
4. The Flask backend provides gesture status to the frontend.
5. The dashboard displays the corresponding simulated spacecraft information.

## 🚀 Future Scope
- Improve recognition when wearing gloves.
- Add voice commands as a backup.
- Integrate more spacecraft monitoring parameters.
- Explore integration with simulated spacecraft systems.

## ⚠️ Disclaimer
AstroGesture is an educational prototype. Spacecraft values and controls are simulated and are not intended for real spacecraft operation.

## 👩‍💻 Project Team
**Team:** NULL POINTERS

Developed for a college hackathon project.
