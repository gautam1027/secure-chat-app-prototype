from flask import Flask, render_template, request, redirect, session, jsonify, flash
from flask_socketio import SocketIO, join_room
from utils.db import get_connection, init_db
from utils.crypto import sign_message, verify_signature, encrypt_for_chat, decrypt_chat
from utils.crypto import generate_rsa_keys,encrypt_private_key,decrypt_private_key

from datetime import datetime
from zoneinfo import ZoneInfo

import hashlib
import re

app = Flask(__name__)
app.secret_key = "secret123"

socketio = SocketIO(app, cors_allowed_origins="*")

init_db()

# ---------------- AUTH ---------------- #

@app.route("/")
def root():
    return redirect("/login")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if not (8 <= len(password) <= 10):
            flash("Password must be 8-10 characters long")
            return redirect("/register")

        if not re.search(r"[A-Z]", password):
            flash("Must contain uppercase")
            return redirect("/register")

        if not re.search(r"[a-z]", password):
            flash("Must contain lowercase")
            return redirect("/register")

        if not re.search(r"[0-9]", password):
            flash("Must contain number")
            return redirect("/register")

        if re.search(r"[^a-zA-Z0-9_]", password):
            flash("Only '_' allowed")
            return redirect("/register")

        from utils.crypto import generate_rsa_keys

        hashed = hashlib.sha256(password.encode()).hexdigest()

# 🔐 generate keys
        public_key, private_key = generate_rsa_keys()
        encrypted_private = encrypt_private_key(private_key, password)

        conn = get_connection()
        cur = conn.cursor()

        try:
            cur.execute(
            "INSERT INTO users(username, password, public_key, private_key) VALUES(?,?,?,?)",
            (username, hashed, public_key, encrypted_private)
            )
            conn.commit()
        except:
            flash("Username already exists")
            return redirect("/register")

        conn.close()
        return redirect("/login")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        hashed = hashlib.sha256(password.encode()).hexdigest()

        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, hashed)
        )

        user = cur.fetchone()
        conn.close()

        if user:
            session["user"] = username
            session["password"] = password
            return redirect("/dashboard")

        flash("Invalid username or password")
        return render_template("login.html", username=username)

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ---------------- DASHBOARD ---------------- #

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    current = session["user"]

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT u.username, MAX(m.timestamp) as last_msg
    FROM users u
    LEFT JOIN messages m
    ON (u.username = m.sender AND m.receiver=?)
    OR (u.username = m.receiver AND m.sender=?)
    WHERE u.username != ?
    GROUP BY u.username
    ORDER BY last_msg DESC
    """, (current, current, current))

    users = cur.fetchall()

    cur.execute("""
    SELECT sender, COUNT(*) as unread
    FROM messages
    WHERE receiver=? AND seen=0
    GROUP BY sender
    """, (current,))

    unread_map = {row["sender"]: row["unread"] for row in cur.fetchall()}

    conn.close()

    return render_template(
        "dashboard.html",
        users=users,
        unread_map=unread_map,
        current=current
    )


# ---------------- CHAT PAGE ---------------- #

@app.route("/chat/<receiver>")
def chat(receiver):
    if "user" not in session:
        return redirect("/login")

    return render_template("chat.html", receiver=receiver)


# ---------------- SOCKET ---------------- #

@socketio.on("join")
def on_join(data):
    join_room(data["room"])


@socketio.on("send_message")
def handle_send(data):

    sender = data["sender"]
    receiver = data["receiver"]
    message = data["message"]

    conn = get_connection()
    cur = conn.cursor()

    # get keys
    cur.execute("SELECT public_key, private_key FROM users WHERE username=?", (sender,))
    sender_row = cur.fetchone()

    cur.execute("SELECT public_key FROM users WHERE username=?", (receiver,))
    receiver_row = cur.fetchone()

    sender_pub = sender_row["public_key"]
    private_key = decrypt_private_key(sender_row["private_key"], session["password"])
    receiver_pub = receiver_row["public_key"]

    # 🔐 Encrypt (AES + RSA wrapping)
    wrapped_sender, wrapped_receiver, nonce, ciphertext, tag = encrypt_for_chat(
        message,
        sender_pub,
        receiver_pub
    )

    # 🔏 Sign full payload
    data_to_sign = nonce + ciphertext + tag
    signature = sign_message(private_key, data_to_sign)

    ist_time = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
    INSERT INTO messages(
        sender, receiver,
        wrapped_key_sender,
        wrapped_key_receiver,
        nonce,
        ciphertext,
        tag,
        signature,
        timestamp,
        seen,
        forwarded
    )
    VALUES(?,?,?,?,?,?,?,?,?,?,?)
    """, (
        sender,
        receiver,
        wrapped_sender,
        wrapped_receiver,
        nonce,
        ciphertext,
        tag,
        signature,
        ist_time,
        0,
        0
    ))

    conn.commit()
    conn.close()

    room = "_".join(sorted([sender, receiver]))
    socketio.emit("new_message", {}, room=room)


# ---------------- FETCH MESSAGES ---------------- #

@app.route("/messages/<receiver>")
def get_messages(receiver):
    if "user" not in session:
        return jsonify([])

    current = session["user"]

    conn = get_connection()
    cur = conn.cursor()

    # mark seen
    cur.execute("""
    UPDATE messages
    SET seen=1
    WHERE sender=? AND receiver=? AND seen=0
    """, (receiver, current))

    conn.commit()

    cur.execute("""
    SELECT * FROM messages
    WHERE (sender=? AND receiver=?)
    OR (sender=? AND receiver=?)
    ORDER BY timestamp
    """, (current, receiver, receiver, current))

    rows = cur.fetchall()

    result = []
    now = datetime.now(ZoneInfo("Asia/Kolkata"))

    for row in rows:

        try:
            dt = datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S")
        except:
            dt = now

        if dt.date() == now.date():
            formatted_time = dt.strftime("%I:%M %p")
        elif (now.date() - dt.date()).days == 1:
            formatted_time = "Yesterday"
        else:
            formatted_time = dt.strftime("%d/%m/%y")

        # 🔐 Verify signature FIRST
        cur.execute("SELECT public_key FROM users WHERE username=?", (row["sender"],))
        pub_key = cur.fetchone()["public_key"]

        data = row["nonce"] + row["ciphertext"] + row["tag"]
        verified = verify_signature(pub_key, data, row["signature"])

        # 🔓 Decrypt
        wrapped_key = row["wrapped_key_receiver"] if row["receiver"] == current else row["wrapped_key_sender"]

        cur.execute("SELECT private_key FROM users WHERE username=?", (current,))
        priv_key = decrypt_private_key(cur.fetchone()["private_key"], session["password"])

        try:
            message = decrypt_chat(
                wrapped_key,
                row["nonce"],
                row["ciphertext"],
                row["tag"],
                priv_key
            )
        except:
            message = "[Decryption Failed]"

        result.append({
            "id": row["id"],
            "sender": row["sender"],
            "message": message,
            "time": formatted_time,
            "seen": row["seen"],
            "forwarded": row["forwarded"],
            "verified": verified
        })

    conn.close()

    return jsonify(result)


# ---------------- UNREAD API ---------------- #

@app.route("/unread")
def unread():
    if "user" not in session:
        return jsonify({})

    current = session["user"]

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT sender, COUNT(*) as unread
    FROM messages
    WHERE receiver=? AND seen=0
    GROUP BY sender
    """, (current,))

    data = {row["sender"]: row["unread"] for row in cur.fetchall()}

    conn.close()

    return jsonify(data)


# ---------------- FORWARD ---------------- #

@app.route("/forward", methods=["POST"])
def forward():

    if "user" not in session:
        return "unauthorized", 401

    sender = session["user"]
    data = request.get_json()

    receivers = data["receivers"][:6]
    message = data["message"]

    conn = get_connection()
    cur = conn.cursor()

    ist_time = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")

    for r in receivers:
        cur.execute("""
        INSERT INTO messages(
            sender, receiver,
            ciphertext,
            signature,
            timestamp,
            seen,
            forwarded
        )
        VALUES(?,?,?,?,?,?,?)
        """, (
            sender,
            r,
            message,
            "",
            ist_time,
            0,
            1
        ))

    conn.commit()
    conn.close()

    return "ok"


# ---------------- RUN ---------------- #

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)