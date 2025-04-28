import os
import pandas as pd
import difflib
import re
from supabase import create_client, Client
from werkzeug.utils import secure_filename
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, redirect, url_for, session
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps

# === Supabase Config ===
SUPABASE_URL = "https://wmthdsalqsrdiwxbmfey.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndtdGhkc2FscXNyZGl3eGJtZmV5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQyNjE2NTEsImV4cCI6MjA1OTgzNzY1MX0.3_3iBmNy9VM5BRycEKLvTfBBCRQkjJF7kP0EN-VZH68"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# === Flask App Config ===
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey123")
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# === User Authentication ===
users = {
    "ailianyvette@gmail.com": generate_password_hash("jojo16022001"),
    "kuoyen23@yahoo.com": generate_password_hash("jojo16022001")
}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    message = None
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if email in users and check_password_hash(users[email], password):
            session['user'] = email
            return redirect(url_for('search_form'))
        else:
            message = "❌ Invalid credentials."

    return render_template_string("""
    <html>
        <head>
            <title>Login</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="container py-5">
            <h2 class="mb-4">🔐 Login to CPSApp</h2>
            {% if message %}
                <div class="alert alert-danger">{{ message }}</div>
            {% endif %}
            <form method="post">
                <div class="mb-3">
                    <label>Email</label>
                    <input type="email" name="email" class="form-control" required>
                </div>
                <div class="mb-3">
                    <label>Password</label>
                    <input type="password" name="password" class="form-control" required>
                </div>
                <button class="btn btn-primary" type="submit">Login</button>
            </form>
        </body>
    </html>
    """, message=message)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

# === Index Redirect to Search ===
@app.route('/')
@login_required
def index():
    return redirect(url_for('search_form'))

# === Upload Form ===
@app.route('/upload-form', methods=['GET', 'POST'])
@login_required
def upload_form():
    message = None
    if request.method == 'POST':
        if 'file' not in request.files or request.files['file'].filename == '':
            message = "No file selected."
        else:
            file = request.files['file']
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            try:
                # Handle Master, Pack_List, Bill (simplified for brevity)
                df = pd.read_excel(filepath, sheet_name='Master')
                for _, row in df.iterrows():
                    code_raw = str(row['Code'])
                    code = code_raw.replace("Code:", "").strip()
                    data = {
                        "design_number": int(row['Design Number']),
                        "description": row['Description'],
                        "price": float(row['Price']),
                        "color": row['Color'],
                        "code": code,
                        "upload_date": datetime.utcnow().isoformat(),
                        "source_file": filename
                    }
                    supabase.table("products").insert(data).execute()

                message = "✅ Upload successful!"
            except Exception as e:
                message = f"❌ Upload failed: {str(e)}"

    return render_template_string("""
    <html>
        <head><title>Upload Product Excel</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"></head>
        <body class="container py-5">
            <h2>📤 Upload Product Excel File</h2>
            {% if message %}
                <div class="alert alert-info">{{ message }}</div>
            {% endif %}
            <form method="post" enctype="multipart/form-data">
                <div class="mb-3"><input class="form-control" type="file" name="file" required></div>
                <button class="btn btn-primary" type="submit">Upload File</button>
            </form>
        </body>
    </html>
    """, message=message)

# === Search & Delete ===
@app.route('/search-form', methods=['GET', 'POST'])
@login_required
def search_form():
    query = ""
    results = []
    message = request.args.get('msg')

    if request.method == 'POST':
        query = request.form.get('query', '')
        if query:
            products = supabase.table('products').select("*").ilike('code', f'%{query}%').execute().data
            results.extend(products)

    return render_template_string("""
    <html>
    <head><title>Search</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="container py-5">
        <h2>🔍 Search & Delete</h2>
        <form method="post" class="mb-4">
            <div class="input-group">
                <input type="text" class="form-control" name="query" placeholder="Enter code or description" value="{{ query }}" required>
                <button class="btn btn-primary" type="submit">Search</button>
            </div>
        </form>
        {% if results %}
            <table class="table table-bordered">
                <thead>
                    <tr><th>Code</th><th>Description</th><th>Price</th><th>Action</th></tr>
                </thead>
                <tbody>
                    {% for row in results %}
                        <tr>
                            <td>{{ row.code }}</td>
                            <td>{{ row.description }}</td>
                            <td>{{ row.price }}</td>
                            <td>
                                <form method="post" action="/delete/{{ row.id }}" onsubmit="return confirm('Delete this row?');">
                                    <button class="btn btn-sm btn-danger">Delete</button>
                                </form>
                            </td>
                        </tr>
                    {% endfor %}
                </tbody>
            </table>
        {% elif query %}
            <div class="alert alert-warning">No results found.</div>
        {% endif %}
    </body>
    </html>
    """, query=query, results=results, message=message)

# === View Pack_List ===
@app.route('/view-packlist', methods=['GET', 'POST'])
@login_required
def view_packlist():
    selected_file = None
    packlist_df = None
    error = None

    file_rows = supabase.table("packlist").select("source_file").execute().data
    unique_files = sorted({r["source_file"] for r in file_rows if r.get("source_file")}, reverse=True)

    if request.method == 'POST':
        selected_file = request.form.get('selected_file')
        try:
            rows = supabase.table("packlist").select("row_data").eq("source_file", selected_file).order("row_index").execute().data
            if rows:
                packlist_df = pd.DataFrame([row['row_data'] for row in rows])
            else:
                error = f"❌ No Pack_List data found for file: {selected_file}"
        except Exception as e:
            error = f"❌ Error loading Pack_List from Supabase: {str(e)}"

    return render_template_string("""
    <html>
        <head><title>📦 View Pack_List</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"></head>
        <body class="container py-5">
            <h2>📦 View Pack_List Sheet</h2>
            <form method="post" class="mb-4">
                <div class="input-group">
                    <select name="selected_file" class="form-select" required>
                        <option value="">-- Select uploaded file --</option>
                        {% for file in unique_files %}
                            <option value="{{ file }}" {% if file == selected_file %}selected{% endif %}>{{ file }}</option>
                        {% endfor %}
                    </select>
                    <button class="btn btn-primary" type="submit">View Pack_List</button>
                </div>
            </form>
            {% if error %}
                <div class="alert alert-danger">{{ error }}</div>
            {% endif %}
            {% if packlist_df is not none %}
                <div class="table-responsive">
                    <table class="table table-bordered table-striped">
                        <thead class="table-light">
                            <tr>
                                {% for col in packlist_df.columns %}
                                    <th>{{ col }}</th>
                                {% endfor %}
                            </tr>
                        </thead>
                        <tbody>
                            {% for _, row in packlist_df.iterrows() %}
                                <tr>
                                    {% for cell in row %}
                                        <td>{{ cell }}</td>
                                    {% endfor %}
                                </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            {% endif %}
        </body>
    </html>
    """, unique_files=unique_files, selected_file=selected_file, packlist_df=packlist_df, error=error)

# === Run App ===
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5002))
    app.run(host='0.0.0.0', port=port)
