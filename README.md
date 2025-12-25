# Registration App (Flask)

A simple Flask-based registration application using **Firebase Firestore** for data storage.

## Features
- Public registration form (`/register`) — no login required
- Admin login (`/admin/login`)
- Admin dashboard (`/admin/dashboard`)
  - View total registrations
  - View category counts
  - Edit / delete registrations
  - Generate and manage API key
  - Download registrations as Excel

---

## Admin Credentials (Default)

Email: admin@gmail.com  
Password: admin123  

(Change these in production)

---

## Tech Stack
- Python 3.11
- Flask
- Firebase Firestore
- Gunicorn
- Bootstrap

---

## Local Setup

### 1. Create virtual environment
```bash
python -m venv venv
venv\Scripts\activate

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
