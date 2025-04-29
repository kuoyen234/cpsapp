import os
import pandas as pd
from supabase import create_client, Client
from werkzeug.utils import secure_filename
from datetime import datetime
from flask import (
    Flask, request, render_template_string,
    redirect, url_for, session
)
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from openpyxl import load_workbook

# === Supabase Config ===
SUPABASE_URL = "https://wmthdsalqsrdiwxbmfey.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndtdGhkc2FscXNyZGl3eGJtZmV5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQyNjE2NTEsImV4cCI6MjA1OTgzNzY1MX0.3_3iBmNy9VM5BRycEKLvTfBBCRQkjJF7kP0EN-VZH68"  # your key
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# === Demo Users ===
users = {
    "ailianyvette@gmail.com": generate_password_hash("jojo16022001"),
    "kuoyen23@yahoo.com":    generate_password_hash("jojo16022001"),
}

# === Flask Setup ===
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey123")
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# === Auth Decorator ===
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# === Navbar HTML (note: Jinja tags inside this WILL be evaluated) ===
NAV_HTML = """
<nav class="navbar navbar-expand-lg navbar-light bg-light mb-4">
  <div class="container-fluid">
    <a class="navbar-brand" href="{{ url_for('search_form') }}">CPSApp</a>
    <button class="navbar-toggler" type="button" data-bs-toggle="collapse"
            data-bs-target="#navbarNav" aria-controls="navbarNav"
            aria-expanded="false" aria-label="Toggle navigation">
      <span class="navbar-toggler-icon"></span>
    </button>
    <div class="collapse navbar-collapse" id="navbarNav">
      <ul class="navbar-nav">
        <li class="nav-item"><a class="nav-link" href="{{ url_for('upload') }}">Upload</a></li>
        <li class="nav-item"><a class="nav-link" href="{{ url_for('search_form') }}">Search</a></li>
        <li class="nav-item"><a class="nav-link" href="{{ url_for('delete_product') }}">Delete</a></li>
        <li class="nav-item"><a class="nav-link" href="{{ url_for('view_pack_list') }}">View Pack List</a></li>
        <li class="nav-item"><a class="nav-link" href="{{ url_for('logout') }}">Logout</a></li>
      </ul>
    </div>
  </div>
</nav>
"""

# === Login ===
@app.route('/login', methods=['GET','POST'])
def login():
    msg = None
    if request.method == 'POST':
        e,p = request.form['email'], request.form['password']
        if e in users and check_password_hash(users[e], p):
            session['user'] = e
            return redirect(url_for('search_form'))
        msg = "❌ Invalid credentials."
    return render_template_string(f"""
<!doctype html>
<html>
<head>
  <title>Login</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css"
        rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</head>
<body class="container py-5">
  <h2>🔐 Login to CPSApp</h2>
  {{% if msg %}}<div class="alert alert-danger">{{{{ msg }}}}</div>{{% endif %}}
  <form method="post">
    <div class="mb-3"><label>Email</label>
      <input type="email" name="email" class="form-control" required>
    </div>
    <div class="mb-3"><label>Password</label>
      <input type="password" name="password" class="form-control" required>
    </div>
    <button class="btn btn-primary">Login</button>
  </form>
</body>
</html>
    """, msg=msg)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return redirect(url_for('search_form'))

# === Upload ===
@app.route('/upload', methods=['GET','POST'])
@login_required
def upload():
    message = None
    if request.method=='POST':
        f = request.files.get('file')
        if f and f.filename.lower().endswith(('.xls','.xlsx,.xlsm')):
            fn = secure_filename(f.filename)
            path = os.path.join(app.config['UPLOAD_FOLDER'], fn)
            f.save(path)
            wb = load_workbook(path, data_only=True)
            if 'Master' in wb.sheetnames:
                ws = wb['Master']
                headers = [c.value for c in ws[1]]
                try:
                    i_code  = headers.index('Code')
                    i_desc  = headers.index('Description')
                    i_price = headers.index('Price')
                    i_qty   = headers.index('Total Quantity')
                except ValueError:
                    i_code, i_desc, i_price, i_qty = 0,1,2,3
                batch = []
                for row in ws.iter_rows(min_row=2, values_only=True):
                    code = row[i_code]
                    if not code: continue
                    batch.append({
                        'code': str(code),
                        'description': row[i_desc],
                        'price': float(row[i_price] or 0),
                        'quantity': int(row[i_qty] or 0),
                        'uploaded_at': datetime.utcnow().isoformat()
                    })
                if batch:
                    supabase.table('products').insert(batch).execute()
                    message = f"✅ Inserted {len(batch)} products from '{fn}'."
                else:
                    message = "⚠️ No rows found in Master sheet."
            else:
                message = "⚠️ 'Master' sheet not found."
        else:
            message = "❌ Please upload a valid Excel file."
    return render_template_string(f"""
<!doctype html>
<html>
<head>
  <title>Upload</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css"
        rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</head>
<body class="container py-5">
  {NAV_HTML}
  <h2>📁 Upload Excel File</h2>
  {{% if message %}}<div class="alert alert-info">{{{{ message }}}}</div>{{% endif %}}
  <form method="post" enctype="multipart/form-data">
    <div class="mb-3">
      <input type="file" name="file" class="form-control" accept=".xls,.xlsx,.xlsm" required>
    </div>
    <button class="btn btn-success">Upload & Import</button>
  </form>
</body>
</html>
    """, message=message)

# === Search ===
@app.route('/search-form', methods=['GET','POST'])
@login_required
def search_form():
    query, results = "", []
    if request.method=='POST':
        query = request.form.get('query','')
        if query:
            data = supabase.table('products') \
                .select("*") \
                .ilike('code', f'%{query}%') \
                .execute().data
            results = data or []
    return render_template_string(f"""
<!doctype html>
<html>
<head>
  <title>Search</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css"
        rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</head>
<body class="container py-5">
  {NAV_HTML}
  <h2>🔍 Search Products</h2>
  <form method="post" class="mb-4">
    <div class="input-group">
      <input type="text" name="query" class="form-control"
             placeholder="Enter code or description"
             value="{{{{ query }}}}" required>
      <button class="btn btn-primary">Search</button>
    </div>
  </form>
  {{% if results %}}
    <table class="table table-bordered">
      <thead><tr><th>Code</th><th>Description</th><th>Price</th><th>Qty</th></tr></thead>
      <tbody>
      {{% for r in results %}}
        <tr>
          <td>{{{{ r.code }}}}</td>
          <td>{{{{ r.description }}}}</td>
          <td>{{{{ r.price }}}}</td>
          <td>{{{{ r.quantity }}}}</td>
        </tr>
      {{% endfor %}}
      </tbody>
    </table>
  {{% elif query %}}
    <div class="alert alert-warning">No results for '{{{{ query }}}}'.</div>
  {{% endif %}}
</body>
</html>
    """, query=query, results=results)

# === Delete ===
@app.route('/delete', methods=['GET','POST'])
@login_required
def delete_product():
    msg = None
    if request.method=='POST':
        code = request.form.get('code','').strip()
        if code:
            supabase.table('products').delete().eq('code', code).execute()
            msg = f"✅ Deleted '{code}'."
        else:
            msg = "❌ Enter a product code."
    return render_template_string(f"""
<!doctype html>
<html>
<head>
  <title>Delete</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css"
        rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</head>
<body class="container py-5">
  {NAV_HTML}
  <h2>🗑️ Delete Product</h2>
  {{% if msg %}}<div class="alert alert-info">{{{{ msg }}}}</div>{{% endif %}}
  <form method="post">
    <div class="mb-3">
      <label>Product Code</label>
      <input type="text" name="code" class="form-control" required>
    </div>
    <button class="btn btn-danger">Delete</button>
  </form>
</body>
</html>
    """, msg=msg)

# === View Pack List ===
@app.route('/view-pack-list', methods=['GET','POST'])
@login_required
def view_pack_list():
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    table = None
    if request.method=='POST':
        fn = request.form.get('filename')
        path = os.path.join(app.config['UPLOAD_FOLDER'], fn)
        wb = load_workbook(path, data_only=True)
        if 'Pack_List' in wb.sheetnames:
            df = pd.DataFrame(wb['Pack_List'].values)
            df.columns = df.iloc[0]; df = df.iloc[1:]
            table = df.to_html(classes="table table-bordered", index=False)
        else:
            table = "<div class='alert alert-warning'>'Pack_List' sheet not found.</div>"
    return render_template_string(f"""
<!doctype html>
<html>
<head>
  <title>View Pack List</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css"
        rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</head>
<body class="container py-5">
  {NAV_HTML}
  <h2>📦 View Pack List</h2>
  <form method="post" class="mb-4">
    <div class="mb-3">
      <label>Select Uploaded File</label>
      <select name="filename" class="form-select" required>
        <option value="">-- choose file --</option>
        {{% for f in files %}}
          <option value="{{{{ f }}}}">{{{{ f }}}}</option>
        {{% endfor %}}
      </select>
    </div>
    <button class="btn btn-primary">Load Pack List</button>
  </form>
  {{% if table %}}
    <div>{{{{ table|safe }}}}</div>
  {{% endif %}}
</body>
</html>
    """, files=files, table=table)

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5002)))
