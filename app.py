from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
import os
from openpyxl import Workbook, load_workbook

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET', 'dev-secret-key')

EXCEL_FILE = os.path.join(os.path.dirname(__file__), 'registrations.xlsx')
ADMIN_EMAIL = 'admin@gmail.com'
ADMIN_PASSWORD = 'Aniruth8682@'

HEADERS = ['Name', 'WhatsApp', 'Email', 'Qualification', 'Designation', 'Gender', 'College/Company', 'Blood Donation', 'Blood Group', 'Webinar Interest', 'Webinar Date']


def ensure_workbook():
    if not os.path.exists(EXCEL_FILE):
        wb = Workbook()
        ws = wb.active
        ws.title = 'Registrations'
        ws.append(HEADERS)
        wb.save(EXCEL_FILE)


def append_registration(data: dict):
    ensure_workbook()
    wb = load_workbook(EXCEL_FILE)
    ws = wb.active
    row = [
        data.get('name',''), data.get('whatsapp',''), data.get('email',''),
        data.get('qualification',''), data.get('designation',''), data.get('gender',''), data.get('college',''),
        data.get('blood_donation','No'), data.get('blood_group',''), data.get('webinar_interest','No'), data.get('webinar_date','')
    ]
    ws.append(row)
    wb.save(EXCEL_FILE)


def read_registrations():
    ensure_workbook()
    wb = load_workbook(EXCEL_FILE)
    ws = wb.active
    rows = list(ws.values)
    if not rows:
        return []
    headers = rows[0]
    data = [dict(zip(headers, r)) for r in rows[1:]]
    return data


@app.route('/')
def home():
    return redirect(url_for('register'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        whatsapp = request.form.get('whatsapp', '').strip()
        email = request.form.get('email', '').strip()
        qualification = request.form.get('qualification', '').strip()
        designation = request.form.get('designation', '').strip()
        gender = request.form.get('gender', '').strip()
        college = request.form.get('college', '').strip()

        missing = []
        for field, label in [(name, 'Name'), (whatsapp, 'WhatsApp'), (email, 'Email'), (qualification, 'Qualification'), (designation, 'Designation'), (gender, 'Gender'), (college, 'College/Company')]:
            if not field:
                missing.append(label)

        if missing:
            flash('Please fill all required fields: ' + ', '.join(missing), 'danger')
            return render_template('register.html', form=request.form)

        blood_donation = request.form.get('blood_donation', 'No')
        blood_group = request.form.get('blood_group', '').strip()
        webinar_interest = request.form.get('webinar_interest', 'No')
        webinar_date = request.form.get('webinar_date', '').strip()

        data = {
            'name': name,
            'whatsapp': whatsapp,
            'email': email,
            'qualification': qualification,
            'designation': designation,
            'gender': gender,
            'college': college,
            'blood_donation': blood_donation,
            'blood_group': blood_group,
            'webinar_interest': webinar_interest,
            'webinar_date': webinar_date,
        }
        # conditional validation
        if blood_donation == 'Yes' and not blood_group:
            flash('Please select your blood group', 'danger')
            return render_template('register.html', form=request.form)
        if webinar_interest == 'Yes' and not webinar_date:
            flash('Please pick a preferred webinar date', 'danger')
            return render_template('register.html', form=request.form)

        append_registration(data)
        flash('Registration submitted successfully.', 'success')
        return redirect(url_for('register'))

    return render_template('register.html')


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid admin credentials', 'danger')
            return render_template('login.html')
    return render_template('login.html')


def admin_required(fn):
    from functools import wraps

    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return fn(*args, **kwargs)

    return wrapper


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))


@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    regs = read_registrations()
    total = len(regs)

    def counts_for(key):
        d = {}
        for r in regs:
            val = r.get(key) or 'Unknown'
            d[val] = d.get(val, 0) + 1
        return sorted(d.items(), key=lambda x: x[1], reverse=True)

    qual_counts = counts_for('Qualification')
    desig_counts = counts_for('Designation')
    gender_counts = counts_for('Gender')
    college_counts = counts_for('College/Company')

    return render_template('admin_dashboard.html', total=total, regs=regs, qual_counts=qual_counts, desig_counts=desig_counts, gender_counts=gender_counts, college_counts=college_counts)


@app.route('/admin/download')
@admin_required
def admin_download():
    ensure_workbook()
    return send_file(EXCEL_FILE, as_attachment=True, download_name='registrations.xlsx')


if __name__ == '__main__':
    app.run(debug=True)
