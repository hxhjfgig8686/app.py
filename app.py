from flask import Flask, render_template, request, redirect, session, jsonify
import cloudscraper, json, re, os, threading, time, requests

app = Flask(__name__)
app.secret_key = "secret123"

BASE = "https://www.ivasms.com"

COOKIES = os.getenv("COOKIES")
TOKEN = os.getenv("TOKEN")

# فك تشفير التوكن
TOKEN = requests.utils.unquote(TOKEN)

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "X-Requested-With": "XMLHttpRequest",
    "Cookie": COOKIES,
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Referer": "https://www.ivasms.com/portal/sms/received",
    "X-CSRF-TOKEN": TOKEN
}

# ================= DB =================

def load(file):
    try:
        with open(file, "r") as f:
            return json.load(f)
    except:
        return []

def save(file, data):
    with open(file, "w") as f:
        json.dump(data, f)

# ================= OTP =================

def extract_otp(text):
    m = re.search(r'\b\d{4,6}\b', text)
    return m.group() if m else None

def clean(text):
    return re.sub(r'<.*?>', '', text).strip()

# ================= FETCH =================

def fetch_ivasms():
    print("🚀 FETCH STARTED")

    scraper = cloudscraper.create_scraper()

    while True:
        try:
            url = BASE + "/portal/sms/received/getsms/number"

            r = scraper.post(url, headers=HEADERS, data={
                "_token": TOKEN,
                "range": "1",
                "start": "",
                "end": ""
            }, timeout=20)

            print("STATUS:", r.status_code)

            html = r.text

            rows = re.findall(r'<tr.*?>(.*?)</tr>', html, re.DOTALL)

            for row in rows:
                cols = re.findall(r'<td.*?>(.*?)</td>', row, re.DOTALL)

                if len(cols) >= 3:
                    number = clean(cols[0])
                    message = clean(cols[1])
                    date = clean(cols[2])

                    otp = extract_otp(message)

                    if otp:
                        db = load("database.json")

                        entry = {
                            "number": number,
                            "msg": message,
                            "otp": otp,
                            "date": date
                        }

                        if entry not in db:
                            db.append(entry)
                            save("database.json", db)

                            print("✅ NEW MESSAGE")
                            print("📞", number)
                            print("📩", message)
                            print("🔐", otp)

        except Exception as e:
            print("❌ ERROR:", e)

        time.sleep(5)

# ================= THREAD =================

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