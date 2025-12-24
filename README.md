# Registration App (Flask)

Simple Flask application with:
- Public registration form (`/register`) — no login required.
- Admin login (`/admin/login`) with default credentials: `admin@gmail.com` / `Aniruth8682@`.
- Admin dashboard (`/admin/dashboard`) showing total registrations and category counts, plus download Excel option.

Setup
1. Create a virtualenv and activate it.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

Run

```bash
set FLASK_APP=app.py
set FLASK_ENV=development
flask run
```

Or run directly:

```bash
python app.py
```

Data storage
- Registrations are stored in `registrations.xlsx` in the project root (created automatically).
