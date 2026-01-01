from flask import Flask, render_template, request, redirect, session, flash, url_for
import sqlite3
import os
from notifications import send_alert # Ensure notifications.py is updated to the email-only version

app = Flask(__name__)
app.secret_key = "free_project_viva_safe_key"

# ---------------- DATABASE CONFIGURATION ----------------
if not os.path.exists('instance'):
    os.makedirs('instance') # Create folder if missing to avoid OperationalError

def get_db():
    db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "instance", "database.db")
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    cur = db.cursor()
    
    # Users Table
    cur.execute("""CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                name TEXT, email TEXT, phone TEXT, 
                password TEXT, type TEXT)""")
    
    # Donors Table
    cur.execute("""CREATE TABLE IF NOT EXISTS donors(
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                name TEXT, email TEXT, phone TEXT, 
                password TEXT, donor_type TEXT, 
                blood_group TEXT, 
                hla1 TEXT, hla2 TEXT, hla3 TEXT, 
                hla4 TEXT, hla5 TEXT, hla6 TEXT, 
                hb REAL, available INTEGER)""")
    
    # Requests Table
    cur.execute("""CREATE TABLE IF NOT EXISTS requests(
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                user_id INTEGER, type TEXT, 
                blood_group TEXT, hla1 TEXT, hla2 TEXT, hla3 TEXT, 
                hla4 TEXT, hla5 TEXT, hla6 TEXT, 
                urgency TEXT, hospital TEXT, 
                amount TEXT, req_date TEXT, status TEXT)""")
    
    # Responses Table
    cur.execute("""CREATE TABLE IF NOT EXISTS donor_responses(
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                request_id INTEGER, donor_id INTEGER, 
                response TEXT)""")
    db.commit()
    db.close()

init_db()

# ---------------- AUTHENTICATION ----------------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/user_register/<type>", methods=["GET", "POST"])
def user_register(type):
    if request.method == "POST":
        db = get_db()
        cur = db.cursor()
        cur.execute("INSERT INTO users(name,email,phone,password,type) VALUES(?,?,?,?,?)",
                    (request.form["name"], request.form["email"], request.form["phone"], request.form["password"], type))
        db.commit()
        db.close()
        return redirect(url_for('user_login', type=type))
    return render_template(f"{type}_user_register.html")

@app.route("/donor_register/<type>", methods=["GET", "POST"])
def donor_register(type):
    if request.method == "POST":
        f = request.form
        db = get_db()
        cur = db.cursor()
        cur.execute("""INSERT INTO donors(name,email,phone,password,donor_type,blood_group,hla1,hla2,hla3,hla4,hla5,hla6,hb,available) 
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", 
                    (f["name"], f["email"], f["phone"], f["password"], type, f.get("blood_group", ""), 
                     f.get("hla1", ""), f.get("hla2", ""), f.get("hla3", ""), f.get("hla4", ""), f.get("hla5", ""), f.get("hla6", ""), 
                     f.get("hb", 0), 1))
        db.commit()
        db.close()
        return redirect(url_for('donor_login', type=type))
    return render_template(f"{type}_donor_register.html")

@app.route("/user_login/<type>", methods=["GET", "POST"])
def user_login(type):
    if request.method == "POST":
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT * FROM users WHERE email=? AND password=? AND type=?",
                    (request.form["email"], request.form["password"], type))
        user = cur.fetchone()
        db.close()
        if user:
            session.clear()
            session["user_id"] = user["id"]
            session["user_type"] = type
            return redirect(url_for(f'{type}_user_dashboard'))
        flash("Invalid Credentials")
    return render_template(f"{type}_user_login.html")

@app.route("/donor_login/<type>", methods=["GET", "POST"])
def donor_login(type):
    if request.method == "POST":
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT * FROM donors WHERE email=? AND password=? AND donor_type=?",
                    (request.form["email"], request.form["password"], type))
        donor = cur.fetchone()
        db.close()
        if donor:
            session.clear()
            session["donor_id"] = donor["id"]
            session["donor_type"] = donor["donor_type"]
            return redirect(url_for('donor_dashboard'))
        flash("Invalid Credentials")
    return render_template(f"{type}_donor_login.html")

# ---------------- DASHBOARDS ----------------

@app.route("/blood_user_dashboard", methods=["GET", "POST"])
def blood_user_dashboard():
    if "user_id" not in session: return redirect("/")
    db = get_db()
    cur = db.cursor()
    if request.method == "POST":
        f = request.form
        cur.execute("INSERT INTO requests(user_id,type,blood_group,urgency,hospital,amount,req_date,status) VALUES(?,?,?,?,?,?,?,?)",
                    (session["user_id"], "blood", f["blood_group"], f["urgency"], f["hospital"], f["amount"], f["req_date"], "Pending"))
        db.commit()
        flash("Request submitted successfully.")
    
    cur.execute("""SELECT d.name, d.phone, d.email FROM donor_responses r JOIN requests req ON req.id=r.request_id 
                JOIN donors d ON d.id=r.donor_id WHERE r.response='Accepted' AND req.user_id=?""", (session["user_id"],))
    donors = cur.fetchall()
    db.close()
    return render_template("blood_user_dashboard.html", donors=donors)

@app.route("/marrow_user_dashboard", methods=["GET", "POST"])
def marrow_user_dashboard():
    if "user_id" not in session: return redirect("/")
    db = get_db()
    cur = db.cursor()
    if request.method == "POST":
        f = request.form
        cur.execute("INSERT INTO requests(user_id,type,hla1,hla2,hla3,hla4,hla5,hla6,urgency,hospital,amount,req_date,status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (session["user_id"], "marrow", f["hla1"], f["hla2"], f["hla3"], f["hla4"], f["hla5"], f["hla6"], f["urgency"], f["hospital"], f["amount"], f["req_date"], "Pending"))
        db.commit()
        flash("Registry search initiated.")
    
    cur.execute("""SELECT d.name, d.phone, d.email FROM donor_responses r JOIN requests req ON req.id=r.request_id 
                JOIN donors d ON d.id=r.donor_id WHERE r.response='Accepted' AND req.user_id=?""", (session["user_id"],))
    donors = cur.fetchall()
    db.close()
    return render_template("marrow_user_dashboard.html", donors=donors)

# ---------------- DONOR DASHBOARD & MATCHING ----------------

@app.route("/donor_dashboard", methods=["GET", "POST"])
def donor_dashboard():
    if "donor_id" not in session: return redirect("/")
    db = get_db()
    cur = db.cursor()

    if request.method == "POST":
        cur.execute("UPDATE donors SET available=?, hb=?, phone=? WHERE id=?", 
                    (request.form["available"], request.form["hb"], request.form["phone"], session["donor_id"]))
        db.commit()
        flash("Profile Updated.")

    cur.execute("SELECT * FROM donors WHERE id=?", (session["donor_id"],))
    donor = cur.fetchone()
    
    eligible = []
    if int(donor["available"]) == 1 and (donor["hb"] and float(donor["hb"]) >= 12.5):
        cur.execute("SELECT * FROM requests WHERE status='Pending' AND type=?", (donor["donor_type"],))
        all_reqs = cur.fetchall()
        for r in all_reqs:
            if donor["donor_type"] == "blood":
                if r["blood_group"].strip().upper() == donor["blood_group"].strip().upper():
                    eligible.append({"request": r, "score": None})
            else:
                d_hla = [donor[f'hla{i}'] for i in range(1,7)]
                r_hla = [r[f'hla{i}'] for i in range(1,7)]
                score = sum(1 for d_v, r_v in zip(d_hla, r_hla) if d_v and r_v and d_v.strip().lower() == r_v.strip().lower())
                if score >= 4:
                    eligible.append({"request": r, "score": score})

    db.close()
    return render_template("donor_dashboard.html", requests=eligible, donor=donor)

# ---------------- THE FREE EMAIL ACCEPT ROUTE ----------------

@app.route("/accept/<rid>")
def accept(rid):
    if "donor_id" not in session: return redirect("/")
    db = get_db()
    cur = db.cursor()
    
    cur.execute("SELECT name, phone, email FROM donors WHERE id=?", (session["donor_id"],))
    donor = cur.fetchone()
    
    cur.execute("""SELECT r.hospital, r.type, u.email, u.name 
                FROM requests r JOIN users u ON r.user_id = u.id WHERE r.id=?""", (rid,))
    req = cur.fetchone()

    cur.execute("INSERT INTO donor_responses(request_id, donor_id, response) VALUES(?,?,?)", (rid, session["donor_id"], "Accepted"))
    cur.execute("UPDATE requests SET status='Accepted' WHERE id=?", (rid,))
    db.commit()
    db.close()

    # TRIGGER FREE EMAIL ALERTS
    # To Patient
    subj_user = "URGENT: Donor Match Found!"
    body_user = f"Hello {req['name']},\n\nGood news! A donor ({donor['name']}) has accepted your {req['type']} request for {req['hospital']}.\n\nDonor Contact Details:\nPhone: {donor['phone']}\nEmail: {donor['email']}\n\nPlease contact them immediately."
    send_alert(req['email'], subj_user, body_user)

    # To Donor
    subj_donor = "Acceptance Confirmed"
    body_donor = f"Hello {donor['name']},\n\nYou have accepted the request for {req['hospital']}. The patient has been notified with your contact details."
    send_alert(donor['email'], subj_donor, body_donor)

    flash("Request accepted. Emails sent successfully.")
    return redirect(url_for('donor_dashboard'))

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)