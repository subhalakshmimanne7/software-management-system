import os
import sqlite3
from datetime import date

from flask import (Flask, flash, g, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

BASE = os.path.dirname(os.path.abspath(__file__))
# Vercel's filesystem is read-only except /tmp (data there resets on cold start)
DB_PATH = os.path.join('/tmp' if os.environ.get('VERCEL') else BASE, 'sms.db')

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'change-this-secret')


# ----------------------------------------------------------------------------
# Database helpers
# ----------------------------------------------------------------------------
def db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON')
    return g.db


@app.teardown_appcontext
def close_db(_=None):
    conn = g.pop('db', None)
    if conn:
        conn.close()


def q(sql, args=()):
    """SELECT -> list of dicts"""
    return [dict(r) for r in db().execute(sql, args).fetchall()]


def run(sql, args=()):
    """INSERT/UPDATE/DELETE -> last row id"""
    conn = db()
    cur = conn.execute(sql, args)
    conn.commit()
    return cur.lastrowid


def init_db():
    first_time = not os.path.exists(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    if first_time:
        with open(os.path.join(BASE, 'database.sql'), encoding='utf-8') as f:
            conn.executescript(f.read())
        conn.execute('INSERT INTO USERS(Name, Email, Password_Hash) VALUES (?,?,?)',
                     ('Administrator', 'admin@sms.com', generate_password_hash('admin123')))
        conn.commit()
    conn.close()


init_db()


def like(search, cols):
    if not search:
        return '', []
    return ' WHERE ' + ' OR '.join(f'{c} LIKE ?' for c in cols), [f'%{search}%'] * len(cols)


def today():
    return date.today().isoformat()


# ----------------------------------------------------------------------------
# Auth
# ----------------------------------------------------------------------------
@app.before_request
def guard():
    if request.endpoint in (None, 'static', 'login', 'register'):
        return
    if 'user_id' not in session:
        return redirect(url_for('login'))


@app.context_processor
def inject_user():
    return {'logged_user_name': session.get('user_name', ''),
            'logged_user_email': session.get('user_email', '')}


@app.route('/')
def index():
    return redirect(url_for('dashboard'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    email = ''
    if request.method == 'POST':
        email = request.form['email'].strip()
        rows = q('SELECT * FROM USERS WHERE Email = ?', (email,))
        if rows and check_password_hash(rows[0]['Password_Hash'], request.form['password']):
            session['user_id'] = rows[0]['User_ID']
            session['user_name'] = rows[0]['Name']
            session['user_email'] = rows[0]['Email']
            return redirect(url_for('dashboard'))
        flash('Invalid email or password.', 'danger')
    return render_template('login.html', email=email)


@app.route('/register', methods=['GET', 'POST'])
def register():
    name = email = ''
    if request.method == 'POST':
        f = request.form
        name, email = f['name'].strip(), f['email'].strip()
        if len(f['password']) < 6:
            flash('Password must be at least 6 characters.', 'danger')
        elif f['password'] != f['confirm_password']:
            flash('Passwords do not match.', 'danger')
        else:
            try:
                run('INSERT INTO USERS(Name, Email, Password_Hash) VALUES (?,?,?)',
                    (name, email, generate_password_hash(f['password'])))
                flash('Account created. Please log in.', 'success')
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                flash('That email is already registered.', 'danger')
    return render_template('register.html', name=name, email=email)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ----------------------------------------------------------------------------
# Dashboard
# ----------------------------------------------------------------------------
ENTITIES = {
    'users': ('👥', 'Users', 'users', [('User_ID', 'ID'), ('Name', 'Name'), ('Email', 'Email')],
              'SELECT User_ID, Name, Email FROM USERS'),
    'departments': ('🏢', 'Departments', 'departments',
                    [('Department_ID', 'ID'), ('Department_Name', 'Name'), ('Location', 'Location'), ('Contact_Email', 'Email')],
                    'SELECT * FROM DEPARTMENT'),
    'projects': ('📁', 'Projects', 'projects',
                 [('Project_ID', 'ID'), ('Project_Name', 'Project'), ('Department_Name', 'Department'), ('Project_Status', 'Status')],
                 'SELECT p.*, d.Department_Name FROM PROJECT p JOIN DEPARTMENT d ON d.Department_ID = p.Department_ID'),
    'developers': ('👨‍💻', 'Developers', 'developers',
                   [('Developer_ID', 'ID'), ('Developer_Name', 'Name'), ('Email', 'Email')], 'SELECT * FROM DEVELOPER'),
    'software': ('💻', 'Software', 'software',
                 [('Software_ID', 'ID'), ('Software_Name', 'Software'), ('Project_Name', 'Project'), ('Status', 'Status')],
                 'SELECT s.*, p.Project_Name FROM SOFTWARE s JOIN PROJECT p ON p.Project_ID = s.Project_ID'),
    'versions': ('🏷️', 'Versions', 'versions',
                 [('Version_ID', 'ID'), ('Software_Name', 'Software'), ('Version_Number', 'Version'), ('Release_Date', 'Released')],
                 'SELECT v.*, s.Software_Name FROM VERSION v JOIN SOFTWARE s ON s.Software_ID = v.Software_ID'),
    'bugs': ('🐞', 'Bugs', 'bugs',
             [('Bug_ID', 'ID'), ('Software_Name', 'Software'), ('Description', 'Description'), ('Severity', 'Severity'), ('Status', 'Status')],
             'SELECT b.*, s.Software_Name FROM BUG b JOIN SOFTWARE s ON s.Software_ID = b.Software_ID'),
    'maintenance': ('🛠️', 'Maintenance', 'maintenance',
                    [('Maintenance_ID', 'ID'), ('Software_Name', 'Software'), ('Developer_Name', 'Developer'), ('Maintenance_Date', 'Date'), ('Status', 'Status')],
                    'SELECT m.*, s.Software_Name, dv.Developer_Name FROM MAINTENANCE m '
                    'JOIN BUG b ON b.Bug_ID = m.Bug_ID JOIN SOFTWARE s ON s.Software_ID = b.Software_ID '
                    'JOIN DEVELOPER dv ON dv.Developer_ID = m.Performed_By'),
    'licenses': ('📜', 'Licenses', 'licenses',
                 [('License_ID', 'ID'), ('Software_Name', 'Software'), ('License_Type', 'Type'), ('Expiry_Date', 'Expires'), ('License_Status', 'Status')],
                 'SELECT l.*, s.Software_Name FROM LICENSE l JOIN SOFTWARE s ON s.Software_ID = l.Software_ID'),
    'technologies': ('⚙️', 'Technologies', 'technologies',
                     [('Technology_ID', 'ID'), ('Technology_Name', 'Name'), ('Technology_Type', 'Type'), ('Version', 'Version')],
                     'SELECT * FROM TECHNOLOGY'),
}
TABLES = {'users': 'USERS', 'departments': 'DEPARTMENT', 'projects': 'PROJECT', 'developers': 'DEVELOPER',
          'software': 'SOFTWARE', 'versions': 'VERSION', 'bugs': 'BUG', 'maintenance': 'MAINTENANCE',
          'licenses': 'LICENSE', 'technologies': 'TECHNOLOGY'}


@app.route('/dashboard')
def dashboard():
    key = request.args.get('entity', 'overview')
    entity = rows = None
    if key in ENTITIES:
        icon, title, page, cols, sql = ENTITIES[key]
        entity = {'icon': icon, 'title': title, 'page': page, 'cols': cols}
        rows = q(sql)
    else:
        key = 'overview'
    counts = {k: q(f'SELECT COUNT(*) AS c FROM {t}')[0]['c'] for k, t in TABLES.items()}
    return render_template(
        'dashboard.html', selected=key, entity=entity, entity_rows=rows, counts=counts,
        active_projects=q("SELECT p.Project_Name, d.Department_Name, p.Project_Status FROM PROJECT p "
                          "JOIN DEPARTMENT d ON d.Department_ID = p.Department_ID "
                          "WHERE p.Project_Status <> 'Completed' LIMIT 6"),
        open_bugs=q("SELECT s.Software_Name, b.Description, b.Severity, b.Status FROM BUG b "
                    "JOIN SOFTWARE s ON s.Software_ID = b.Software_ID "
                    "WHERE b.Status IN ('Open','In Progress') ORDER BY b.Reported_Date DESC LIMIT 6"),
        expired_licenses=q("SELECT s.Software_Name, l.License_Type, l.Expiry_Date, "
                           "CAST(julianday('now') - julianday(l.Expiry_Date) AS INTEGER) AS Days_Expired "
                           "FROM LICENSE l JOIN SOFTWARE s ON s.Software_ID = l.Software_ID "
                           "WHERE l.Expiry_Date < date('now') LIMIT 6"),
        recent_maintenance=q("SELECT m.Maintenance_Date, dv.Developer_Name, m.Description, m.Status "
                             "FROM MAINTENANCE m JOIN DEVELOPER dv ON dv.Developer_ID = m.Performed_By "
                             "ORDER BY m.Maintenance_Date DESC LIMIT 6"))


# ----------------------------------------------------------------------------
# Generic add / edit / delete routes
#   /<listing>/add   /<listing>/edit/<id>   /<listing>/delete/<id>
# form field name -> column name
# ----------------------------------------------------------------------------
def set_techs(software_id):
    run('DELETE FROM SOFTWARE_TECHNOLOGY WHERE Software_ID = ?', (software_id,))
    for t in request.form.getlist('technologies'):
        run('INSERT OR IGNORE INTO SOFTWARE_TECHNOLOGY(Software_ID, Technology_ID) VALUES (?,?)', (software_id, t))


def make_crud(name, table, pk, listing, fields, after=None):
    cols = list(fields.values())

    def add():
        vals = [request.form.get(k) or None for k in fields]
        try:
            new_id = run(f"INSERT INTO {table}({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", vals)
            if after:
                after(new_id)
            flash(f'{name.title()} added successfully.', 'success')
        except sqlite3.IntegrityError as e:
            flash(f'Database constraint error: {e}', 'danger')
        return redirect(url_for(listing))

    def edit(id):
        vals = [request.form.get(k) or None for k in fields]
        try:
            run(f"UPDATE {table} SET {', '.join(c + ' = ?' for c in cols)} WHERE {pk} = ?", vals + [id])
            if after:
                after(id)
            flash(f'{name.title()} updated successfully.', 'success')
        except sqlite3.IntegrityError as e:
            flash(f'Database constraint error: {e}', 'danger')
        return redirect(url_for(listing))

    def delete(id):
        try:
            run(f'DELETE FROM {table} WHERE {pk} = ?', (id,))
            flash(f'{name.title()} deleted.', 'success')
        except sqlite3.IntegrityError:
            flash(f'Cannot delete this {name}: other records still reference it (foreign key).', 'danger')
        return redirect(url_for(listing))

    app.add_url_rule(f'/{listing}/add', f'add_{name}', add, methods=['POST'])
    app.add_url_rule(f'/{listing}/edit/<int:id>', f'edit_{name}', edit, methods=['POST'])
    app.add_url_rule(f'/{listing}/delete/<int:id>', f'delete_{name}', delete, methods=['POST'])


make_crud('department', 'DEPARTMENT', 'Department_ID', 'departments',
          {'department_name': 'Department_Name', 'description': 'Description',
           'location': 'Location', 'contact_email': 'Contact_Email'})
make_crud('project', 'PROJECT', 'Project_ID', 'projects',
          {'project_name': 'Project_Name', 'department_id': 'Department_ID', 'start_date': 'Start_Date',
           'end_date': 'End_Date', 'project_status': 'Project_Status', 'description': 'Description'})
make_crud('developer', 'DEVELOPER', 'Developer_ID', 'developers',
          {'developer_name': 'Developer_Name', 'email': 'Email'})
make_crud('software', 'SOFTWARE', 'Software_ID', 'software',
          {'software_name': 'Software_Name', 'project_id': 'Project_ID', 'status': 'Status',
           'description': 'Description'}, after=set_techs)
make_crud('version', 'VERSION', 'Version_ID', 'versions',
          {'software_id': 'Software_ID', 'version_number': 'Version_Number', 'release_date': 'Release_Date'})
make_crud('technology', 'TECHNOLOGY', 'Technology_ID', 'technologies',
          {'technology_name': 'Technology_Name', 'technology_type': 'Technology_Type',
           'version': 'Version', 'description': 'Description'})
make_crud('license', 'LICENSE', 'License_ID', 'licenses',
          {'software_id': 'Software_ID', 'license_type': 'License_Type', 'start_date': 'Start_Date',
           'expiry_date': 'Expiry_Date', 'license_status': 'License_Status'})
make_crud('bug', 'BUG', 'Bug_ID', 'bugs',
          {'software_id': 'Software_ID', 'description': 'Description', 'severity': 'Severity',
           'status': 'Status', 'reported_date': 'Reported_Date'})
make_crud('maintenance', 'MAINTENANCE', 'Maintenance_ID', 'maintenance',
          {'bug_id': 'Bug_ID', 'performed_by': 'Performed_By', 'maintenance_date': 'Maintenance_Date',
           'status': 'Status', 'description': 'Description'})


# ----------------------------------------------------------------------------
# List pages
# ----------------------------------------------------------------------------
def search_arg():
    return request.args.get('search', '').strip()


@app.route('/departments')
def departments():
    s = search_arg()
    w, a = like(s, ['Department_Name', 'Location', 'Contact_Email', 'Description'])
    return render_template('departments.html', search=s,
                           departments=q('SELECT * FROM DEPARTMENT' + w + ' ORDER BY Department_ID', a))


@app.route('/projects')
def projects():
    s = search_arg()
    w, a = like(s, ['p.Project_Name', 'p.Project_Status', 'd.Department_Name'])
    return render_template(
        'projects.html', search=s, today_date=today(),
        projects=q('SELECT p.*, d.Department_Name FROM PROJECT p JOIN DEPARTMENT d '
                   'ON d.Department_ID = p.Department_ID' + w + ' ORDER BY p.Project_ID', a),
        departments=q('SELECT * FROM DEPARTMENT ORDER BY Department_Name'))


@app.route('/developers')
def developers():
    s = search_arg()
    w, a = like(s, ['Developer_Name', 'Email'])
    return render_template('developers.html', search=s,
                           developers=q('SELECT * FROM DEVELOPER' + w + ' ORDER BY Developer_ID', a))


@app.route('/software')
def software():
    s = search_arg()
    w, a = like(s, ['s.Software_Name', 's.Status', 'p.Project_Name'])
    rows = q('SELECT s.*, p.Project_Name FROM SOFTWARE s JOIN PROJECT p ON p.Project_ID = s.Project_ID'
             + w + ' ORDER BY s.Software_ID', a)
    for r in rows:
        r['technologies'] = q('SELECT t.* FROM TECHNOLOGY t JOIN SOFTWARE_TECHNOLOGY st '
                              'ON st.Technology_ID = t.Technology_ID WHERE st.Software_ID = ?', (r['Software_ID'],))
    return render_template('software.html', search=s, software=rows,
                           projects=q('SELECT * FROM PROJECT ORDER BY Project_Name'),
                           all_technologies=q('SELECT * FROM TECHNOLOGY ORDER BY Technology_Name'))


@app.route('/software/<int:software_id>/technology', methods=['POST'])
def manage_software_tech(software_id):
    tech = request.form['technology_id']
    if request.form.get('action') == 'remove':
        run('DELETE FROM SOFTWARE_TECHNOLOGY WHERE Software_ID = ? AND Technology_ID = ?', (software_id, tech))
    else:
        run('INSERT OR IGNORE INTO SOFTWARE_TECHNOLOGY(Software_ID, Technology_ID) VALUES (?,?)', (software_id, tech))
    return redirect(url_for('software'))


def software_list():
    return q('SELECT Software_ID, Software_Name FROM SOFTWARE ORDER BY Software_Name')


@app.route('/versions')
def versions():
    s = search_arg()
    w, a = like(s, ['v.Version_Number', 's.Software_Name'])
    return render_template('versions.html', search=s, today_date=today(), software_list=software_list(),
                           versions=q('SELECT v.*, s.Software_Name FROM VERSION v JOIN SOFTWARE s '
                                      'ON s.Software_ID = v.Software_ID' + w + ' ORDER BY v.Release_Date DESC', a))


@app.route('/technologies')
def technologies():
    s = search_arg()
    w, a = like(s, ['Technology_Name', 'Technology_Type', 'Version'])
    return render_template('technologies.html', search=s,
                           technologies=q('SELECT * FROM TECHNOLOGY' + w + ' ORDER BY Technology_ID', a))


@app.route('/licenses')
def licenses():
    s, st = search_arg(), request.args.get('status', '')
    w, a = like(s, ['l.License_Type', 's.Software_Name'])
    if st:
        w += (' AND ' if w else ' WHERE ') + 'l.License_Status = ?'
        a.append(st)
    rows = q("SELECT l.*, s.Software_Name, "
             "CASE WHEN l.Expiry_Date < date('now') THEN 'EXPIRED' ELSE 'VALID' END AS Auto_Status, "
             "CAST(julianday(l.Expiry_Date) - julianday('now') AS INTEGER) AS Days_Remaining "
             "FROM LICENSE l JOIN SOFTWARE s ON s.Software_ID = l.Software_ID" + w + " ORDER BY l.Expiry_Date", a)
    return render_template('licenses.html', search=s, status_filter=st, licenses=rows,
                           today_date=today(), software_list=software_list())


@app.route('/bugs')
def bugs():
    s, sev, st = search_arg(), request.args.get('severity', ''), request.args.get('status', '')
    conds, a = [], []
    if s:
        conds.append('(b.Description LIKE ? OR s.Software_Name LIKE ?)')
        a += [f'%{s}%'] * 2
    if sev:
        conds.append('b.Severity = ?')
        a.append(sev)
    if st:
        conds.append('b.Status = ?')
        a.append(st)
    w = (' WHERE ' + ' AND '.join(conds)) if conds else ''
    return render_template(
        'bugs.html', search=s, severity_filter=sev, status_filter=st, today_date=today(),
        software_list=software_list(),
        bugs=q('SELECT b.*, s.Software_Name FROM BUG b JOIN SOFTWARE s ON s.Software_ID = b.Software_ID'
               + w + ' ORDER BY b.Bug_ID DESC', a))


@app.route('/maintenance')
def maintenance():
    s = search_arg()
    w, a = like(s, ['m.Description', 'dv.Developer_Name', 'm.Status', 'b.Description', 's.Software_Name'])
    rows = q('SELECT m.*, b.Description AS Bug_Description, s.Software_Name, dv.Developer_Name '
             'FROM MAINTENANCE m JOIN BUG b ON b.Bug_ID = m.Bug_ID JOIN SOFTWARE s ON s.Software_ID = b.Software_ID '
             'JOIN DEVELOPER dv ON dv.Developer_ID = m.Performed_By' + w + ' ORDER BY m.Maintenance_Date DESC', a)
    return render_template(
        'maintenance.html', search=s, today_date=today(), maintenance_list=rows,
        bugs=q('SELECT b.Bug_ID, b.Description, b.Severity, s.Software_Name FROM BUG b '
               'JOIN SOFTWARE s ON s.Software_ID = b.Software_ID ORDER BY b.Bug_ID'),
        developers=q('SELECT * FROM DEVELOPER ORDER BY Developer_Name'))


# ----------------------------------------------------------------------------
# Users (passwords are hashed with Werkzeug)
# ----------------------------------------------------------------------------
@app.route('/users')
def users():
    s = search_arg()
    w, a = like(s, ['Name', 'Email'])
    return render_template('users.html', search=s,
                           users=q('SELECT User_ID, Name, Email FROM USERS' + w + ' ORDER BY User_ID', a))


@app.route('/users/add', methods=['POST'])
def add_user():
    f = request.form
    if len(f['password']) < 6:
        flash('Password must be at least 6 characters.', 'danger')
    else:
        try:
            run('INSERT INTO USERS(Name, Email, Password_Hash) VALUES (?,?,?)',
                (f['name'], f['email'], generate_password_hash(f['password'])))
            flash('User added.', 'success')
        except sqlite3.IntegrityError:
            flash('That email is already registered.', 'danger')
    return redirect(url_for('users'))


@app.route('/users/edit/<int:id>', methods=['POST'])
def edit_user(id):
    f = request.form
    try:
        run('UPDATE USERS SET Name = ?, Email = ? WHERE User_ID = ?', (f['name'], f['email'], id))
        if f.get('password'):
            run('UPDATE USERS SET Password_Hash = ? WHERE User_ID = ?', (generate_password_hash(f['password']), id))
        flash('User updated.', 'success')
    except sqlite3.IntegrityError:
        flash('That email is already registered.', 'danger')
    return redirect(url_for('users'))


@app.route('/users/delete/<int:id>', methods=['POST'])
def delete_user(id):
    if id == session.get('user_id'):
        flash('You cannot delete your own account.', 'danger')
    else:
        run('DELETE FROM USERS WHERE User_ID = ?', (id,))
        flash('User deleted.', 'success')
    return redirect(url_for('users'))


# ----------------------------------------------------------------------------
# 15 SQL reports
# ----------------------------------------------------------------------------
REPORTS = [
    ('Software → Project → Department', '3-table INNER JOIN',
     "SELECT s.Software_Name, p.Project_Name, d.Department_Name, s.Status\n"
     "FROM SOFTWARE s\nJOIN PROJECT p ON s.Project_ID = p.Project_ID\n"
     "JOIN DEPARTMENT d ON p.Department_ID = d.Department_ID\nORDER BY d.Department_Name;"),
    ('Bugs per Software', 'LEFT JOIN + GROUP BY + COUNT',
     "SELECT s.Software_Name, COUNT(b.Bug_ID) AS Bug_Count\nFROM SOFTWARE s\n"
     "LEFT JOIN BUG b ON b.Software_ID = s.Software_ID\nGROUP BY s.Software_ID, s.Software_Name\nORDER BY Bug_Count DESC;"),
    ('Unresolved Critical / High Bugs', 'WHERE with IN',
     "SELECT s.Software_Name, b.Description, b.Severity, b.Status\nFROM BUG b\n"
     "JOIN SOFTWARE s ON s.Software_ID = b.Software_ID\n"
     "WHERE b.Severity IN ('Critical','High') AND b.Status IN ('Open','In Progress');"),
    ('License Expiry Evaluation', 'CASE + date comparison',
     "SELECT s.Software_Name, l.License_Type, l.Expiry_Date,\n"
     "  CASE WHEN l.Expiry_Date < date('now') THEN 'EXPIRED' ELSE 'VALID' END AS Expiry_Evaluation\n"
     "FROM LICENSE l JOIN SOFTWARE s ON s.Software_ID = l.Software_ID\nORDER BY l.Expiry_Date;"),
    ('Projects per Department', 'LEFT JOIN + GROUP BY',
     "SELECT d.Department_Name, COUNT(p.Project_ID) AS Total_Projects\nFROM DEPARTMENT d\n"
     "LEFT JOIN PROJECT p ON p.Department_ID = d.Department_ID\nGROUP BY d.Department_ID, d.Department_Name;"),
    ('Technologies per Software', 'M:N join + GROUP_CONCAT',
     "SELECT s.Software_Name, GROUP_CONCAT(t.Technology_Name, ', ') AS Technologies_Used\nFROM SOFTWARE s\n"
     "JOIN SOFTWARE_TECHNOLOGY st ON st.Software_ID = s.Software_ID\n"
     "JOIN TECHNOLOGY t ON t.Technology_ID = st.Technology_ID\nGROUP BY s.Software_ID, s.Software_Name;"),
    ('Developer Workload', 'LEFT JOIN + COUNT',
     "SELECT dv.Developer_Name, COUNT(m.Maintenance_ID) AS Fixes_Done\nFROM DEVELOPER dv\n"
     "LEFT JOIN MAINTENANCE m ON m.Performed_By = dv.Developer_ID\n"
     "GROUP BY dv.Developer_ID, dv.Developer_Name\nORDER BY Fixes_Done DESC;"),
    ('Software with No Bugs', 'NOT EXISTS subquery',
     "SELECT s.Software_Name, s.Status\nFROM SOFTWARE s\n"
     "WHERE NOT EXISTS (SELECT 1 FROM BUG b WHERE b.Software_ID = s.Software_ID);"),
    ('Latest Version of Each Software', 'Correlated subquery + MAX',
     "SELECT s.Software_Name, v.Version_Number, v.Release_Date\nFROM VERSION v\n"
     "JOIN SOFTWARE s ON s.Software_ID = v.Software_ID\n"
     "WHERE v.Release_Date = (SELECT MAX(v2.Release_Date) FROM VERSION v2 WHERE v2.Software_ID = v.Software_ID);"),
    ('Bugs Never Maintained', 'LEFT JOIN ... IS NULL',
     "SELECT b.Bug_ID, s.Software_Name, b.Description, b.Severity\nFROM BUG b\n"
     "JOIN SOFTWARE s ON s.Software_ID = b.Software_ID\n"
     "LEFT JOIN MAINTENANCE m ON m.Bug_ID = b.Bug_ID\nWHERE m.Maintenance_ID IS NULL;"),
    ('Days Taken to Fix Bugs', 'Date arithmetic',
     "SELECT b.Bug_ID, s.Software_Name, b.Reported_Date, m.Maintenance_Date,\n"
     "  CAST(julianday(m.Maintenance_Date) - julianday(b.Reported_Date) AS INTEGER) AS Days_To_Fix\n"
     "FROM MAINTENANCE m\nJOIN BUG b ON b.Bug_ID = m.Bug_ID\nJOIN SOFTWARE s ON s.Software_ID = b.Software_ID\n"
     "WHERE m.Status = 'Completed';"),
    ('Most Used Technologies', 'GROUP BY on junction table',
     "SELECT t.Technology_Name, t.Technology_Type, COUNT(st.Software_ID) AS Used_In\nFROM TECHNOLOGY t\n"
     "LEFT JOIN SOFTWARE_TECHNOLOGY st ON st.Technology_ID = t.Technology_ID\n"
     "GROUP BY t.Technology_ID, t.Technology_Name, t.Technology_Type\nORDER BY Used_In DESC;"),
    ('Overdue Projects', 'Date comparison + julianday',
     "SELECT p.Project_Name, p.End_Date, p.Project_Status,\n"
     "  CAST(julianday('now') - julianday(p.End_Date) AS INTEGER) AS Days_Overdue\nFROM PROJECT p\n"
     "WHERE p.End_Date < date('now') AND p.Project_Status <> 'Completed';"),
    ('Open Bugs per Department', '4-table JOIN + GROUP BY',
     "SELECT d.Department_Name, COUNT(b.Bug_ID) AS Open_Bugs\nFROM DEPARTMENT d\n"
     "JOIN PROJECT p ON p.Department_ID = d.Department_ID\nJOIN SOFTWARE s ON s.Project_ID = p.Project_ID\n"
     "JOIN BUG b ON b.Software_ID = s.Software_ID\nWHERE b.Status IN ('Open','In Progress')\n"
     "GROUP BY d.Department_ID, d.Department_Name;"),
    ('Software with Many Bugs', 'GROUP BY + HAVING (adjustable)',
     "SELECT s.Software_Name, COUNT(b.Bug_ID) AS Bug_Count\nFROM SOFTWARE s\n"
     "JOIN BUG b ON b.Software_ID = s.Software_ID\nGROUP BY s.Software_ID, s.Software_Name\n"
     "HAVING Bug_Count >= ?\nORDER BY Bug_Count DESC;"),
]


@app.route('/reports')
def reports():
    rid = request.args.get('report', '1')
    if not rid.isdigit() or not 1 <= int(rid) <= len(REPORTS):
        rid = '1'
    title, _, sql = REPORTS[int(rid) - 1]
    min_bugs = request.args.get('min_bugs', 1, type=int)
    rows = q(sql, (min_bugs,) if '?' in sql else ())
    return render_template(
        'reports.html', reports=[{'id': str(i + 1), 'title': f'{i + 1}. {r[0]}', 'desc': r[1]}
                                 for i, r in enumerate(REPORTS)],
        active_report=rid, title=title, rows=rows, columns=list(rows[0].keys()) if rows else [],
        sql_query=sql.replace('?', str(min_bugs)), min_bugs=min_bugs)


if __name__ == '__main__':
    app.run(debug=True)
