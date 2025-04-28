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
from openpyxl import load_workbook

# === Supabase Config ===
SUPABASE_URL = "https://wmthdsalqsrdiwxbmfey.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndtdGhkc2FscXNyZGl3eGJtZmV5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQyNjE2NTEsImV4cCI6MjA1OTgzNzY1MX0.3_3iBmNy9VM5BRycEKLvTfBBCRQkjJF7kP0EN-VZH68"  # Replace with your valid Supabase key
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

users = {
    "ailianyvette@gmail.com": generate_password_hash("jojo16022001"),
    "kuoyen23@yahoo.com": generate_password_hash("jojo16022001")
}

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey123")
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# === Authentication Decorator ===
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

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
        <h2>🔐 Login to CPSApp</h2>
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

# === Index Redirect to Search Form ===
@app.route('/')
@login_required
def index():
    return redirect(url_for('search_form'))

# === Search Form Route (Fix Ensured) ===
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
        <h2>🔍 Search Products</h2>
        <form method="post" class="mb-4">
            <div class="input-group">
                <input type="text" class="form-control" name="query" placeholder="Enter code or description" value="{{ query }}" required>
                <button class="btn btn-primary" type="submit">Search</button>
            </div>
        </form>
        {% if results %}
            <table class="table table-bordered">
                <thead>
                    <tr><th>Code</th><th>Description</th><th>Price</th></tr>
                </thead>
                <tbody>
                    {% for row in results %}
                        <tr><td>{{ row.code }}</td><td>{{ row.description }}</td><td>{{ row.price }}</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        {% elif query %}
            <div class="alert alert-warning">No results found.</div>
        {% endif %}
    </body>
    </html>
    """, query=query, results=results, message=message)

# === Run App ===
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5002))
    app.run(host='0.0.0.0', port=port)
