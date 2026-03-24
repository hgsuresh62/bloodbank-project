import smtplib
from email.mime.text import MIMEText
import sqlite3
from flask import Flask, render_template, request, redirect, session, url_for, flash
from functools import wraps

def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


def send_email(subject, body, to_email):
    try:
        sender_email = "bloodbankproject02@gmail.com"
        sender_password = "kvmkeunlgkthyxzh"

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = to_email

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)

        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()

        print("✅ Email sent to", to_email)

    except Exception as e:
        import traceback
        traceback.print_exc()


app = Flask(__name__)
app.secret_key = "bloodbank_secret_key"


# ============================
# LOGIN DECORATOR
# ============================

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):

        if "username" not in session:
            flash("Please login first")
            return redirect(url_for("login_page"))

        return f(*args, **kwargs)

    return wrapper


# ============================
# DATABASE INIT (SQLite Users)
# ============================

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()


# ============================
# ORACLE CONNECTION
# ============================





# ============================
# LOGIN PAGE
# ============================

@app.route("/")
def login_page():
    return render_template("login.html")


# ============================
# REGISTER
# ============================

@app.route("/register", methods=["GET","POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        role = "user"   # user registration only

        conn = get_db()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO users(username,password,role) VALUES(?,?,?)",
                (username, password, role)
            )

            conn.commit()

        except sqlite3.IntegrityError:
            conn.close()

            return render_template(
                "register.html",
                error="Username already exists"
            )

        conn.close()

        flash("Registration Successful ✅ Please Login")
        return redirect(url_for("login_page"))

    return render_template("register.html")


# ============================
# LOGIN
# ============================

@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]
        role = request.form["role"].strip().lower()

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT username,password,role FROM users WHERE username=?",
            (username,)
        )

        user = cursor.fetchone()
        conn.close()

        if user and user["password"] == password and user["role"] == role:

            session.clear()
            session["username"] = user["username"]
            session["role"] = user["role"]

            return redirect(url_for("home"))

        return render_template(
            "login.html",
            error="Invalid Username, Password, or Role"
        )

    return render_template("login.html")


# ============================
# HOME PAGE
# ============================

@app.route("/home")
@login_required
def home():
    return render_template("index.html")


# ============================
# DASHBOARD (OPEN ONLY IF CLICKED)
# ============================

@app.route("/dashboard")
@login_required
def dashboard():

    conn = get_db()
    cursor = conn.cursor()

    # Total Counts
    cursor.execute("SELECT COUNT(*) FROM donors")
    total_donors = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM blood_requests")
    total_requests = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM hospitals")
    total_hospitals = cursor.fetchone()[0]

    # Blood Group Distribution
    cursor.execute("""
        SELECT blood_group, COUNT(*) AS count
        FROM donors
        GROUP BY blood_group
    """)

    blood_data = cursor.fetchall()

    blood_labels = [row["blood_group"] for row in blood_data]
    blood_values = [row["count"] for row in blood_data]

    # Monthly Requests (SQLite version)
    cursor.execute("""
        SELECT strftime('%m', request_date) AS month,
               COUNT(*) AS count
        FROM blood_requests
        GROUP BY month
        ORDER BY month
    """)

    monthly_data = cursor.fetchall()

    month_labels = [row["month"] for row in monthly_data]
    month_values = [row["count"] for row in monthly_data]

    # Recent 5 Requests
    cursor.execute("""
        SELECT patient_name, blood_group, hospital_name, contact
        FROM blood_requests
        ORDER BY request_id DESC
        LIMIT 5
    """)

    recent_requests = cursor.fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        total_donors=total_donors,
        total_requests=total_requests,
        total_hospitals=total_hospitals,
        blood_labels=blood_labels,
        blood_values=blood_values,
        month_labels=month_labels,
        month_values=month_values,
        recent_requests=recent_requests
    )

# ============================
# ADD DONOR
# ============================

import time

@app.route("/add_donor", methods=["GET","POST"])
@login_required
def add_donor():

    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":

        cursor.execute("SELECT COALESCE(MAX(donor_id),0)+1 FROM donors")
        new_id = cursor.fetchone()[0]

        # Insert donor
        cursor.execute("""
        INSERT INTO donors
        (donor_id,name,age,gender,blood_group,district,phone,email,bio)
        VALUES(?,?,?,?,?,?,?,?,?)
        """, (
            new_id,
            request.form["name"],
            request.form["age"],
            request.form["gender"],
            request.form["blood_group"],
            request.form["district"],
            request.form["phone"],
            request.form["email"],
            request.form["bio"]
        ))

        conn.commit()

        # ============================
        # 📧 EMAIL TO ADMIN
        # ============================
        admin_email = "hgsuresh62@gmail.com"

        subject_admin = "New Donor Registered 🩸"

        body_admin = f"""
New Donor Added

Name: {request.form["name"]}
Age: {request.form["age"]}
Gender: {request.form["gender"]}
Blood Group: {request.form["blood_group"]}
District: {request.form["district"]}
Phone: {request.form["phone"]}
Email: {request.form["email"]}

Added By: {session.get("username")} ({session.get("role")})

Blood Bank System
"""

        send_email(subject_admin, body_admin, admin_email)

        # 🔥 ADD DELAY
        time.sleep(2)

        # ============================
        # 📧 EMAIL TO DONOR
        # ============================
        donor_email = request.form["email"]

        subject_user = "Thank You for Donating 🩸"

        body_user = f"""
Hello {request.form["name"]},

Thank you for registering as a blood donor ❤️

Your contribution can save lives.

Blood Bank Team
"""

        send_email(subject_user, body_user, donor_email)

        conn.close()

        flash("Donor Added Successfully & Emails Sent ✅")
        return redirect(url_for("add_donor"))

    conn.close()
    return render_template("add_donor.html")
# ============================
# HOSPITALS
# ============================

@app.route("/hospitals")
@login_required
def hospitals():

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM hospitals")
    hospital_list = cursor.fetchall()

    conn.close()

    return render_template("hospitals.html",
                           hospitals=hospital_list)


# ============================
# VIEW DONORS
# ============================

@app.route("/donors")
@login_required
def donors():

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM donors")
    donors_list = cursor.fetchall()

    conn.close()

    return render_template("donors.html",
                           donors=donors_list)


# ============================
# FIND BLOOD
# ============================

@app.route("/findblood", methods=["GET","POST"])
@login_required
def findblood():

    donors = []

    if request.method == "POST":

        conn = get_db()
        cursor = conn.cursor()

        district = request.form.get("district","").strip()
        blood_group = request.form.get("blood_group","").strip()

        query = "SELECT * FROM donors WHERE 1=1"
        params = []

        if district:
            query += " AND district LIKE ?"
            params.append("%" + district + "%")

        if blood_group:
            query += " AND blood_group = ?"
            params.append(blood_group)

        cursor.execute(query, params)
        donors = cursor.fetchall()

        conn.close()

    return render_template("search.html", donors=donors)


# ============================
# REQUEST BLOOD
# ============================

@app.route("/request-blood", methods=["GET","POST"])
@login_required
def request_blood():

    if request.method == "POST":

        conn = get_db()
        cursor = conn.cursor()

        # Generate new request ID (SQLite version)
        cursor.execute("SELECT COALESCE(MAX(request_id),0)+1 FROM blood_requests")
        new_id = cursor.fetchone()[0]

        patient_name = request.form.get("patient_name")
        blood_group = request.form.get("blood_group")
        hospital_name = request.form.get("hospital_name")
        contact = request.form.get("contact")
        user_email = request.form.get("email")

        # Save request
        cursor.execute("""
        INSERT INTO blood_requests
        (request_id,patient_name,blood_group,hospital_name,contact,email,request_date)
        VALUES(?,?,?,?,?,?,CURRENT_TIMESTAMP)
        """, (
            new_id,
            patient_name,
            blood_group,
            hospital_name,
            contact,
            user_email
        ))

        conn.commit()

        # ---------- Send mail to matching donors ----------
        cursor.execute(
            "SELECT name,email FROM donors WHERE blood_group=?",
            (blood_group,)
        )

        matching_donors = cursor.fetchall()

        for donor in matching_donors:

            subject = "Urgent Blood Request 🚨"

            body = f"""
Hello {donor[0]},

A patient urgently needs {blood_group} blood.

Patient Name: {patient_name}
Hospital: {hospital_name}
Contact: {contact}

If available please help.

Blood Bank Team
"""

            send_email(subject, body, donor[1])

        # ---------- Send confirmation to user ----------
        if user_email:

            subject_user = "Blood Request Submitted Successfully ✅"

            body_user = f"""
Hello {patient_name},

Your request for {blood_group} blood has been received.

Matching donors have been notified.

Blood Bank Team
"""

            send_email(subject_user, body_user, user_email)

        # ---------- Send copy to admin ----------
        admin_email = "hgsuresh62@gmail.com"

        subject_admin = "New Blood Request Alert 🚨"

        body_admin = f"""
New Blood Request Received

Patient Name: {patient_name}
Blood Group: {blood_group}
Hospital: {hospital_name}
Contact: {contact}
User Email: {user_email}

Matching Donors Found: {len(matching_donors)}
"""

        send_email(subject_admin, body_admin, admin_email)

        conn.close()

        flash("Request Submitted & Notifications Sent ✅")
        return redirect(url_for("request_blood"))

    return render_template("request_blood.html")




@app.route("/delete_donor/<int:donor_id>")
@login_required
def delete_donor(donor_id):

    # Allow only admin
    if session.get("role") != "admin":
        flash("Unauthorized Access ❌")
        return redirect(url_for("donors"))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM donors WHERE donor_id=?",
        (donor_id,)
    )

    conn.commit()
    conn.close()

    flash("Donor deleted successfully ✅")
    return redirect(url_for("donors"))






@app.route("/edit_donor/<int:donor_id>", methods=["GET", "POST"])
@login_required
def edit_donor(donor_id):

    # Allow only admin
    if session.get("role") != "admin":
        flash("Unauthorized Access ❌")
        return redirect(url_for("donors"))

    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":

        cursor.execute("""
            UPDATE donors
            SET name=?,
                blood_group=?,
                phone=?
            WHERE donor_id=?
        """, (
            request.form.get("name"),
            request.form.get("blood_group"),
            request.form.get("contact"),
            donor_id
        ))

        conn.commit()
        conn.close()

        flash("Donor updated successfully ✅")
        return redirect(url_for("donors"))

    cursor.execute("SELECT * FROM donors WHERE donor_id=?", (donor_id,))
    donor = cursor.fetchone()

    conn.close()

    return render_template("edit_donor.html", donor=donor)




# ============================
# VIEW BLOOD REQUESTS (ADMIN)
# ============================

@app.route("/blood_requests")
@login_required
def blood_requests():

    # Only admin can view
    if session.get("role") != "admin":
        flash("Access denied ❌ Admin only")
        return redirect(url_for("home"))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT request_id, patient_name, blood_group,
               hospital_name, contact, email
        FROM blood_requests
        ORDER BY request_id DESC
    """)

    requests = cursor.fetchall()

    conn.close()

    return render_template("blood_requests.html", requests=requests)




@app.route("/edit-request/<int:request_id>", methods=["GET","POST"])
@login_required
def edit_request(request_id):

    # Only admin should edit
    if session.get("role") != "admin":
        flash("Access denied ❌ Admin only")
        return redirect(url_for("blood_requests"))

    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":

        cursor.execute("""
        UPDATE blood_requests
        SET patient_name=?,
            blood_group=?,
            hospital_name=?,
            contact=?,
            email=?
        WHERE request_id=?
        """, (
            request.form["patient_name"],
            request.form["blood_group"],
            request.form["hospital_name"],
            request.form["contact"],
            request.form["email"],
            request_id
        ))

        conn.commit()
        conn.close()

        flash("Blood Request Updated Successfully")
        return redirect(url_for("blood_requests"))

    cursor.execute("SELECT * FROM blood_requests WHERE request_id=?", (request_id,))
    request_data = cursor.fetchone()

    conn.close()

    return render_template("edit_request.html", request=request_data)




@app.route("/delete-request/<int:request_id>")
@login_required
def delete_request(request_id):

    # Only admin can delete
    if session.get("role") != "admin":
        flash("Access denied ❌ Admin only")
        return redirect(url_for("blood_requests"))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM blood_requests WHERE request_id=?",
        (request_id,)
    )

    conn.commit()
    conn.close()

    flash("Blood Request Deleted Successfully")

    return redirect(url_for("blood_requests"))




@app.route("/add_hospital", methods=["GET","POST"])
@login_required
def add_hospital():

    if session.get("role") != "admin":
        flash("Unauthorized ❌ Admin only")
        return redirect(url_for("home"))

    if request.method == "POST":

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
INSERT INTO hospitals (name, location, phone)
VALUES (?, ?, ?)
""", (
    request.form.get("name"),
    request.form.get("location"),
    request.form.get("phone")
))

        conn.commit()
        conn.close()

        flash("Hospital added successfully ✅")
        return redirect(url_for("hospitals"))

    return render_template("add_hospital.html")



@app.route("/edit_hospital/<int:id>", methods=["GET","POST"])
@login_required
def edit_hospital(id):

    if session.get("role") != "admin":
        flash("Unauthorized ❌ Admin only")
        return redirect(url_for("hospitals"))

    conn = get_db()
    cursor = conn.cursor()

    try:

        if request.method == "POST":

            cursor.execute("""
            UPDATE hospitals
            SET name=?, location=?, phone=?
            WHERE id=?
            """, (
                request.form.get("name"),
                request.form.get("location"),
                request.form.get("phone"),
                id
            ))

            conn.commit()
            flash("Hospital updated successfully ✅")

            return redirect(url_for("hospitals"))

        cursor.execute("SELECT * FROM hospitals WHERE id=?", (id,))
        hospital = cursor.fetchone()

        conn.close()

        return render_template("edit_hospital.html", hospital=hospital)

    except Exception as e:
        print("Edit hospital error:", e)
        return "Internal Server Error"



@app.route("/delete_hospital/<int:id>")
@login_required
def delete_hospital(id):

    if session.get("role") != "admin":
        flash("Unauthorized ❌ Admin only")
        return redirect(url_for("hospitals"))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM hospitals WHERE id=?", (id,))

    conn.commit()
    conn.close()

    flash("Hospital deleted successfully ✅")
    return redirect(url_for("hospitals"))




# ============================
# LOGOUT
# ============================

@app.route("/logout")
@login_required
def logout():

    session.clear()

    flash("Logged out successfully ✅")

    return redirect(url_for("login_page"))


# ============================
# RUN SERVER
# ============================

import os

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 8000))

app.run(host="0.0.0.0", port=port, debug=True)