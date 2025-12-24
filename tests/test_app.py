import os
import app as app_module


def test_register_get():
    client = app_module.app.test_client()
    rv = client.get('/register')
    assert rv.status_code == 200
    assert b'APJC INFO TECH' in rv.data or b'Registration' in rv.data


def test_register_post_and_admin_dashboard(tmp_path):
    # Use a temporary excel file so tests don't affect real data
    test_file = tmp_path / 'registrations_test.xlsx'
    app_module.EXCEL_FILE = str(test_file)

    client = app_module.app.test_client()

    data = {
        'name': 'Test User',
        'whatsapp': '9999999999',
        'email': 'testuser@example.com',
        'qualification': 'BSc',
        'designation': 'Engineer',
        'gender': 'Male',
        'college': 'Test College'
    }

    rv = client.post('/register', data=data, follow_redirects=True)
    assert b'Registration submitted successfully' in rv.data

    # Login as admin and check dashboard
    rv = client.post('/admin/login', data={'email': app_module.ADMIN_EMAIL, 'password': app_module.ADMIN_PASSWORD}, follow_redirects=True)
    assert rv.status_code == 200
    assert b'Total Registrations' in rv.data or b'Admin Dashboard' in rv.data
