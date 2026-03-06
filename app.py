import smtplib
from email.mime.text import MIMEText
import oracledb
import sqlite3
from flask import Flask, render_template, request, redirect, session, url_for, flash
from functools import wraps

def send_email(subject, body, to_email):

    sender_email = "bloodbankproject02@gmail.com"
    sender_password = "kvmkeunlgkthyxzh"

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = to_email

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()
        print("Email sent successfully ✅")

    except Exception as e:
        print("Email sending failed ❌", e)


app = Flask(__name__)
app.secret_key = "bloodbank_secret_key"


# ============================
# LOGIN DECORATOR
# ============================

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return wrapper


# ============================
# DATABASE INIT (SQLite Users)
# ============================

def init_db():
    conn = sqlite3.connect("database.db")
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

dsn = oracledb.makedsn("127.0.0.1", 1521, sid="XE")

try:
    connection = oracledb.connect(
        user="system",
        password="suresh",
        dsn=dsn
    )
    print("✅ Oracle Connected")
except Exception as e:
    print("❌ Oracle Connection Error:", e)


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

        # Role is always USER
        role = "user"

        conn = sqlite3.connect("database.db")
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

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            "SELECT username,password,role FROM users WHERE username=?",
            (username,)
        )

        user = cursor.fetchone()
        conn.close()

        # ✅ check username, password AND role
        if user and user[1] == password and user[2] == role:

            session.clear()
            session["username"] = user[0]
            session["role"] = user[2]

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

    cursor = connection.cursor()

    # Total Counts
    cursor.execute("SELECT COUNT(*) FROM donors")
    total_donors = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM blood_requests")
    total_requests = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM hospitals")
    total_hospitals = cursor.fetchone()[0]

    # Blood Group Distribution
    cursor.execute("""
        SELECT blood_group, COUNT(*)
        FROM donors
        GROUP BY blood_group
    """)
    blood_data = cursor.fetchall()

    blood_labels = [row[0] for row in blood_data]
    blood_values = [row[1] for row in blood_data]

    # Monthly Requests
    cursor.execute("""
    SELECT TO_CHAR(request_date, 'Mon') AS month, COUNT(*)
    FROM blood_requests
    GROUP BY TO_CHAR(request_date, 'Mon')
    ORDER BY MIN(request_date)
""")
    monthly_data = cursor.fetchall()

    month_labels = [row[0].strip() for row in monthly_data]
    month_values = [row[1] for row in monthly_data]

    # Recent 5 Requests
    cursor.execute("""
        SELECT patient_name, blood_group, hospital_name, contact
        FROM blood_requests
        ORDER BY request_id DESC
        FETCH FIRST 5 ROWS ONLY
    """)
    recent_requests = cursor.fetchall()

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

@app.route("/add_donor", methods=["GET","POST"])
@login_required
def add_donor():

    if request.method == "POST":

        cursor = connection.cursor()

        cursor.execute("SELECT NVL(MAX(donor_id),0)+1 FROM donors")
        new_id = cursor.fetchone()[0]

        cursor.execute("""
        INSERT INTO donors
        (donor_id,name,age,gender,blood_group,district,phone,email,bio)
        VALUES(:donor_id,:name,:age,:gender,:blood_group,:district,:phone,:email,:bio)
        """, {
            "donor_id": new_id,
            "name": request.form["name"],
            "age": request.form["age"],
            "gender": request.form["gender"],
            "blood_group": request.form["blood_group"],
            "district": request.form["district"],
            "phone": request.form["phone"],
            "email": request.form["email"],
            "bio": request.form["bio"]
        })

        connection.commit()

        flash("Donor Added Successfully ✅")
        return redirect(url_for("add_donor"))

    return render_template("add_donor.html")


# ============================
# HOSPITALS
# ============================

@app.route("/hospitals")
@login_required
def hospitals():

    cursor = connection.cursor()
    cursor.execute("SELECT * FROM hospitals")
    hospital_list = cursor.fetchall()

    return render_template("hospitals.html",
                           hospitals=hospital_list)


# ============================
# VIEW DONORS
# ============================

@app.route("/donors")
@login_required
def donors():

    cursor = connection.cursor()
    cursor.execute("SELECT * FROM donors")
    donors_list = cursor.fetchall()

    return render_template("donors.html",
                           donors=donors_list)


# ============================
# FIND BLOOD
# ============================

@app.route("/findblood", methods=["GET","POST"])
@login_required
def findblood():

    donors = []
    cursor = connection.cursor()

    if request.method == "POST":

        district = request.form.get("district","").strip()
        blood_group = request.form.get("blood_group","").strip()

        query = "SELECT * FROM donors WHERE 1=1"
        params = {}

        if district:
            query += " AND district LIKE :district"
            params["district"] = "%" + district + "%"

        if blood_group:
            query += " AND blood_group = :bg"
            params["bg"] = blood_group

        cursor.execute(query, params)
        donors = cursor.fetchall()

    return render_template("search.html", donors=donors)


# ============================
# REQUEST BLOOD
# ============================

@app.route("/request-blood", methods=["GET","POST"])
@login_required
def request_blood():

    if request.method == "POST":

        cursor = connection.cursor()

        cursor.execute("SELECT NVL(MAX(request_id),0)+1 FROM blood_requests")
        new_id = cursor.fetchone()[0]

        patient_name = request.form.get("patient_name")
        blood_group = request.form.get("blood_group")
        hospital_name = request.form.get("hospital_name")
        contact = request.form.get("contact")
        user_email = request.form.get("email")   # safer than request.form["email"]

        # ===============================
        # SAVE REQUEST IN DATABASE
        # ===============================
        cursor.execute("""
        INSERT INTO blood_requests
        (request_id,patient_name,blood_group,hospital_name,contact,email)
        VALUES(:request_id,:patient_name,:blood_group,:hospital_name,:contact,:email)
        """, {
            "request_id": new_id,
            "patient_name": patient_name,
            "blood_group": blood_group,
            "hospital_name": hospital_name,
            "contact": contact,
            "email": user_email
        })

        connection.commit()

        # ===============================
        # 1️⃣ SEND MAIL TO MATCHING DONORS
        # ===============================
        cursor.execute(
            "SELECT name,email FROM donors WHERE blood_group = :bg",
            {"bg": blood_group}
        )

        matching_donors = cursor.fetchall()

        for donor in matching_donors:

            donor_name = donor[0]
            donor_email = donor[1]

            subject = "Urgent Blood Request 🚨"

            body = f"""
Hello {donor_name},

A patient urgently needs {blood_group} blood.

Patient Name: {patient_name}
Hospital: {hospital_name}
Contact: {contact}

If available please help.

Blood Bank Team
"""

            send_email(subject, body, donor_email)

        # ===============================
        # 2️⃣ SEND CONFIRMATION TO USER
        # ===============================
        if user_email:

            subject_user = "Blood Request Submitted Successfully ✅"

            body_user = f"""
Hello {patient_name},

Your request for {blood_group} blood has been received.

Matching donors have been notified.
They may contact you soon.

Stay strong 💪
Blood Bank Team
"""

            send_email(subject_user, body_user, user_email)

        # ===============================
        # 3️⃣ SEND COPY TO ADMIN
        # ===============================
        admin_email = "hgsuresh62@gmail.com"   # replace with your email

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

        flash("Request Submitted & Notifications Sent ✅")
        return redirect(url_for("request_blood"))

    return render_template("request_blood.html")



@app.route("/delete_donor/<int:donor_id>")
@login_required
def delete_donor(donor_id):

    # ✅ Allow only admin
    if session.get("role") != "admin":
        flash("Unauthorized Access ❌")
        return redirect(url_for("donors"))

    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM donors WHERE donor_id = :1",
        (donor_id,)
    )

    connection.commit()

    flash("Donor deleted successfully ✅")
    return redirect(url_for("donors"))






@app.route("/edit_donor/<int:donor_id>", methods=["GET", "POST"])
@login_required
def edit_donor(donor_id):

    # ✅ Allow only admin
    if session.get("role") != "admin":
        flash("Unauthorized Access ❌")
        return redirect(url_for("donors"))

    cursor = connection.cursor()

    if request.method == "POST":

        cursor.execute("""
            UPDATE donors
            SET name = :1,
                blood_group = :2,
                phone = :3
            WHERE donor_id = :4
        """, (
            request.form.get("name"),
            request.form.get("blood_group"),
            request.form.get("contact"),
            donor_id
        ))

        connection.commit()

        flash("Donor updated successfully ✅")
        return redirect(url_for("donors"))

    cursor.execute(
        "SELECT * FROM donors WHERE donor_id = :1",
        (donor_id,)
    )

    donor = cursor.fetchone()

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

    cursor = connection.cursor()

    cursor.execute("""
        SELECT request_id, patient_name, blood_group,
               hospital_name, contact, email
        FROM blood_requests
        ORDER BY request_id DESC
    """)

    requests = cursor.fetchall()

    return render_template("blood_requests.html", requests=requests)




@app.route("/edit-request/<int:request_id>", methods=["GET","POST"])
def edit_request(request_id):

    cursor = connection.cursor()

    if request.method == "POST":

        cursor.execute("""
        UPDATE blood_requests
        SET patient_name=:patient_name,
            blood_group=:blood_group,
            hospital_name=:hospital_name,
            contact=:contact,
            email=:email
        WHERE request_id=:request_id
        """, {

            "patient_name": request.form["patient_name"],
            "blood_group": request.form["blood_group"],
            "hospital_name": request.form["hospital_name"],
            "contact": request.form["contact"],
            "email": request.form["email"],
            "request_id": request_id
        })

        connection.commit()

        flash("Blood Request Updated Successfully")
        return redirect(url_for("blood_requests"))

    cursor.execute("SELECT * FROM blood_requests WHERE request_id=:1",[request_id])
    request_data = cursor.fetchone()

    return render_template("edit_request.html", request=request_data)




@app.route("/delete-request/<int:request_id>")
def delete_request(request_id):

    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM blood_requests WHERE request_id=:1",
        [request_id]
    )

    connection.commit()

    flash("Blood Request Deleted Successfully")

    return redirect(url_for("blood_requests"))




# ============================
# LOGOUT
# ============================

@app.route("/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("login_page"))


# ============================
# RUN SERVER
# ============================

import os

port = int(os.environ.get("PORT", 8000))
app.run(host="0.0.0.0", port=port)