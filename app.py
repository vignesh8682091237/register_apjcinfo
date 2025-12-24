from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from openpyxl import Workbook, load_workbook
from datetime import datetime, timedelta
import io
import secrets
import jwt

# API key storage file
API_KEY_FILE = os.path.join(os.path.dirname(__file__), '.api_key')
JWT_EXP_MINUTES = 30



from flask_cors import CORS
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET', 'dev-secret-key')
CORS(app)


# PostgreSQL connection config
# Set your actual server details here:
POSTGRES_HOST = 'localhost'         # e.g., 'localhost' or your cloud server address
POSTGRES_DB = 'register_db'        # your database name
POSTGRES_USER = 'postgres'         # your PostgreSQL username
POSTGRES_PASSWORD = 'apjc'     # your PostgreSQL password

def get_pg_connection():
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        return psycopg2.connect(db_url, cursor_factory=RealDictCursor)
    else:
        return psycopg2.connect(
            host=POSTGRES_HOST,
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            cursor_factory=RealDictCursor
        )

# Example usage (uncomment to test connection):
# with get_pg_connection() as conn:
#     with conn.cursor() as cur:
#         cur.execute('SELECT version();')
#         print(cur.fetchone())

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



# Save registration to PostgreSQL
def append_registration_pg(data: dict):
    query = '''
        INSERT INTO registrations
        (name, whatsapp, email, qualification, designation, gender, college_company, blood_donation, blood_group, webinar_interest, webinar_date, registered_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    '''
    registered_at = datetime.now()
    webinar_date = data.get('webinar_date','')
    if not webinar_date:
        webinar_date = None
    values = (
        data.get('name',''), data.get('whatsapp',''), data.get('email',''),
        data.get('qualification',''), data.get('designation',''), data.get('gender',''), data.get('college',''),
        data.get('blood_donation','No'), data.get('blood_group',''), data.get('webinar_interest','No'), webinar_date, registered_at
    )
    with get_pg_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, values)
        conn.commit()



# Fetch registrations from PostgreSQL
def read_registrations():
    query = '''
        SELECT name AS "Name", whatsapp AS "WhatsApp", email AS "Email", qualification AS "Qualification", designation AS "Designation", gender AS "Gender", college_company AS "College/Company", blood_donation AS "Blood Donation", blood_group AS "Blood Group", webinar_interest AS "Webinar Interest", webinar_date AS "Webinar Date", registered_at AS "Registered At"
        FROM registrations
        ORDER BY registered_at DESC
    '''
    with get_pg_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
    return rows


@app.route('/')
def home():
    return redirect(url_for('register'))



@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        if request.is_json:
            req_data = request.get_json()
        else:
            req_data = request.form

        name = req_data.get('name', '').strip()
        whatsapp = req_data.get('whatsapp', '').strip()
        email = req_data.get('email', '').strip()
        qualification = req_data.get('qualification', '').strip()
        designation = req_data.get('designation', '').strip()
        gender = req_data.get('gender', '').strip()
        college = req_data.get('college', '').strip()

        missing = []
        for field, label in [(name, 'Name'), (whatsapp, 'WhatsApp'), (email, 'Email'), (qualification, 'Qualification'), (designation, 'Designation'), (gender, 'Gender'), (college, 'College/Company')]:
            if not field:
                missing.append(label)

        if missing:
            if request.is_json:
                return jsonify({'error': 'Please fill all required fields: ' + ', '.join(missing)}), 400
            flash('Please fill all required fields: ' + ', '.join(missing), 'danger')
            return render_template('register.html', form=req_data)

        blood_donation = req_data.get('blood_donation', 'No')
        blood_group = req_data.get('blood_group', '').strip()
        webinar_interest = req_data.get('webinar_interest', 'No')
        webinar_date = req_data.get('webinar_date', '').strip()

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
            if request.is_json:
                return jsonify({'error': 'Please select your blood group'}), 400
            flash('Please select your blood group', 'danger')
            return render_template('register.html', form=req_data)

        append_registration_pg(data)
        if request.is_json:
            return jsonify({'message': 'Registration submitted successfully.'}), 201
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

    # Build SQL query with optional date filtering
    base_query = '''
        SELECT name AS "Name", whatsapp AS "WhatsApp", email AS "Email", qualification AS "Qualification", designation AS "Designation", gender AS "Gender", college_company AS "College/Company", blood_donation AS "Blood Donation", blood_group AS "Blood Group", webinar_interest AS "Webinar Interest", webinar_date AS "Webinar Date", registered_at AS "Registered At"
        FROM registrations
    '''
    filters = []
    params = []
    if start:
        filters.append('registered_at >= %s')
        params.append(f"{start} 00:00:00")
    if end:
        filters.append('registered_at <= %s')
        params.append(f"{end} 23:59:59")
    if filters:
        base_query += ' WHERE ' + ' AND '.join(filters)
    base_query += ' ORDER BY registered_at DESC'

    with get_pg_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(base_query, params)
            regs = cur.fetchall()

    # write filtered to an in-memory workbook
    wb = Workbook()
    ws = wb.active
    ws.title = 'Registrations'
    ws.append(HEADERS)
    for r in regs:
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

    # optional date range
    start = request.args.get('start')
    end = request.args.get('end')

    base_query = '''
        SELECT name AS "Name", whatsapp AS "WhatsApp", email AS "Email", qualification AS "Qualification", designation AS "Designation", gender AS "Gender", college_company AS "College/Company", blood_donation AS "Blood Donation", blood_group AS "Blood Group", webinar_interest AS "Webinar Interest", webinar_date AS "Webinar Date", registered_at AS "Registered At"
        FROM registrations
    '''
    filters = []
    params = []
    if start:
        filters.append('registered_at >= %s')
        params.append(f"{start} 00:00:00")
    if end:
        filters.append('registered_at <= %s')
        params.append(f"{end} 23:59:59")
    if filters:
        base_query += ' WHERE ' + ' AND '.join(filters)
    base_query += ' ORDER BY registered_at DESC'

    with get_pg_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(base_query, params)
            regs = cur.fetchall()

    return {'count': len(regs), 'registrations': regs}


def ensure_database_exists():
    """
    Ensure the PostgreSQL database exists. If not, create it using the default 'postgres' database.
    """
    import psycopg2
    try:
        # Try connecting to the target database
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD
        )
        conn.close()
    except psycopg2.OperationalError as e:
        if f'database "{POSTGRES_DB}" does not exist' in str(e):
            # Connect to default 'postgres' database and create the target database
            conn = psycopg2.connect(
                host=POSTGRES_HOST,
                dbname='postgres',
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD
            )
            conn.autocommit = True  # Set autocommit before creating cursor
            with conn.cursor() as cur:
                cur.execute(f'CREATE DATABASE {POSTGRES_DB};')
            conn.close()
            print(f"Database '{POSTGRES_DB}' created.")
        else:
            raise

def ensure_registrations_table_exists():
    """
    Ensure the 'registrations' table exists in the database. Create it if missing.
    """
    create_table_sql = '''
    CREATE TABLE IF NOT EXISTS registrations (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100),
        whatsapp VARCHAR(20),
        email VARCHAR(100),
        qualification VARCHAR(100),
        designation VARCHAR(100),
        gender VARCHAR(20),
        college_company VARCHAR(200),
        blood_donation VARCHAR(10),
        blood_group VARCHAR(10),
        webinar_interest VARCHAR(10),
        webinar_date DATE,
        registered_at TIMESTAMP
    );
    '''
    with get_pg_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(create_table_sql)
        conn.commit()

# Ensure DB and table exist at startup
ensure_database_exists()
ensure_registrations_table_exists()

if __name__ == '__main__':
    app.run(debug=True)


