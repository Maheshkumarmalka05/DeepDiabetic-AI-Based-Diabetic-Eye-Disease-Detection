from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os
import uuid
from datetime import datetime
import random
import json

app = Flask(__name__)
app.secret_key = "super_secret_key"

DATABASE = 'deepdiabetic.db'

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'}

# ---------------- FILE CHECK ----------------
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# ---------------- DATABASE ----------------
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()

    conn.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        created_at TEXT
    )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS images_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        original_filename TEXT,
        stored_filename TEXT,
        filepath TEXT,
        uploaded_by TEXT,
        upload_date TEXT,
        analysis_status TEXT
    )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS analysis_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        image_id INTEGER,
        analysis_date TEXT,
        performed_by TEXT,
        dr_severity TEXT,
        dr_confidence REAL,
        dme_status TEXT,
        dme_confidence REAL,
        other_conditions TEXT,
        processing_time_ms INTEGER,
        explainability_info TEXT,
        model_used TEXT
    )''')

    conn.commit()
    conn.close()

init_db()

# ---------------- LOGIN REQUIRED ----------------
def login_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'username' not in session:
            flash("Login required!", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper

# ---------------- MOCK AI ----------------
def mock_analysis():
    return {
        "dr_severity": random.choice(['No DR', 'Mild', 'Moderate', 'Severe']),
        "dr_confidence": round(random.uniform(0.8, 0.99), 2),
        "dme_status": random.choice(['Detected', 'Not Detected']),
        "dme_confidence": round(random.uniform(0.7, 0.95), 2),
        "other_conditions": json.dumps([{"name": "Glaucoma", "detected": True}]),
        "processing_time_ms": random.randint(500, 2000),
        "explainability_info": "Heatmap generated",
        "model_used": "Mock Model"
    }

# ---------------- ROUTES ----------------
@app.route('/')
def index():
    return render_template('index.html', username=session.get('username'))

# REGISTER
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])

        conn = get_db_connection()
        exists = conn.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()

        if exists:
            flash("User already exists!", "danger")
            return redirect(url_for('register'))

        conn.execute('INSERT INTO users (username,password,created_at) VALUES (?,?,?)',
                     (username, password, datetime.now().isoformat()))
        conn.commit()
        conn.close()

        flash("Registered successfully!", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

# LOGIN
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['username'] = username
            return redirect(url_for('index'))

        flash("Invalid login!", "danger")

    return render_template('login.html')

# LOGOUT
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# UPLOAD IMAGE
@app.route('/upload_image', methods=['GET','POST'])
@login_required
def upload_image():
    if request.method == 'POST':

        file = request.files.get('fundus_image')

        if not file or file.filename == '':
            flash("No file selected!", "danger")
            return redirect(request.url)

        if not allowed_file(file.filename):
            flash("Invalid file type!", "danger")
            return redirect(request.url)

        filename = str(uuid.uuid4()) + os.path.splitext(file.filename)[1]
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(path)

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''INSERT INTO images_data 
        (original_filename,stored_filename,filepath,uploaded_by,upload_date,analysis_status)
        VALUES (?,?,?,?,?,?)''',
        (file.filename, filename, path, session['username'], datetime.now().isoformat(), "Done"))

        image_id = cursor.lastrowid

        analysis = mock_analysis()

        cursor.execute('''INSERT INTO analysis_results 
        (image_id,analysis_date,performed_by,dr_severity,dr_confidence,dme_status,dme_confidence,
        other_conditions,processing_time_ms,explainability_info,model_used)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
        (image_id, datetime.now().isoformat(), session['username'],
         analysis['dr_severity'], analysis['dr_confidence'],
         analysis['dme_status'], analysis['dme_confidence'],
         analysis['other_conditions'], analysis['processing_time_ms'],
         analysis['explainability_info'], analysis['model_used']))

        conn.commit()
        conn.close()

        return redirect(url_for('show_results', image_id=image_id))

    return render_template('upload_image.html')

# RESULTS
@app.route('/results/<int:image_id>')
@login_required
def show_results(image_id):
    conn = get_db_connection()

    image = conn.execute('SELECT * FROM images_data WHERE id=?', (image_id,)).fetchone()
    result = conn.execute('SELECT * FROM analysis_results WHERE image_id=?', (image_id,)).fetchone()

    conn.close()

    if not image or not result:
        flash("Data not found!", "danger")
        return redirect(url_for('history'))

    result = dict(result)
    result['other_conditions'] = json.loads(result['other_conditions'])

    return render_template('results.html', image=image, results=result)

# ✅ HISTORY ROUTE (IMPORTANT FIX)
@app.route('/history')
@login_required
def history():
    conn = get_db_connection()
    uploads = conn.execute(
        'SELECT * FROM images_data WHERE uploaded_by=? ORDER BY id DESC',
        (session['username'],)
    ).fetchall()
    conn.close()

    return render_template('history.html', uploads=uploads)

# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(debug=True)