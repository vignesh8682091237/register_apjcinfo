import os
import json
import base64
import io
from functools import wraps
from collections import Counter

from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session, jsonify, send_file
)
from flask_cors import CORS
from openpyxl import Workbook

import firebase_admin
from firebase_admin import credentials, firestore


# =========================================================
# 🔥 FIREBASE INIT (ENV FIRST, JSON FILE FALLBACK)
# =========================================================

firebase_json = None

# 1️⃣ Try Base64 ENV (Render / Production)
firebase_b64 = os.environ.get("FIREBASE_CREDENTIALS_B64")
if firebase_b64:
    firebase_json = base64.b64decode(firebase_b64).decode("utf-8")



if not firebase_admin._apps:
    cred = credentials.Certificate(json.loads(firebase_json))
    firebase_admin.initialize_app(cred)

db = firestore.client()


# =========================================================
# 🔥 FLASK INIT
# =========================================================

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "dev-secret-key")
CORS(app)


# =========================================================
# 🔐 ADMIN CONFIG
# =========================================================

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@gmail.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated


# =========================================================
# 🏠 HOME
# =========================================================

@app.route("/")
def home():
    return redirect(url_for("register"))


# =========================================================
# 📝 REGISTER
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        data = request.form

        reg_data = {
            "name": data.get("name", "").strip(),
            "whatsapp": data.get("whatsapp", "").strip(),
            "email": data.get("email", "").strip(),
            "qualification": data.get("qualification", "").strip(),
            "designation": data.get("designation", "").strip(),
            "gender": data.get("gender", "").strip(),
            "college_company": data.get("college_company", "").strip(),
            "blood_donation": data.get("blood_donation", "").strip(),
            "blood_group": data.get("blood_group", "").strip(),
            "webinar_interest": data.get("webinar_interest", "").strip(),
            "webinar_date": data.get("webinar_date", "").strip(),
            "registered_at": firestore.SERVER_TIMESTAMP
        }

        db.collection("registrations").add(reg_data)
        flash("Registration successful!", "success")
        return redirect(url_for("register"))

    return render_template("register.html")


# =========================================================
# 🔑 ADMIN LOGIN / LOGOUT
# =========================================================

@app.route("/admin")
def admin_root():
    return redirect(url_for("admin_login"))


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))

        flash("Invalid credentials", "danger")

    return render_template("login.html")


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin_login"))


# =========================================================
# 📊 ADMIN DASHBOARD
# =========================================================

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    docs = db.collection("registrations").stream()

    regs = []
    for doc in docs:
        d = doc.to_dict()
        d["id"] = doc.id
        regs.append(d)

    total = len(regs)

    webinar_interest_count = sum(
        1 for r in regs if r.get("webinar_interest", "").lower() == "yes"
    )

    blood_donation_count = sum(
        1 for r in regs if r.get("blood_donation", "").lower() == "yes"
    )

    college_counts = set(
        r.get("college_company", "")
        for r in regs if r.get("college_company")
    )

    qual_counts = Counter(
        r.get("qualification", "")
        for r in regs if r.get("qualification")
    ).most_common()

    desig_counts = Counter(
        r.get("designation", "")
        for r in regs if r.get("designation")
    ).most_common()

    gender_counts = Counter(
        r.get("gender", "")
        for r in regs if r.get("gender")
    ).most_common()

    return render_template(
        "admin_dashboard.html",
        total=total,
        webinar_interest_count=webinar_interest_count,
        blood_donation_count=blood_donation_count,
        college_counts=college_counts,
        qual_counts=qual_counts,
        desig_counts=desig_counts,
        gender_counts=gender_counts,
        regs=regs,
        start=None,
        end=None
    )


# =========================================================
# ✏️ ADMIN EDIT
# =========================================================

@app.route("/admin/edit/<doc_id>", methods=["GET", "POST"])
@admin_required
def admin_edit(doc_id):
    ref = db.collection("registrations").document(doc_id)
    snap = ref.get()

    if not snap.exists:
        flash("Record not found", "danger")
        return redirect(url_for("admin_dashboard"))

    reg = snap.to_dict()

    if request.method == "POST":
        ref.update({
            "name": request.form.get("name", "").strip(),
            "whatsapp": request.form.get("whatsapp", "").strip(),
            "email": request.form.get("email", "").strip(),
            "qualification": request.form.get("qualification", "").strip(),
            "designation": request.form.get("designation", "").strip(),
            "gender": request.form.get("gender", "").strip(),
            "college_company": request.form.get("college_company", "").strip(),
            "blood_donation": request.form.get("blood_donation", "").strip(),
            "blood_group": request.form.get("blood_group", "").strip(),
            "webinar_interest": request.form.get("webinar_interest", "").strip(),
            "webinar_date": request.form.get("webinar_date", "").strip()
        })

        flash("Updated successfully", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("admin_edit.html", reg=reg, doc_id=doc_id)


# =========================================================
# 🗑️ ADMIN DELETE (POST ONLY)
# =========================================================

@app.route("/admin/delete/<doc_id>", methods=["POST"])
@admin_required
def admin_delete(doc_id):
    ref = db.collection("registrations").document(doc_id)
    if ref.get().exists:
        ref.delete()
        flash("Deleted successfully", "success")
    else:
        flash("Record not found", "danger")
    return redirect(url_for("admin_dashboard"))


# =========================================================
# 🔑 ADMIN API KEY
# =========================================================

@app.route("/admin/api-key", methods=["GET", "POST"])
@admin_required
def admin_api_key():
    ref = db.collection("admin").document("api_key")
    snap = ref.get()
    api_key = snap.to_dict().get("key") if snap.exists else None

    if request.method == "POST":
        import secrets
        api_key = secrets.token_urlsafe(32)
        ref.set({"key": api_key})
        flash("API key generated", "success")

    return render_template("admin_api_key.html", api_key=api_key)


# =========================================================
# 📥 ADMIN DOWNLOAD (EXCEL)
# =========================================================

@app.route("/admin/download")
@admin_required
def admin_download():
    docs = db.collection("registrations").stream()

    wb = Workbook()
    ws = wb.active
    ws.title = "Registrations"

    headers = [
        "Name", "WhatsApp", "Email", "Qualification", "Designation",
        "Gender", "College/Company", "Blood Donation", "Blood Group",
        "Webinar Interest", "Webinar Date", "Registered At"
    ]
    ws.append(headers)

    for doc in docs:
        r = doc.to_dict()
        ws.append([
            r.get("name", ""),
            r.get("whatsapp", ""),
            r.get("email", ""),
            r.get("qualification", ""),
            r.get("designation", ""),
            r.get("gender", ""),
            r.get("college_company", ""),
            r.get("blood_donation", ""),
            r.get("blood_group", ""),
            r.get("webinar_interest", ""),
            r.get("webinar_date", ""),
            str(r.get("registered_at", ""))
        ])

    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)

    return send_file(
        bio,
        as_attachment=True,
        download_name="registrations.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# =========================================================
# 🌐 API (API KEY PROTECTED)
# =========================================================

@app.route("/api/registrations")
def api_registrations():
    key = request.headers.get("X-API-Key") or request.args.get("api_key")

    ref = db.collection("admin").document("api_key")
    snap = ref.get()
    valid_key = snap.to_dict().get("key") if snap.exists else None

    if not key or key != valid_key:
        return jsonify({"error": "Invalid API key"}), 401

    docs = db.collection("registrations").stream()
    data = []
    for doc in docs:
        d = doc.to_dict()
        d["id"] = doc.id
        data.append(d)

    return jsonify({"count": len(data), "registrations": data})


# =========================================================
# 🚀 MAIN
# =========================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
