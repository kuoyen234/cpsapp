import os
import pandas as pd
import re
from datetime import datetime
from flask import Flask, request, render_template_string, redirect, url_for, session
from functools import wraps
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from supabase import create_client, Client

# === Supabase Config ===
SUPABASE_URL = "https://wmthdsalqsrdiwxbmfey.supabase.co"
SUPABASE_KEY = "YOUR_VALID_SUPABASE_KEY_HERE"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# === Flask App ===
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey123")
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# === Simple user login ===
users = {
    "your@email.com": generate_password_hash("yourpassword"),
}

# === Login Required Decorator ===
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

# === Navbar HTML ===
navbar_html = """
<nav class="navbar navbar-expand-lg navbar-dark bg-dark mb-4">
    <div class="container-fluid">
        <a class="navbar-brand" href="/search-form">🧾 CPSApp</a>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#mainNavbar">
            <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="mainNavbar">
            <ul class="navbar-nav me-auto mb-2 mb-lg-0">
                <li class="nav-item">
                    <a class="nav-link {% if request.path == '/upload-form' %}active{% endif %}" href="/upload-form">📤 Upload</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link {% if request.path == '/search-form' %}active{% endif %}" href="/search-form">🔍 Search & Delete</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link {% if request.path == '/view-packlist' %}active{% endif %}" href="/view-packlist">📦 Pack_List</a>
                </li>
            </ul>
            {% if session.get("user") %}
                <div class="d-flex align-items-center">
                    <span class="navbar-text text-white me-3">👋 {{ session['user'] }}</span>
                    <a href="/logout" class="btn btn-outline-light btn-sm">Logout</a>
                </div>
            {% endif %}
        </div>
    </div>
</nav>
"""

# === Login Route ===
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
        <head><title>Login</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="container py-5">
            <h2 class="mb-4">🔐 Login to CPSApp</h2>
            {% if message %}
                <div class="alert alert-danger">{{ message }}</div>
            {% endif %}
            <form method="post">
                <div class="mb-3"><label>Email</label><input type="email" name="email" class="form-control" required></div>
                <div class="mb-3"><label>Password</label><input type="password" name="password" class="form-control" required></div>
                <button class="btn btn-primary" type="submit">Login</button>
            </form>
        </body>
    </html>
    """, message=message)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

# === Upload Form Route ===
@app.route('/upload-form', methods=['GET', 'POST'])
@login_required
def upload_form():
    message = None
    if request.method == 'POST':
        file = request.files.get('file')
        if file and file.filename:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            message = f"✅ File '{filename}' uploaded successfully!"
        else:
            message = "❌ No file selected."
    return render_template_string("""
    <html>
        <head><title>Upload Product Excel</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="container py-5">
            {{ navbar }}
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
    """, navbar=navbar_html, message=message)

# === Search & Delete Form Route ===
@app.route('/search-form', methods=['GET', 'POST'])
@login_required
def search_form():
    query = request.form.get('query', '')
    results = []
    if request.method == 'POST' and query:
        results = supabase.table("products").select("*").ilike("code", f"%{query}%").execute().data
    return render_template_string("""
    <html>
        <head><title>Search Products</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="container py-5">
            {{ navbar }}
            <h2>🔎 Search Products</h2>
            <form method="post" class="mb-4">
                <div class="input-group">
                    <input type="text" class="form-control" name="query" placeholder="Enter code or description" value="{{ query }}" required>
                    <button class="btn btn-primary" type="submit">Search</button>
                </div>
            </form>
            {% if results %}
                <table class="table table-bordered">
                    <thead><tr>{% for k in results[0].keys() %}<th>{{ k }}</th>{% endfor %}</tr></thead>
                    <tbody>{% for row in results %}
                        <tr>{% for val in row.values() %}<td>{{ val }}</td>{% endfor %}</tr>{% endfor %}
                    </tbody>
                </table>
            {% endif %}
        </body>
    </html>
    """, navbar=navbar_html, query=query, results=results)

# === View Pack_List Route ===
@app.route('/view-packlist', methods=['GET'])
@login_required
def view_packlist():
    packlist_data = supabase.table("packlist").select("*").execute().data
    return render_template_string("""
    <html>
        <head><title>📦 View Pack_List</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="container py-5">
            {{ navbar }}
            <h2>📦 View Pack_List</h2>
            {% if packlist_data %}
                <table class="table table-bordered">
                    <thead><tr>{% for k in packlist_data[0].keys() %}<th>{{ k }}</th>{% endfor %}</tr></thead>
                    <tbody>{% for row in packlist_data %}
                        <tr>{% for val in row.values() %}<td>{{ val }}</td>{% endfor %}</tr>{% endfor %}
                    </tbody>
                </table>
            {% else %}
                <p>No Pack_List data available.</p>
            {% endif %}
        </body>
    </html>
    """, navbar=navbar_html, packlist_data=packlist_data)

# === Default Route ===
@app.route('/')
@login_required
def index():
    return redirect(url_for('search_form'))

# === Run App ===
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)
