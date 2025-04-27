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
from collections import defaultdict

# === Supabase Config ===
SUPABASE_URL = "https://wmthdsalqsrdiwxbmfey.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndtdGhkc2FscXNyZGl3eGJtZmV5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQyNjE2NTEsImV4cCI6MjA1OTgzNzY1MX0.3_3iBmNy9VM5BRycEKLvTfBBCRQkjJF7kP0EN-VZH68"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# === Flask App ===
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey123")
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# === Users ===
users = {
    "ailianyvette@gmail.com": generate_password_hash("jojo16022001"),
    "kuoyen23@yahoo.com": generate_password_hash("jojo16022001")
}

# === Login Required Decorator ===
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
        <head><title>Login</title></head>
        <body>
            <h2>Login</h2>
            {% if message %}
                <p>{{ message }}</p>
            {% endif %}
            <form method="post">
                <input type="email" name="email" required>
                <input type="password" name="password" required>
                <button type="submit">Login</button>
            </form>
        </body>
    </html>
    """, message=message)

# === Logout ===
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

# === Generate Invoice Form ===
@app.route('/invoice', methods=['GET', 'POST'])
@login_required
def invoice_form():
    invoice_number = f"INV-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    invoice_date = datetime.utcnow().strftime('%Y-%m-%d')
    live_session_number = ""
    total = 0
    courier_fee = 0
    products = []
    delivery = ""
    show_invoice = False

    if request.method == 'POST':
        invoice_number = request.form.get('invoice_number')
        invoice_date = request.form.get('invoice_date')
        live_session_number = request.form.get('live_session_number')
        products_raw = request.form.get('products', '')
        delivery = request.form.get('delivery')

        for line in products_raw.strip().split('\n'):
            if line:
                try:
                    parts = [p.strip() for p in line.split('|')]
                    desc, code, price, qty = parts
                    price = float(price)
                    qty = int(qty)
                    subtotal = price * qty
                    products.append({
                        "desc": desc,
                        "code": code,
                        "price": price,
                        "qty": qty,
                        "subtotal": subtotal
                    })
                    total += subtotal
                except Exception as e:
                    print(f"[DEBUG] Failed to parse line: {line}, Error: {str(e)}", flush=True)

        if delivery == "Courier Service":
            courier_fee = 4
            total += courier_fee

        show_invoice = True

    return render_template_string("""
    <html>
        <head>
            <title>🧾 Create Invoice</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="container py-5">
            <h2>Create Invoice</h2>
            <form method="post" class="mb-5">
                <div class="mb-3">
                    <label>Invoice Number</label>
                    <input type="text" name="invoice_number" class="form-control" value="{{ invoice_number }}" readonly>
                </div>
                <div class="mb-3">
                    <label>Invoice Date</label>
                    <input type="text" name="invoice_date" class="form-control" value="{{ invoice_date }}" readonly>
                </div>
                <div class="mb-3">
                    <label>Live Session Number</label>
                    <input type="text" name="live_session_number" class="form-control" value="{{ live_session_number }}">
                </div>

                <h5>Products</h5>
                <div class="mb-3">
                    <textarea class="form-control" name="products" rows="5" placeholder="Description | Code | Price | Qty">{{ request.form.get('products', '') }}</textarea>
                    <small class="form-text text-muted">Enter one product per line, format: Description | Code | Price | Qty</small>
                </div>

                <h5>Delivery Method</h5>
                <div class="mb-3">
                    {% for option in ["Courier Service", "Jurong Point", "NorthPoint", "Westmall", "Accumulation"] %}
                        <div class="form-check">
                            <input class="form-check-input" type="radio" name="delivery" value="{{ option }}" id="{{ option }}" {% if delivery == option %}checked{% endif %}>
                            <label class="form-check-label" for="{{ option }}">{{ option }} {% if option == "Courier Service" %}(+$4){% endif %}</label>
                        </div>
                    {% endfor %}
                </div>

                <button type="submit" class="btn btn-primary">Generate Invoice</button>
            </form>

            {% if show_invoice %}
            <h3>🧾 Invoice</h3>
            <p><strong>Invoice Number:</strong> {{ invoice_number }}</p>
            <p><strong>Invoice Date:</strong> {{ invoice_date }}</p>
            <p><strong>Live Session Number:</strong> {{ live_session_number }}</p>
            <table class="table table-bordered">
                <thead class="table-light">
                    <tr>
                        <th>Description</th>
                        <th>Code</th>
                        <th>Price</th>
                        <th>Qty</th>
                        <th>Subtotal</th>
                    </tr>
                </thead>
                <tbody>
                    {% for item in products %}
                    <tr>
                        <td>{{ item.desc }}</td>
                        <td>{{ item.code }}</td>
                        <td>{{ item.price }}</td>
                        <td>{{ item.qty }}</td>
                        <td>{{ item.subtotal }}</td>
                    </tr>
                    {% endfor %}
                    {% if courier_fee %}
                    <tr>
                        <td colspan="4"><strong>Courier Fee</strong></td>
                        <td>{{ courier_fee }}</td>
                    </tr>
                    {% endif %}
                    <tr>
                        <td colspan="4"><strong>Total</strong></td>
                        <td><strong>{{ total }}</strong></td>
                    </tr>
                </tbody>
            </table>

            <div class="alert alert-info">
                <strong>Please make payment via:</strong><br>
                1. Bank transfer to OCBC current account 588056739001<br>
                2. PAYNOW to UEN number: 201013470W<br>
                Cupid Apparel Pte Ltd<br><br>
                ** Kindly indicate your FB name in the payment description, and do a screenshot of your payment.
            </div>
            {% endif %}
        </body>
    </html>
    """, invoice_number=invoice_number, invoice_date=invoice_date, live_session_number=live_session_number, products=products, courier_fee=courier_fee, total=total, delivery=delivery, show_invoice=show_invoice)

# === Default Home Redirect ===
@app.route('/')
@login_required
def index():
    return redirect(url_for('search_form'))  # Or any default route like invoice_form

# === Run App ===
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5002))
    app.run(host='0.0.0.0', port=port)
