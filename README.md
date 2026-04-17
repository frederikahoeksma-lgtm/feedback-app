# EKX Live Feedback App

A lightweight, self-contained live polling and feedback application.
Participants join via a QR code on their phones and submit answers in real time.
The admin sees live results as they come in.

---

## Prerequisites

Choose **one** of the two methods below.

---

## Method 1 — Docker (recommended, no Python install needed)

### What you need
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) — free, available for Windows, macOS, and Linux

### Steps

```bash
# 1. Open a terminal in this folder
# 2. Build and start the app
docker compose up --build

# 3. Open your browser
#    http://localhost:5000
```

To stop:
```bash
docker compose down
```

Data (sessions, questions, responses) is stored in a Docker volume named `ekx_data`
and persists across restarts.

To change the host port (e.g. use 8080 instead of 5000), edit `docker-compose.yml`:
```yaml
ports:
  - "8080:5000"
```

---

## Method 2 — Direct Python (no Docker needed)

### What you need
- [Python 3.9 or higher](https://www.python.org/downloads/)
  - During Windows installation, check **"Add Python to PATH"**

### macOS / Linux

```bash
# In a terminal, navigate to this folder, then:
bash run.sh
```

### Windows

Double-click **`run_windows.bat`**  
or open Command Prompt in this folder and run:
```cmd
run_windows.bat
```

The script will:
1. Create a Python virtual environment (`venv/`)
2. Install all dependencies from `requirements.txt`
3. Start the server

---

## Using the app

1. Open **http://localhost:5000** in your browser (the admin interface)
2. Click **New Session** to create a feedback session
3. Add your questions — five answer types are supported:
   - Open Text
   - Single Choice
   - Multiple Choice
   - Rating 1–5
   - Yes / No
4. On the session page, a **QR code** is displayed — project it on a screen or share the link
5. Participants scan the QR code on their phones and submit feedback
6. The **Live Results** tab updates in real time as responses arrive

### Network access for participants

Participants must be on the **same Wi-Fi network** as the machine running the app.
The QR code is automatically generated with your local network IP (e.g. `http://192.168.1.x:5000`).

If you are using Docker and participants cannot reach the app, ensure your firewall
allows inbound connections on port 5000.

---

## File structure

```
feedback_app/
├── app.py                 # Flask backend (routes, database, WebSocket)
├── requirements.txt       # Python dependencies
├── Dockerfile             # Container definition
├── docker-compose.yml     # One-command Docker startup
├── run.sh                 # Direct-run script (macOS / Linux)
├── run_windows.bat        # Direct-run script (Windows)
├── static/                # Static assets (empty, extendable)
└── templates/
    ├── base.html          # Shared admin layout and styles
    ├── index.html         # Session list
    ├── new_session.html   # Session + question builder (3-step wizard)
    ├── admin_session.html # Session admin: QR code, live results, responses
    ├── feedback.html      # Participant feedback form (mobile-optimised)
    └── error.html         # Error page (session closed / not found)
```

---

## Changing the port

**Docker:**  Edit `docker-compose.yml`, change `"5000:5000"` to e.g. `"8080:5000"`, then restart.

**Direct Python:**  Set the `PORT` environment variable before running:
```bash
PORT=8080 bash run.sh          # macOS / Linux
set PORT=8080 && run_windows.bat  # Windows
```

---

## Technical details

| Component | Technology |
|-----------|-----------|
| Backend   | Python 3.9+, Flask 3, Flask-SocketIO 5 |
| Real-time | WebSocket via Socket.IO |
| Database  | SQLite (single file, zero config) |
| QR codes  | `qrcode` + `Pillow` |
| Frontend  | Vanilla HTML / CSS / JS (no framework) |
| Styling   | SAP Fiori-inspired color palette |
