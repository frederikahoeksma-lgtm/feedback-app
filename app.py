import os
import io
import json
import base64
import sqlite3
import qrcode
import socket
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify, session as flask_session
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)
app.secret_key = os.urandom(24)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Template filters
@app.template_filter('from_json')
def from_json_filter(value):
    if value is None:
        return []
    try:
        return json.loads(value)
    except Exception:
        return []

DB_PATH = os.path.join(os.path.dirname(__file__), "feedback.db")

# ─── Database helpers ────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS poll_session (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            description TEXT,
            max_participants INTEGER DEFAULT 20,
            created_at  TEXT DEFAULT (datetime('now')),
            is_active   INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS question (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            text       TEXT NOT NULL,
            type       TEXT NOT NULL DEFAULT 'text',
            options    TEXT,
            position   INTEGER DEFAULT 0,
            FOREIGN KEY (session_id) REFERENCES poll_session(id)
        );
        CREATE TABLE IF NOT EXISTS response (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  INTEGER NOT NULL,
            participant TEXT NOT NULL,
            answers     TEXT NOT NULL,
            submitted_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (session_id) REFERENCES poll_session(id)
        );
    """)
    conn.commit()
    conn.close()

init_db()

# ─── Utility ─────────────────────────────────────────────────────────────────

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def make_qr_base64(url):
    qr = qrcode.QRCode(box_size=8, border=3)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0070F2", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

# ─── Admin routes ─────────────────────────────────────────────────────────────

@app.route("/")
def index():
    conn = get_db()
    sessions = conn.execute("SELECT * FROM poll_session ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("index.html", sessions=sessions)

@app.route("/session/new", methods=["GET", "POST"])
def new_session():
    if request.method == "POST":
        title = request.form["title"].strip()
        description = request.form.get("description", "").strip()
        max_p = int(request.form.get("max_participants", 20))
        questions_json = request.form.get("questions_json", "[]")
        questions = json.loads(questions_json)

        conn = get_db()
        cur = conn.execute(
            "INSERT INTO poll_session (title, description, max_participants) VALUES (?,?,?)",
            (title, description, max_p)
        )
        session_id = cur.lastrowid
        for i, q in enumerate(questions):
            opts = json.dumps(q.get("options", [])) if q.get("options") else None
            conn.execute(
                "INSERT INTO question (session_id, text, type, options, position) VALUES (?,?,?,?,?)",
                (session_id, q["text"], q["type"], opts, i)
            )
        conn.commit()
        conn.close()
        return redirect(url_for("admin_session", session_id=session_id))
    return render_template("new_session.html")

@app.route("/session/<int:session_id>")
def admin_session(session_id):
    conn = get_db()
    sess = conn.execute("SELECT * FROM poll_session WHERE id=?", (session_id,)).fetchone()
    questions = conn.execute("SELECT * FROM question WHERE session_id=? ORDER BY position", (session_id,)).fetchall()
    responses = conn.execute("SELECT * FROM response WHERE session_id=? ORDER BY submitted_at DESC", (session_id,)).fetchall()
    conn.close()

    # Use BASE_URL env var if set (tunnel / cloud deployment)
    # Otherwise detect scheme from request (works on Railway, Render, etc.)
    base_url = os.environ.get("BASE_URL", "").rstrip("/")
    if not base_url:
        scheme = "https" if request.headers.get("X-Forwarded-Proto") == "https" else "http"
        base_url = f"{scheme}://{request.host}"
    feedback_url = f"{base_url}/feedback/{session_id}"
    qr_b64 = make_qr_base64(feedback_url)

    parsed_responses = []
    for r in responses:
        parsed_responses.append({
            "participant": r["participant"],
            "submitted_at": r["submitted_at"],
            "answers": json.loads(r["answers"])
        })

    # Convert sqlite3.Row objects to plain dicts for JSON serialization in templates
    questions_dicts = [dict(q) for q in questions]
    # Parse options JSON string into list for each question
    for q in questions_dicts:
        q["options"] = json.loads(q["options"]) if q.get("options") else []

    return render_template(
        "admin_session.html",
        sess=dict(sess),
        questions=questions_dicts,
        responses=parsed_responses,
        feedback_url=feedback_url,
        qr_b64=qr_b64
    )

@app.route("/session/<int:session_id>/toggle", methods=["POST"])
def toggle_session(session_id):
    conn = get_db()
    sess = conn.execute("SELECT is_active FROM poll_session WHERE id=?", (session_id,)).fetchone()
    new_state = 0 if sess["is_active"] else 1
    conn.execute("UPDATE poll_session SET is_active=? WHERE id=?", (new_state, session_id))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_session", session_id=session_id))

@app.route("/session/<int:session_id>/delete", methods=["POST"])
def delete_session(session_id):
    conn = get_db()
    conn.execute("DELETE FROM response WHERE session_id=?", (session_id,))
    conn.execute("DELETE FROM question WHERE session_id=?", (session_id,))
    conn.execute("DELETE FROM poll_session WHERE id=?", (session_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))

# ─── Participant routes ───────────────────────────────────────────────────────

@app.route("/feedback/<int:session_id>")
def feedback(session_id):
    conn = get_db()
    sess = conn.execute("SELECT * FROM poll_session WHERE id=?", (session_id,)).fetchone()
    if not sess:
        return render_template("error.html", message="This feedback session does not exist."), 404
    questions = conn.execute("SELECT * FROM question WHERE session_id=? ORDER BY position", (session_id,)).fetchall()
    response_count = conn.execute("SELECT COUNT(*) as cnt FROM response WHERE session_id=?", (session_id,)).fetchone()["cnt"]
    conn.close()

    if not sess["is_active"]:
        return render_template("error.html", message="This feedback session is currently closed."), 403
    if response_count >= sess["max_participants"]:
        return render_template("error.html", message="The maximum number of participants has been reached."), 403

    qs = []
    for q in questions:
        opts = json.loads(q["options"]) if q["options"] else []
        qs.append({"id": q["id"], "text": q["text"], "type": q["type"], "options": opts})

    return render_template("feedback.html", sess=sess, questions=qs, session_id=session_id)

@app.route("/feedback/<int:session_id>/submit", methods=["POST"])
def submit_feedback(session_id):
    conn = get_db()
    sess = conn.execute("SELECT * FROM poll_session WHERE id=?", (session_id,)).fetchone()
    if not sess or not sess["is_active"]:
        conn.close()
        return jsonify({"error": "Session closed"}), 403

    response_count = conn.execute("SELECT COUNT(*) as cnt FROM response WHERE session_id=?", (session_id,)).fetchone()["cnt"]
    if response_count >= sess["max_participants"]:
        conn.close()
        return jsonify({"error": "Max participants reached"}), 403

    data = request.get_json()
    participant = data.get("participant", f"Participant {response_count + 1}")
    answers = data.get("answers", {})

    conn.execute(
        "INSERT INTO response (session_id, participant, answers) VALUES (?,?,?)",
        (session_id, participant, json.dumps(answers))
    )
    conn.commit()

    # Refresh count
    new_count = conn.execute("SELECT COUNT(*) as cnt FROM response WHERE session_id=?", (session_id,)).fetchone()["cnt"]
    conn.close()

    # Notify admin room of new response
    socketio.emit("new_response", {
        "participant": participant,
        "answers": answers,
        "count": new_count,
        "max": sess["max_participants"]
    }, room=f"session_{session_id}")

    return jsonify({"success": True, "count": new_count})

# ─── API: live results ─────────────────────────────────────────────────────────

@app.route("/api/session/<int:session_id>/results")
def api_results(session_id):
    conn = get_db()
    questions = conn.execute("SELECT * FROM question WHERE session_id=? ORDER BY position", (session_id,)).fetchall()
    responses = conn.execute("SELECT answers FROM response WHERE session_id=?", (session_id,)).fetchall()
    conn.close()

    results = {}
    for q in questions:
        results[str(q["id"])] = {"text": q["text"], "type": q["type"], "answers": []}

    for r in responses:
        ans = json.loads(r["answers"])
        for qid, val in ans.items():
            if qid in results:
                results[qid]["answers"].append(val)

    return jsonify(results)

# ─── SocketIO ─────────────────────────────────────────────────────────────────

@socketio.on("join_admin")
def on_join_admin(data):
    session_id = data.get("session_id")
    join_room(f"session_{session_id}")

# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") == "development"
    socketio.run(app, host="0.0.0.0", port=port, debug=debug, allow_unsafe_werkzeug=True)
