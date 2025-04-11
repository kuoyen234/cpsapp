import os
import pandas as pd
from flask import Flask, request, jsonify
from supabase import create_client, Client
from werkzeug.utils import secure_filename
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, redirect
from flask import redirect, url_for
from openpyxl import load_workbook


# === Supabase Config ===
SUPABASE_URL = "https://wmthdsalqsrdiwxbmfey.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndtdGhkc2FscXNyZGl3eGJtZmV5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQyNjE2NTEsImV4cCI6MjA1OTgzNzY1MX0.3_3iBmNy9VM5BRycEKLvTfBBCRQkjJF7kP0EN-VZH68"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# === Flask App ===
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# === Upload Endpoint ===
@app.route('/upload', methods=['POST'])
def upload_file():
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

        for _, row in df.iterrows():
            code_raw = str(row['Code'])
            code = code_raw.replace("Code:", "").strip()

            data = {
                "design_number": int(row['Design Number']),
                "description": row['Description'],
                "price": float(row['Price']),
                "total_quantity": int(row['Total Quantity']),
                "color": row['Color'],
                "code": code,
                "upload_date": datetime.utcnow().isoformat(),
                "source_file": filename
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

@app.route('/upload-form', methods=['GET', 'POST'])
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
                df = pd.read_excel(filepath, sheet_name='Master')
                for _, row in df.iterrows():
                    code_raw = str(row['Code'])
                    code = code_raw.replace("Code:", "").strip()

                    data = {
                        "design_number": int(row['Design Number']),
                        "description": row['Description'],
                        "price": float(row['Price']),
                        "total_quantity": int(row['Total Quantity']),
                        "color": row['Color'],
                        "code": code,
                        "source_file": filename,
                        "upload_date": datetime.utcnow().isoformat()
                    }

                    supabase.table("products").insert(data).execute()
                message = "✅ Upload and insert successful!"
            except Exception as e:
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
                    <a class="navbar-brand" href="/">🧾 CPSApp</a>
                    <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#mainNavbar" aria-controls="mainNavbar" aria-expanded="false" aria-label="Toggle navigation">
                        <span class="navbar-toggler-icon"></span>
                    </button>
                    <div class="collapse navbar-collapse" id="mainNavbar">
                        <ul class="navbar-nav me-auto mb-2 mb-lg-0">
                            <li class="nav-item">
                                <a class="nav-link" href="/upload-form">📤 Upload</a>
                            </li>
                            <li class="nav-item">
                                <a class="nav-link" href="/search-form">🔍 Search & Delete</a>
                            </li>
                        </ul>
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
    </html>
    """, message=message)


@app.route('/delete/<row_id>', methods=['POST'])

def delete_row(row_id):
    try:
        supabase.table("products").delete().eq("id", row_id).execute()
        return redirect(url_for('search_form', msg='deleted'))
    except Exception as e:
        return f"Error deleting row: {str(e)}", 500

    
@app.route('/delete-by-file', methods=['POST'])
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

    return render_template_string("""
    <html>
        <head>
            <title>Search Products</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
            <script>
                setTimeout(function() {
                    const alert = document.querySelector('.alert');
                    if (alert) {
                        alert.classList.add('fade');
                        alert.style.opacity = 0;
                    }
                }, 3000);
            </script>
        </head>
        <body class="container py-5">
            <nav class="navbar navbar-expand-lg navbar-dark bg-dark mb-4">
                <div class="container-fluid">
                    <a class="navbar-brand" href="/">🧾 CPSApp</a>
                    <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#mainNavbar" aria-controls="mainNavbar" aria-expanded="false" aria-label="Toggle navigation">
                        <span class="navbar-toggler-icon"></span>
                    </button>
                    <div class="collapse navbar-collapse" id="mainNavbar">
                        <ul class="navbar-nav me-auto mb-2 mb-lg-0">
                            <li class="nav-item">
                                <a class="nav-link" href="/upload-form">📤 Upload</a>
                            </li>
                            <li class="nav-item">
                                <a class="nav-link" href="/search-form">🔍 Search & Delete</a>
                            </li>
                        </ul>
                    </div>
                </div>
            </nav>

            <h2 class="mb-4">🔎 Search Products</h2>

            {% if message == 'deleted' %}
                <div class="alert alert-success">✅ Row successfully deleted.</div>
            {% elif message == 'bulk_deleted' %}
                <div class="alert alert-success">✅ All rows from file <strong>{{ filename }}</strong> were deleted.</div>
            {% endif %}

            <!-- Search form -->
            <form method="post" class="mb-4">
                <div class="input-group">
                    <input type="text" class="form-control" name="query" placeholder="Enter code or description" value="{{ query }}" required>
                    <button class="btn btn-primary" type="submit">Search</button>
                </div>
            </form>

            <!-- Delete-by-file form with dropdown -->
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
                        {% for key in results[0].keys() %}
                            {% if key != 'id' and key != 'upload_date' %}
                                <th>{{ key.replace('_', ' ').title() }}</th>
                            {% endif %}
                        {% endfor %}
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {% for row in results %}
                        <tr>
                            {% for key, value in row.items() %}
                                {% if key != 'id' and key != 'upload_date' %}
                                    <td>{{ value }}</td>
                                {% endif %}
                            {% endfor %}
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
        </body>
    </html>
    """, results=results, query=query, message=message, filename=filename, unique_files=unique_files)

@app.route('/')
def home():
    return render_template_string("""
    <html>
        <head>
            <title>Control Panel</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
        </head>
        <body>
            <nav class="navbar navbar-expand-lg navbar-dark bg-dark mb-4">
                <div class="container-fluid">
                    <a class="navbar-brand" href="/">🧾 CPSApp</a>
                    <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#mainNavbar" aria-controls="mainNavbar" aria-expanded="false" aria-label="Toggle navigation">
                        <span class="navbar-toggler-icon"></span>
                    </button>
                    <div class="collapse navbar-collapse" id="mainNavbar">
                        <ul class="navbar-nav me-auto mb-2 mb-lg-0">
                            <li class="nav-item">
                                <a class="nav-link" href="/upload-form">📤 Upload</a>
                            </li>
                            <li class="nav-item">
                                <a class="nav-link" href="/search-form">🔍 Search & Delete</a>
                            </li>
                        </ul>
                    </div>
                </div>
            </nav>

            <div class="container">
                <h1 class="mb-4">Welcome to CPSApp 👋</h1>
                <p>Please use the menu above to upload or search for products.</p>
            </div>
        </body>
    </html>
    """)

def extract_measurements(sheet):
    """Extract and concatenate measurements from cells H4, H5, H6"""
    values = []
    for row in [4, 5, 6]:
        cell_value = sheet[f'H{row}']
        if cell_value and cell_value.value:
            values.append(str(cell_value.value).strip())
    return ', '.join(values)  # Join all non-empty values into one string

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


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
