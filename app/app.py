import re
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_session import Session
from flask_socketio import SocketIO, emit, join_room

from config import Config
from utils.db import init_db, get_connection
from utils.auth import hash_password, verify_password
from utils.crypto import (
    generate_keys,
    encrypt_for_chat,
    decrypt_chat,
    sign_message,
    verify_signature
)
app = Flask(__name__)
app.config.from_object(Config)

Session(app)
socketio = SocketIO(app, cors_allowed_origins="*")

init_db()


@app.route("/")
def home():
    if "user" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"].strip()
        password = request.form["password"].strip()

        # username validation
        if not re.fullmatch(r"[A-Za-z0-9_]+", username):
            flash("Invalid input")
            return redirect("/register")

        # password validation:
        # 8-10 chars
        # uppercase + lowercase + number
        # only _ allowed as symbol
        pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d_]{8,10}$"

        if not re.fullmatch(pattern, password):
            flash("Invalid input")
            return redirect("/register")

        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM users WHERE username=?",
            (username,)
        )

        if cur.fetchone():
            conn.close()
            flash("Invalid input")
            return redirect("/register")

        public_key, private_key = generate_keys()
        hashed = hash_password(password)

        cur.execute("""
        INSERT INTO users(username,password,public_key,private_key)
        VALUES(?,?,?,?)
        """, (username, hashed, public_key, private_key))

        conn.commit()
        conn.close()

        flash("Account created")
        return redirect("/login")

    return render_template("register.html")


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE username=?", (username,))
        user = cur.fetchone()
        conn.close()

        if user and verify_password(user["password"], password):
            session["user"] = username
            return redirect("/dashboard")

        flash("Invalid login")

    return render_template("login.html")


# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT username FROM users WHERE username != ?", (session["user"],))
    users = cur.fetchall()

    conn.close()

    return render_template("dashboard.html", users=users, current=session["user"])


# ---------------- CHAT PAGE ----------------
@app.route("/chat/<receiver>")
def chat(receiver):
    if "user" not in session:
        return redirect("/login")

    return render_template(
        "chat.html",
        sender=session["user"],
        receiver=receiver
    )


# ---------------- SEND MESSAGE ----------------
@app.route("/send", methods=["POST"])
def send():
    if "user" not in session:
        return "Unauthorized"

    sender = session["user"]
    receiver = request.form["receiver"]
    message = request.form["message"]

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT username, public_key FROM users WHERE username IN (?,?)",
        (sender, receiver)
    )

    rows = cur.fetchall()

    keys = {}
    for row in rows:
        keys[row["username"]] = row["public_key"]

    wrapped_sender, wrapped_receiver, nonce, ciphertext, tag = encrypt_for_chat(
        message,
        keys[sender],
        keys[receiver]
    )

    ist_time = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
    INSERT INTO messages(
    sender, receiver,
    wrapped_key_sender,
    wrapped_key_receiver,
    nonce, ciphertext, tag,
    timestamp
    )
    VALUES(?,?,?,?,?,?,?,?)
    """, (
    sender, receiver,
    wrapped_sender,
    wrapped_receiver,
    nonce, ciphertext, tag,
    ist_time
    ))

    conn.commit()
    conn.close()

    return "sent"


# ---------------- LOAD MESSAGES ----------------
@app.route("/messages/<receiver>")
def messages(receiver):
    if "user" not in session:
        return jsonify([])

    current = session["user"]

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
    "SELECT private_key FROM users WHERE username=?",
    (current,)
    )

    row = cur.fetchone()

    if not row:
        session.clear()
        return jsonify([])

    private_key = row["private_key"]

    cur.execute("""
    SELECT * FROM messages
    WHERE (sender=? AND receiver=?)
       OR (sender=? AND receiver=?)
    ORDER BY id ASC
    """, (current, receiver, receiver, current))

    rows = cur.fetchall()

    result = []

    for row in rows:

        if row["sender"] == current:
            wrapped_key = row["wrapped_key_sender"]
        else:
            wrapped_key = row["wrapped_key_receiver"]

        try:
            text = decrypt_chat(
                wrapped_key,
                row["nonce"],
                row["ciphertext"],
                row["tag"],
                private_key
            )
        except Exception:
            text = "[Decrypt Error]"

        cur.execute(
        "SELECT public_key FROM users WHERE username=?",
        (row["sender"],)
        )
        pub = cur.fetchone()["public_key"]

        if row["signature"]:
            valid = verify_signature(
            pub,
            row["ciphertext"],
            row["signature"]
        )
        else:
            valid = False

        now = datetime.now(ZoneInfo("Asia/Kolkata"))
        dt = datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S")

        if dt.date() == now.date():
            formatted_time = dt.strftime("%I:%M %p")
        elif (now.date() - dt.date()).days == 1:
            formatted_time = "Yesterday"
        else:
            formatted_time = dt.strftime("%d/%m/%y")

        result.append({
        "sender": row["sender"],
        "message": text,
        "time": formatted_time,
        "verified": valid
        })

    conn.close()
    return jsonify(result)


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@socketio.on("join")
def handle_join(data):
    room = data["room"]
    join_room(room)


@socketio.on("send_message")
def handle_send(data):

    sender = data["sender"]
    receiver = data["receiver"]
    message = data["message"]

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT username, public_key FROM users WHERE username IN (?,?)",
        (sender, receiver)
    )

    rows = cur.fetchall()

    keys = {}
    for row in rows:
        keys[row["username"]] = row["public_key"]

    wrapped_sender, wrapped_receiver, nonce, ciphertext, tag = encrypt_for_chat(
        message,
        keys[sender],
        keys[receiver]
    )
    cur.execute(
    "SELECT private_key FROM users WHERE username=?",
    (sender,)
    )
    row = cur.fetchone()
    sender_private_key = row["private_key"]

    signature = sign_message(sender_private_key, ciphertext)

    ist_time = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
    INSERT INTO messages(
    sender,
    receiver,
    wrapped_key_sender,
    wrapped_key_receiver,
    nonce,
    ciphertext,
    tag,
    signature,
    timestamp
    )
    VALUES(?,?,?,?,?,?,?,?,?)
    """, (
    sender,
    receiver,
    wrapped_sender,
    wrapped_receiver,
    nonce,
    ciphertext,
    tag,
    signature,
    ist_time
    ))

    conn.commit()
    conn.close()

    room = "_".join(sorted([sender, receiver]))

    socketio.emit("new_message", {}, to=room)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)