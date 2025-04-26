import os
import pandas as pd
import difflib
import re
from supabase import create_client, Client
from werkzeug.utils import secure_filename
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, redirect
from flask import redirect, url_for
from openpyxl import load_workbook
from collections import defaultdict
from flask import session, redirect, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps





# === Supabase Config ===
SUPABASE_URL = "https://wmthdsalqsrdiwxbmfey.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndtdGhkc2FscXNyZGl3eGJtZmV5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQyNjE2NTEsImV4cCI6MjA1OTgzNzY1MX0.3_3iBmNy9VM5BRycEKLvTfBBCRQkjJF7kP0EN-VZH68"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
# Simple user store (you can also use .env or Supabase if needed)
users = {
    "ailianyvette@gmail.com": generate_password_hash("jojo16022001"),
    "kuoyen23@yahoo.com": generate_password_hash("jojo16022001")
}

# === Flask App ===
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey123")
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)



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
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>

    </html>
    """, message=message)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))


# === Upload Endpoint ===
@app.route('/upload', methods=['POST'])
@login_required
def upload_product_api():  #
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    try:
        df = pd.read_excel(filepath, sheet_name='Master')
        wb = load_workbook(filepath, data_only=True)

        for _, row in df.iterrows():
            code_raw = str(row['Code'])
            code = code_raw.replace("Code:", "").strip()

            product_tab = row['Description'].strip()
            if product_tab in wb.sheetnames:
                sheet = wb[product_tab]
                print(f"[DEBUG] Tab: {product_tab}")
                for row in [5, 6, 7]:
                    for col in ['F', 'G', 'H', 'I', 'J']:
                        cell_ref = f'{col}{row}'
                        cell = sheet[cell_ref]
                        print(f"[DEBUG] {cell_ref}: {cell.value if cell else 'None'}")
                measurements = extract_measurements(sheet)

            else:
                measurements = ""

            data = {
                "design_number": int(row['Design Number']),
                "description": row['Description'],
                "price": float(row['Price']),
                "total_quantity": int(row['Total Quantity']),
                "color": row['Color'],
                "code": code,
                "upload_date": datetime.utcnow().isoformat(),
                "source_file": filename,
                "measurements": measurements
            }

            supabase.table("products").insert(data).execute()

        return jsonify({"message": "Upload and insert successful"})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# === Run the App ===
from flask import render_template_string

@app.route('/search', methods=['GET'])
def search():
    code = request.args.get('code')
    description = request.args.get('description')

    query = supabase.table("products").select("*")

    if code:
        query = query.ilike("code", f"%{code}%")
    elif description:
        query = query.ilike("description", f"%{description}%")
    else:
        return "Please provide a code or description", 400

    result = query.execute()
    data = result.data

    # HTML table template
    html_template = """
    <html>
        <head><title>Search Results</title></head>
        <body>
            <h2>Search Results</h2>
            {% if data %}
            <table border="1" cellpadding="8">
                <tr>
                    {% for key in data[0].keys() %}
                        <th>{{ key }}</th>
                    {% endfor %}
                </tr>
                {% for row in data %}
                    <tr>
                    {% for value in row.values() %}
                        <td>{{ value }}</td>
                    {% endfor %}
                    </tr>
                {% endfor %}
            </table>
            {% else %}
                <p>No matching results found.</p>
            {% endif %}
        </body>
    </html>
    """
    return render_template_string(html_template, data=data)

def extract_measurements(sheet):
    values = []
    for row in [5, 6, 7]:
        cell = sheet[f'H{row}']
        if cell and cell.value:
            text = str(cell.value).strip()

            replacements = {
                r'\bptp\b': 'PTP',
                r'\bhip\b': 'Hip',
                r'\bhips\b': 'Hip',
                r'\bwaist\b': 'Waist',
                r'\blength\b': 'Length',
                r'\bl\b': 'Length',
                r'\bw\b': 'Waist',
                r'\bh\b': 'Hip',
                r'\binner\b': 'Inner',
                r'\bouter\b': 'Outer'
            }

            for pattern, replacement in replacements.items():
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
            text = re.sub(r'\s*,\s*', ', ', text)
            text = re.sub(r'\s+', ' ', text)

            values.append(text)

    return ', '.join(values)



@app.route('/upload-form', methods=['GET', 'POST'])
@login_required
def upload_form():
    message = None

    if request.method == 'POST':
        print("[DEBUG] Upload form POST triggered",flush=True)
        if 'file' not in request.files or request.files['file'].filename == '':
            message = "No file selected."
        else:
            print("[DEBUG] File selected: proceeding to save and process...",flush=True)
            file = request.files['file']
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            try:
                print("[DEBUG] Starting full upload processing...",flush=True)

                # Pack_List tab
                try:
                    print("[DEBUG] Processing Pack_List tab...",flush=True)
                    packlist_df = pd.read_excel(filepath, sheet_name='Pack_List')
                    print("[DEBUG] ✅ Loaded Pack_List",flush=True)
                    for i, row in packlist_df.iterrows():
                        row_dict = row.dropna().to_dict()
                        supabase.table("packlist").insert({
                            "source_file": filename,
                            "row_index": i,
                            "row_data": row_dict
                        }).execute()
                except Exception as e:
                    print(f"[DEBUG] ❌ Failed to load or save Pack_List: {str(e)}",flush=True)

                # Bill tab
                try:
                    print("[DEBUG] Attempting to read Bill tab...",flush=True)
                    bill_df = pd.read_excel(filepath, sheet_name='Bill')
                    print("[DEBUG] ✅ Loaded Bill",flush=True)
                    for i, row in bill_df.iterrows():
                        row_dict = row.dropna().to_dict()
                        print(f"[DEBUG] Bill row {i}: {row_dict}",flush=True)
                        supabase.table("bills").insert({
                            "source_file": filename,
                            "row_index": i,
                            "row_data": row_dict
                        }).execute()
                except Exception as e:
                    print(f"[DEBUG] ❌ Failed to load or save Bill tab: {str(e)}",flush=True)

                # Master tab
                df = pd.read_excel(filepath, sheet_name='Master')
                wb = load_workbook(filepath, data_only=True)

                for _, row in df.iterrows():
                    code_raw = str(row['Code'])
                    code = code_raw.replace("Code:", "").strip()
                    product_tab = row['Description'].strip()

                    tab_match = difflib.get_close_matches(product_tab, wb.sheetnames, n=1, cutoff=0.6)
                    if tab_match:
                        sheet = wb[tab_match[0]]
                        measurements = extract_measurements(sheet)
                    else:
                        measurements = ""

                    data = {
                        "design_number": int(row['Design Number']),
                        "description": row['Description'],
                        "price": float(row['Price']),
                        "total_quantity": int(row['Total Quantity']),
                        "color": row['Color'],
                        "code": code,
                        "upload_date": datetime.utcnow().isoformat(),
                        "source_file": filename,
                        "measurements": measurements
                    }

                    supabase.table("products").insert(data).execute()

                message = "✅ Upload and insert successful!"

            except Exception as e:
                print(f"[DEBUG] ❌ Outer upload error: {str(e)}",flush=True)
                message = f"❌ Upload failed: {str(e)}"

    return render_template_string("""
    <html>
        <head>
            <title>Upload Product Excel</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
        </head>
        <body class="container py-5">
           <nav class="navbar navbar-expand-lg navbar-dark bg-dark mb-4">
                <div class="container-fluid">
                    <a class="navbar-brand" href="/">🧾 2PM App</a>
                    <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#mainNavbar" aria-controls="mainNavbar" aria-expanded="false" aria-label="Toggle navigation">
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
                        <span class="navbar-text text-white me-3">
                            👋 {{ session['user'] }}
                        </span>
                        <a href="/logout" class="btn btn-outline-light btn-sm">Logout</a>
                        </div>
                    {% endif %}
                    </div>
                </div>
            </nav>

            <h2 class="mb-4">📤 Upload Product Excel File</h2>
            {% if message %}
                <div class="alert alert-info">{{ message }}</div>
            {% endif %}
            <form method="post" enctype="multipart/form-data">
                <div class="mb-3">
                    <input class="form-control" type="file" name="file" required>
                </div>
                <button class="btn btn-primary" type="submit">Upload File</button>
            </form>
        </body>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>                          
    </html>
    """, message=message)





@app.route('/delete/<row_id>', methods=['POST'])
@login_required
def delete_row(row_id):
    try:
        supabase.table("products").delete().eq("id", row_id).execute()
        return redirect(url_for('search_form', msg='deleted'))
    except Exception as e:
        return f"Error deleting row: {str(e)}", 500

    
@app.route('/delete-by-file', methods=['POST'])
@login_required
def delete_by_file():
    filename = request.form.get('source_file')
    if not filename:
        return "No file name provided", 400
    try:
        supabase.table("products").delete().eq("source_file", filename).execute()
        return redirect(url_for('search_form', msg='bulk_deleted', filename=filename))
    except Exception as e:
        return f"Error deleting rows from file: {str(e)}", 500


@app.route('/search-form', methods=['GET', 'POST'])
@login_required
def search_form():
    results = []
    query = ""
    message = request.args.get('msg')
    filename = request.args.get('filename')

    # Get unique Excel file names for dropdown
    file_list = supabase.table("products").select("source_file").execute().data
    unique_files = sorted(set(row['source_file'] for row in file_list if row.get('source_file')))

    if request.method == 'POST' and 'query' in request.form:
        query = request.form.get('query', '').strip()

        if query:
            code_match = supabase.table("products").select("*").ilike("code", f"%{query}%").execute().data
            desc_match = supabase.table("products").select("*").ilike("description", f"%{query}%").execute().data

            seen = set()
            for row in code_match + desc_match:
                row_id = row["id"]
                if row_id not in seen:
                    results.append(row)
                    seen.add(row_id)

    # Lookup buyers from 'bills' table
    bill_rows = supabase.table("bills").select("row_data").execute().data
    buyers_by_code = {}

    for bill in bill_rows:
        desc = str(bill['row_data'].get('Description', '')).strip()
        name = str(bill['row_data'].get('Name', '')).strip()
        price = bill['row_data'].get('Price', '')

        match = re.search(r'Code[:\s]*(\d+)', desc)
        if match:
            code = match.group(1).strip()
            buyers_by_code.setdefault(code, set()).add((name, price))

    # Convert sets to list of dicts for display
    for code in buyers_by_code:
        buyers_by_code[code] = [{'name': name, 'price': price} for name, price in buyers_by_code[code]]


    for r in results:
        r['buyers'] = buyers_by_code.get(r.get('code', ''), [])

    return render_template_string("""
    <!DOCTYPE html>
<html>
<head>
    <title>Search Products</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</head>
<body class="container py-5">
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark mb-4">
        <div class="container-fluid">
            <a class="navbar-brand" href="/search-form">🧾 CPSApp</a>
            <div class="collapse navbar-collapse" id="mainNavbar">
                <ul class="navbar-nav me-auto mb-2 mb-lg-0">
                    <li class="nav-item">
                        <a class="nav-link" href="/upload-form">📤 Upload</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link active" href="/search-form">🔍 Search & Delete</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/view-packlist">📦 Pack_List</a>
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

    <h2 class="mb-4">🔎 Search Products</h2>

    {% if message == 'deleted' %}
        <div class="alert alert-success">✅ Row successfully deleted.</div>
    {% elif message == 'bulk_deleted' %}
        <div class="alert alert-success">✅ All rows from file <strong>{{ filename }}</strong> were deleted.</div>
    {% endif %}

    <!-- 🔍 Search form -->
    <form method="post" class="mb-4">
        <div class="input-group">
            <input type="text" class="form-control" name="query" placeholder="Enter code or description" value="{{ query }}" required>
            <button class="btn btn-primary" type="submit">Search</button>
        </div>
    </form>

    <!-- 📂 Delete-by-file form -->
    <form method="post" action="/delete-by-file" class="mb-4">
        <div class="row g-2 align-items-center">
            <div class="col-auto">
                <select name="source_file" class="form-select" required>
                    <option value="">-- Select Excel file to delete --</option>
                    {% for f in unique_files %}
                        <option value="{{ f }}">{{ f }}</option>
                    {% endfor %}
                </select>
            </div>
            <div class="col-auto">
                <button class="btn btn-outline-danger" type="submit" onclick="return confirm('Delete all rows from this file?');">
                    Delete All From File
                </button>
            </div>
        </div>
    </form>

    {% if results %}
        <div class="table-responsive">
            <table class="table table-bordered align-middle">
                <thead class="table-light">
                    <tr>
                        <th>Code</th>
                        <th>Description</th>
                        <th>Price</th>
                        <th>Color</th>
                        <th>Measurements</th>
                        <th>Design Number</th>
                        <th>Source File</th>
                        <th>Buyers</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {% for row in results %}
                        <tr>
                            <td>{{ row['code'] }}</td>
                            <td>{{ row['description'] }}</td>
                            <td>{{ row['price'] }}</td>
                            <td>{{ row['color'] }}</td>
                            <td>{{ row['measurements'] }}</td>
                            <td>{{ row['design_number'] }}</td>
                            <td>{{ row['source_file'] }}</td>
                            <td>
                                {% if row['buyers'] %}
                                    <ul class="mb-0">
                                        {% for buyer in row['buyers'] %}
                                            <li>{{ buyer.name }}</li>
                                        {% endfor %}
                                    </ul>
                                {% else %}
                                    <span class="text-muted">No buyers</span>
                                {% endif %}
                            </td>
                            <td>
                                <form method="post" action="/delete/{{ row['id'] }}" onsubmit="return confirm('Delete this row?');">
                                    <button class="btn btn-sm btn-danger">Delete</button>
                                </form>
                            </td>
                        </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    {% elif query %}
        <div class="alert alert-warning">No results found for "{{ query }}".</div>
    {% endif %}
    <script>
    document.addEventListener('DOMContentLoaded', function() {
        const searchInput = document.querySelector('input[name="query"]');
        searchInput.blur();  // Remove focus after page load
    });
    </script>
                              
</body>
</html>

    """, results=results, query=query, message=message, filename=filename, unique_files=unique_files)




def process_product_tab(sheet, product_name):
    # Example: existing logic to extract other product info...

    measurements = extract_measurements(sheet)

    product_data = {
        'name': product_name,
        # 'other_field': value,
        'measurements': measurements,
    }

    return product_data

@app.route('/get-products')
def get_products():
    products = supabase.table('products').select("*").execute().data

    filtered = []
    for p in products:
        # Remove ID and Upload Date
        p.pop('id', None)
        p.pop('upload_date', None)
        filtered.append(p)

    return jsonify(filtered)


@app.route('/view-packlist', methods=['GET', 'POST'])
@login_required
def view_packlist():
    selected_file = None
    packlist_df = None
    error = None

    # Fetch file list from Supabase
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
        <head>
            <title>📦 View Pack_List</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="container py-5">
            <nav class="navbar navbar-expand-lg navbar-dark bg-dark mb-4">
                <div class="container-fluid">
                    <a class="navbar-brand" href="/search-form">🧾 CPSApp</a>
                    <div class="collapse navbar-collapse justify-content-between">
                        <ul class="navbar-nav me-auto mb-2 mb-lg-0">
                            <li class="nav-item"><a class="nav-link" href="/upload-form">📤 Upload</a></li>
                            <li class="nav-item"><a class="nav-link" href="/search-form">🔍 Search & Delete</a></li>
                            <li class="nav-item"><a class="nav-link active" href="/view-packlist">📦 Pack_List</a></li>
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

            <h2 class="mb-4">📦 View Pack_List Sheet</h2>

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

@app.route('/')
@login_required
def index():
    return redirect(url_for('search_form'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5002))
    app.run(host='0.0.0.0', port=port)
