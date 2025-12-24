import re
import app as app_module

client = app_module.app.test_client()
# perform admin login
rv = client.post('/admin/login', data={'email': app_module.ADMIN_EMAIL, 'password': app_module.ADMIN_PASSWORD}, follow_redirects=True)
rv = client.get('/admin/dashboard')
html = rv.get_data(as_text=True)

m_qual = re.search(r"const qual = (.*?);\n", html)
m_desig = re.search(r"const desig = (.*?);\n", html)
m_gender = re.search(r"const gender = (.*?);\n", html)
print('STATUS:', rv.status_code)
print('\n--- qual JSON ---')
print(m_qual.group(1) if m_qual else 'NOT FOUND')
print('\n--- desig JSON ---')
print(m_desig.group(1) if m_desig else 'NOT FOUND')
print('\n--- gender JSON ---')
print(m_gender.group(1) if m_gender else 'NOT FOUND')

# show a short snippet around the charts
idx = html.find('new Chart(document.getElementById(\'qualChart\')')
print('\n--- chart snippet ---')
print(html[idx:idx+400])
