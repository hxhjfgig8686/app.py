from flask import Flask, render_template, request, redirect, session, jsonify
import requests, json, re, os, uuid, threading, time

app = Flask(__name__)
app.secret_key = "secret123"

BASE = "https://www.ivasms.com"

COOKIES = os.getenv("COOKIES")
TOKEN = os.getenv("TOKEN")

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "X-Requested-With": "XMLHttpRequest",
    "Cookie": COOKIES
}

# ================= DB =================

def load(file):
    try:
        return json.load(open(file))
    except:
        return []

def save(file, data):
    json.dump(data, open(file, "w"))

# ================= OTP =================

def extract_otp(text):
    m = re.search(r'\b\d{4,6}\b', text)
    return m.group() if m else None

def clean(text):
    return re.sub(r'<.*?>', '', text).strip()

# ================= IVASMS FETCH =================

def fetch_ivasms():
    while True:
        try:
            url = BASE + "/portal/sms/received/getsms/number"

            r = requests.post(url, headers=HEADERS, data={
                "_token": TOKEN,
                "range": "1",
                "start": "",
                "end": ""
            }, timeout=20)

            text = clean(r.text)
            otp = extract_otp(text)

            if otp:
                db = load("database.json")

                entry = {
                    "msg": text,
                    "otp": otp
                }

                if entry not in db:
                    db.append(entry)
                    save("database.json", db)
                    print("NEW OTP:", otp)

        except Exception as e:
            print("ERROR:", e)

        time.sleep(5)

# ================= START THREAD =================

threading.Thread(target=fetch_ivasms, daemon=True).start()

# ================= AUTH =================

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        if request.form["user"] == "admin" and request.form["pass"] == "1234":
            session["login"] = True
            return redirect("/")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ================= DASHBOARD =================

@app.route("/")
def dashboard():
    if not session.get("login"):
        return redirect("/login")

    messages = load("database.json")
    return render_template("dashboard.html",
        total=len(messages),
        messages_data=messages[::-1]
    )

# ================= API =================

@app.route("/api/messages")
def api():
    return jsonify(load("database.json"))

# ================= RUN =================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
