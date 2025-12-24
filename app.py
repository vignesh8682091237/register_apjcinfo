from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
import os
from openpyxl import Workbook, load_workbook
from datetime import datetime, timedelta
import io
import secrets
import jwt

# API key storage file
API_KEY_FILE = os.path.join(os.path.dirname(__file__), '.api_key')
JWT_EXP_MINUTES = 30

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET', 'dev-secret-key')

EXCEL_FILE = os.path.join(os.path.dirname(__file__), 'registrations.xlsx')
ADMIN_EMAIL = 'admin@gmail.com'
ADMIN_PASSWORD = 'Aniruth8682@'

HEADERS = ['Name', 'WhatsApp', 'Email', 'Qualification', 'Designation', 'Gender', 'College/Company', 'Blood Donation', 'Blood Group', 'Webinar Interest', 'Webinar Date', 'Registered At']


def ensure_workbook():
    if not os.path.exists(EXCEL_FILE):
        wb = Workbook()
        ws = wb.active
        ws.title = 'Registrations'
        ws.append(HEADERS)
        wb.save(EXCEL_FILE)
    else:
        # ensure header row matches HEADERS; remove accidental duplicate header rows
        wb = load_workbook(EXCEL_FILE)
        ws = wb.active
        # normalize first row to HEADERS if mismatch
        first_row = [ws.cell(row=1, column=i).value for i in range(1, len(HEADERS) + 1)]
        if first_row != HEADERS:
            for i, h in enumerate(HEADERS, start=1):
                ws.cell(row=1, column=i).value = h

        # remove any duplicate header rows that may exist below row 1
        for r in range(ws.max_row, 1, -1):
            vals = [ws.cell(row=r, column=c).value for c in range(1, len(HEADERS) + 1)]
            if vals == HEADERS:
                ws.delete_rows(r)

        wb.save(EXCEL_FILE)


def append_registration(data: dict):
    ensure_workbook()
    wb = load_workbook(EXCEL_FILE)
    ws = wb.active
    # include registration timestamp
    registered_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    row = [
        data.get('name',''), data.get('whatsapp',''), data.get('email',''),
        data.get('qualification',''), data.get('designation',''), data.get('gender',''), data.get('college',''),
        data.get('blood_donation','No'), data.get('blood_group',''), data.get('webinar_interest','No'), data.get('webinar_date',''), registered_at
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


def get_api_key():
    try:
        if os.path.exists(API_KEY_FILE):
            with open(API_KEY_FILE, 'r', encoding='utf-8') as f:
                return f.read().strip()
    except Exception:
        return None
    return None


def set_api_key(key: str):
    with open(API_KEY_FILE, 'w', encoding='utf-8') as f:
        f.write(key)
    return key


@app.route('/admin/api_key', methods=['GET', 'POST'])
@admin_required
def admin_api_key():
    # show current key; POST regenerates
    current = get_api_key()
    if request.method == 'POST':
        new = secrets.token_urlsafe(32)
        set_api_key(new)
        flash('API key generated', 'success')
        current = new
    return render_template('admin_api_key.html', api_key=current)


@app.route('/auth/token', methods=['POST'])
def auth_token():
    # Accept JSON body with either api_key or admin credentials
    data = request.get_json() or {}
    provided_key = data.get('api_key') or request.form.get('api_key')
    email = data.get('email') or request.form.get('email')
    password = data.get('password') or request.form.get('password')

    # verify via api_key first
    real = get_api_key()
    if provided_key and real and provided_key == real:
        sub = 'api_key_client'
    elif email and password and email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
        sub = 'admin_user'
    else:
        return ({'error': 'invalid_credentials'}, 401)

    payload = {
        'sub': sub,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(minutes=JWT_EXP_MINUTES)
    }
    token = jwt.encode(payload, app.secret_key, algorithm='HS256')
    return {'token': token, 'expires_in': JWT_EXP_MINUTES}


def verify_token(token):
    try:
        payload = jwt.decode(token, app.secret_key, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except Exception:
        return None


@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    regs = read_registrations()

    # optional date range filter from query params (YYYY-MM-DD)
    start = request.args.get('start')
    end = request.args.get('end')

    def parse_registered_at(r):
        v = r.get('Registered At') or ''
        try:
            return datetime.strptime(v, '%Y-%m-%d %H:%M:%S')
        except Exception:
            return None

    if start or end:
        try:
            start_dt = datetime.strptime(start, '%Y-%m-%d') if start else None
        except Exception:
            start_dt = None
        try:
            end_dt = datetime.strptime(end, '%Y-%m-%d') if end else None
            # include whole day for end
            if end_dt:
                end_dt = end_dt.replace(hour=23, minute=59, second=59)
        except Exception:
            end_dt = None

        def in_range(rdt):
            if not rdt:
                return False
            if start_dt and rdt < start_dt:
                return False
            if end_dt and rdt > end_dt:
                return False
            return True

        regs = [r for r in regs if in_range(parse_registered_at(r))]

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

    # compute some quick counts for dashboard cards
    webinar_interest_count = sum(1 for r in regs if (r.get('Webinar Interest') or '').strip().lower() == 'yes')
    blood_donation_count = sum(1 for r in regs if (r.get('Blood Donation') or '').strip().lower() == 'yes')

    return render_template('admin_dashboard.html', total=total, regs=regs, qual_counts=qual_counts, desig_counts=desig_counts, gender_counts=gender_counts, college_counts=college_counts, webinar_interest_count=webinar_interest_count, blood_donation_count=blood_donation_count, start=start, end=end)


@app.route('/admin/download')
@admin_required
def admin_download():
    # support optional date range query params to download filtered data
    start = request.args.get('start')
    end = request.args.get('end')
    ensure_workbook()
    if not start and not end:
        return send_file(EXCEL_FILE, as_attachment=True, download_name='registrations.xlsx')

    # load all registrations and filter by Registered At
    regs = read_registrations()

    def parse_registered_at_val(v):
        try:
            return datetime.strptime(v, '%Y-%m-%d %H:%M:%S')
        except Exception:
            return None

    try:
        start_dt = datetime.strptime(start, '%Y-%m-%d') if start else None
    except Exception:
        start_dt = None
    try:
        end_dt = datetime.strptime(end, '%Y-%m-%d') if end else None
        if end_dt:
            end_dt = end_dt.replace(hour=23, minute=59, second=59)
    except Exception:
        end_dt = None

    def in_range(r):
        rdt = parse_registered_at_val(r.get('Registered At') or '')
        if not rdt:
            return False
        if start_dt and rdt < start_dt:
            return False
        if end_dt and rdt > end_dt:
            return False
        return True

    filtered = [r for r in regs if in_range(r)]

    # write filtered to an in-memory workbook
    wb = Workbook()
    ws = wb.active
    ws.title = 'Registrations'
    ws.append(HEADERS)
    for r in filtered:
        row = [r.get(h, '') for h in HEADERS]
        ws.append(row)

    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    fname = 'registrations'
    if start: fname += f'_{start}'
    if end: fname += f'_to_{end}'
    fname += '.xlsx'
    return send_file(bio, as_attachment=True, download_name=fname, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@app.route('/api/registrations')
def api_registrations():
    # API key via header 'X-API-Key' or query param 'api_key' OR Bearer token
    auth_header = request.headers.get('Authorization', '')
    provided_key = request.headers.get('X-API-Key') or request.args.get('api_key')
    real = get_api_key()

    # check Bearer token first
    if auth_header and auth_header.lower().startswith('bearer '):
        token = auth_header.split(None, 1)[1]
        payload = verify_token(token)
        if not payload:
            return ({'error': 'unauthorized'}, 401)
        # token valid; proceed
    else:
        # fallback to api key
        if not real or not provided_key or provided_key != real:
            return ({'error': 'unauthorized'}, 401)

    regs = read_registrations()

    # optional date range
    start = request.args.get('start')
    end = request.args.get('end')

    def parse_registered_at_val(v):
        try:
            return datetime.strptime(v, '%Y-%m-%d %H:%M:%S')
        except Exception:
            return None

    try:
        start_dt = datetime.strptime(start, '%Y-%m-%d') if start else None
    except Exception:
        start_dt = None
    try:
        end_dt = datetime.strptime(end, '%Y-%m-%d') if end else None
        if end_dt:
            end_dt = end_dt.replace(hour=23, minute=59, second=59)
    except Exception:
        end_dt = None

    def in_range(r):
        rdt = parse_registered_at_val(r.get('Registered At') or '')
        if not rdt:
            return False
        if start_dt and rdt < start_dt:
            return False
        if end_dt and rdt > end_dt:
            return False
        return True

    if start_dt or end_dt:
        regs = [r for r in regs if in_range(r)]

    return {'count': len(regs), 'registrations': regs}


if __name__ == '__main__':
    app.run(debug=True)
