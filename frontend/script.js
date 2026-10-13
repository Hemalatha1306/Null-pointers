
"use strict";

// ==========================================
// ASTROGESTURE - FRONTEND CONTROLLER
// ==========================================

const API = "http://127.0.0.1:5000";

const $ = id => document.getElementById(id);

// ==========================================
// SPACECRAFT SYSTEMS
// These are demonstration values, not real telemetry.
// ==========================================

const systems = {
    1: {
        title: "CABIN ENVIRONMENT",
        instruction: "One finger detected",
        meaning: "One finger selects Cabin Environment.",
        why: "Monitor cabin temperature and cabin pressure.",
        action: "Display cabin temperature and pressure readings.",
        practical: "Helps the crew monitor simulated cabin conditions.",
        label1: "Cabin Temperature",
        value1: "22",
        unit1: "°C",
        label2: "Cabin Pressure",
        value2: "101.3",
        unit2: "kPa"
    },

    2: {
        title: "AIR QUALITY",
        instruction: "Two fingers detected",
        meaning: "Two fingers select Air Quality.",
        why: "Monitor oxygen and carbon dioxide levels.",
        action: "Display oxygen partial pressure and CO₂ level.",
        practical: "Demonstrates hands-free access to simulated air-quality information.",
        label1: "Oxygen Partial Pressure",
        value1: "3.0",
        unit1: "psi",
        label2: "CO₂ Level",
        value2: "3.0",
        unit2: "mmHg"
    },

    3: {
        title: "POWER & PROPULSION",
        instruction: "Three fingers detected",
        meaning: "Three fingers select Power & Propulsion.",
        why: "Monitor battery charge and fuel reserves.",
        action: "Display battery and fuel percentages.",
        practical: "Helps the crew review simulated spacecraft resources.",
        label1: "Battery Level",
        value1: "86",
        unit1: "%",
        label2: "Fuel Reserve",
        value2: "65",
        unit2: "%"
    },

    4: {
        title: "NAVIGATION & STRUCTURE",
        instruction: "Four fingers detected",
        meaning: "Four fingers select Navigation & Structure.",
        why: "Review spacecraft velocity and hull integrity.",
        action: "Display velocity and simulated hull integrity.",
        practical: "Demonstrates hands-free navigation and structure monitoring.",
        label1: "Velocity",
        value1: "7.8",
        unit1: "km/s",
        label2: "Hull Integrity",
        value2: "100",
        unit2: "%"
    },

    5: {
        title: "CREW SAFETY",
        instruction: "Five fingers detected",
        meaning: "Five fingers select Crew Safety.",
        why: "Review simulated crew safety indicators.",
        action: "Display example heart rate and radiation status.",
        practical: "Demonstrates hands-free access to simulated crew safety information.",
        label1: "Crew Heart Rate",
        value1: "78",
        unit1: "BPM",
        label2: "Radiation Status",
        value2: "NORMAL",
        unit2: ""
    }
};

// ==========================================
// APPLICATION STATE
// ==========================================

let detectionEnabled = true;
let currentFingerCount = null;
let pendingFingerCount = null;
let consecutiveReadings = 0;
let lastHandDetected = false;
let requestInProgress = false;
let pollingTimer = null;
let lastBackendOnline = null;

const REQUIRED_READINGS = 2;

// ==========================================
// ACTIVITY LOG
// ==========================================

function addActivity(message) {
    const log = $("activityLog");
    if (!log) return;

    // Ignore identical consecutive log messages.
    const latest = log.firstElementChild;

    if (latest && latest.dataset.message === message) {
        return;
    }

    const entry = document.createElement("p");
    entry.className = "activity-entry";
    entry.dataset.message = message;

    const time = document.createElement("span");
    time.className = "activity-time";
    time.textContent = new Date().toLocaleTimeString();

    entry.appendChild(time);
    entry.appendChild(document.createTextNode(message));

    log.prepend(entry);

    // Keep the latest 10 entries.
    while (log.children.length > 10) {
        log.lastElementChild.remove();
    }
}

// ==========================================
// UPDATE THE HOW IT WORKS SECTION
// ==========================================

function updateInformation(count) {
    const system = systems[count];
    if (!system) return;

    $("infoTitle").textContent = system.title;
    $("infoMeaning").textContent = system.meaning;
    $("infoWhy").textContent = system.why;
    $("infoAction").textContent = system.action;
    $("infoPractical").textContent = system.practical;
}

// ==========================================
// UPDATE SYSTEM PARAMETER CARDS
// ==========================================

function updateParameters(count) {
    const system = systems[count];
    if (!system) return;

    $("parameterLabel1").textContent = system.label1;
    $("parameterValue1").textContent = system.value1;
    $("parameterUnit1").textContent = system.unit1;

    $("parameterLabel2").textContent = system.label2;
    $("parameterValue2").textContent = system.value2;
    $("parameterUnit2").textContent = system.unit2;
}

// ==========================================
// HIGHLIGHT NUMBERED SELECTION
// ==========================================

function highlightButton(count) {
    document.querySelectorAll(".number-command").forEach(button => {
        const selected = Number(button.dataset.finger) === count;

        button.classList.toggle("active-command", selected);
        button.setAttribute("aria-pressed", String(selected));
    });
}

// ==========================================
// SELECT A SPACECRAFT SYSTEM
// ==========================================

function selectSystem(count, source = "camera") {
    const system = systems[count];

    if (!system) return;

    const changed = currentFingerCount !== count;
    currentFingerCount = count;

    $("infoTitle").textContent = system.title;

    updateInformation(count);
    updateParameters(count);
    highlightButton(count);

    if (source === "camera") {
        $("cameraStatusTitle").textContent = system.title;
        $("cameraStatusMessage").textContent =
            `${system.instruction}. ${system.label1}: ` +
            `${system.value1} ${system.unit1}; ${system.label2}: ` +
            `${system.value2} ${system.unit2}.`;
    } else {
        $("cameraStatusTitle").textContent = `${count} — ${system.title}`;
        $("cameraStatusMessage").textContent =
            "Manual selection active. Show the matching number of fingers to select by camera.";
    }

    $("detectionDescription").textContent =
        `Selected: ${count} — ${system.title}`;

    if (changed) {
        const method = source === "camera"
            ? `${count} finger(s) detected`
            : `numbered button ${count} clicked`;

        addActivity(`${system.title} selected — ${method}.`);
    }
}

// ==========================================
// SHOW WAITING STATE
// ==========================================

function showWaiting(message = "Show 1–5 fingers to select a system.") {
    $("cameraStatusTitle").textContent = detectionEnabled
        ? "Waiting for hand..."
        : "Detection paused";

    $("cameraStatusMessage").textContent = message;

    $("detectionHeading").textContent = detectionEnabled
        ? "Hand Detection Active"
        : "Hand Detection Paused";

    $("detectionDescription").textContent = detectionEnabled
        ? "Show one to five fingers to select a system."
        : "Resume detection to use finger controls.";

    $("toggleDetection").textContent = detectionEnabled
        ? "Pause Detection"
        : "Resume Detection";
}

// ==========================================
// BACKEND CONNECTION STATUS
// ==========================================

function setBackendStatus(online) {
    const status = $("systemStatus");

    status.textContent = online ? "SYSTEM ONLINE" : "SYSTEM OFFLINE";
    status.classList.toggle("online", online);
    status.classList.toggle("offline", !online);

    if (lastBackendOnline !== online) {
        if (lastBackendOnline !== null) {
            addActivity(
                online
                    ? "Backend connection restored."
                    : "Backend connection lost."
            );
        }

        lastBackendOnline = online;
    }
}

// ==========================================
// POLL FLASK BACKEND
// ==========================================

async function fetchBackendStatus() {
    if (requestInProgress) return;

    requestInProgress = true;

    try {
        const response = await fetch(`${API}/api/status`, {
            method: "GET",
            cache: "no-store"
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        setBackendStatus(true);

        detectionEnabled = Boolean(data.detection_enabled);
        lastHandDetected = data.hand_detected === true;

        showWaiting(
            lastHandDetected
                ? "Hand detected. Raise one to five fingers."
                : "Waiting for the camera to detect your hand..."
        );

        // Keep the detection toggle synchronized with the backend.
        $("toggleDetection").textContent = detectionEnabled
            ? "Pause Detection"
            : "Resume Detection";

        $("detectionHeading").textContent = detectionEnabled
            ? "Hand Detection Active"
            : "Hand Detection Paused";

        if (!detectionEnabled) {
            pendingFingerCount = null;
            consecutiveReadings = 0;
            currentFingerCount = null;
            highlightButton(null);
            return;
        }

        const count = Number(data.finger_count);

        if (
            lastHandDetected &&
            Number.isInteger(count) &&
            count >= 1 &&
            count <= 5
        ) {
            if (pendingFingerCount === count) {
                consecutiveReadings++;
            } else {
                pendingFingerCount = count;
                consecutiveReadings = 1;
            }

            if (consecutiveReadings >= REQUIRED_READINGS) {
                selectSystem(count, "camera");
            }
        } else {
            pendingFingerCount = null;
            consecutiveReadings = 0;

            if (lastHandDetected && count === 0) {
                $("cameraStatusTitle").textContent = "Hand detected";
                $("cameraStatusMessage").textContent =
                    "Raise one to five fingers clearly toward the camera.";
            }
        }

    } catch (error) {
        console.error("AstroGesture connection error:", error);

        setBackendStatus(false);

        $("cameraStatusTitle").textContent = "Connection Error";
        $("cameraStatusMessage").textContent =
            "Cannot reach Flask. Make sure app.py is running on port 5000.";

        $("detectionDescription").textContent =
            "Waiting for the backend connection.";

    } finally {
        requestInProgress = false;
    }
}

// ==========================================
// PAUSE / RESUME DETECTION
// ==========================================

async function toggleDetection() {
    $("toggleDetection").disabled = true;

    try {
        const response = await fetch(`${API}/api/toggle_detection`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        detectionEnabled = Boolean(data.detection_enabled);

        pendingFingerCount = null;
        consecutiveReadings = 0;

        if (!detectionEnabled) {
            currentFingerCount = null;
            highlightButton(null);
            showWaiting();
            addActivity("Hand detection paused.");
        } else {
            showWaiting();
            addActivity("Hand detection resumed.");
        }

        await fetchBackendStatus();

    } catch (error) {
        console.error("Could not toggle detection:", error);

        $("cameraStatusMessage").textContent =
            "Could not change detection. Check the Flask backend.";

        addActivity("Failed to change detection setting.");

    } finally {
        $("toggleDetection").disabled = false;
    }
}

// ==========================================
// MANUAL BUTTONS 1–5
// ==========================================

function setupNumberButtons() {
    document.querySelectorAll(".number-command").forEach(button => {
        button.addEventListener("click", () => {
            const count = Number(button.dataset.finger);

            if (systems[count]) {
                selectSystem(count, "button");
            }
        });
    });
}

// ==========================================
// CAMERA FEED ERROR HANDLING
// ==========================================

function setupCameraFeed() {
    const camera = $("cameraFeed");
    const placeholder = $("cameraPlaceholder");

    camera.addEventListener("load", () => {
        placeholder.classList.add("hidden");
    });

    camera.addEventListener("error", () => {
        placeholder.classList.remove("hidden");

        addActivity(
            "Camera feed failed to load. Check the Flask camera endpoint."
        );
    });
}

// ==========================================
// INITIALIZE APPLICATION
// ==========================================

function initializeAstroGesture() {
    console.log("NULLPOINTERS initialized.");

    setupNumberButtons();
    setupCameraFeed();

    $("toggleDetection").addEventListener("click", toggleDetection);

    addActivity("AstroGesture initialized. Waiting for system selection.");

    showWaiting("Connecting to recognition system...");

    // Check immediately, then poll every 300 milliseconds.
    fetchBackendStatus();
    pollingTimer = window.setInterval(fetchBackendStatus, 300);
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeAstroGesture);
} else {
    initializeAstroGesture();
}

window.addEventListener("beforeunload", () => {
    if (pollingTimer !== null) {
        window.clearInterval(pollingTimer);
    }
});
