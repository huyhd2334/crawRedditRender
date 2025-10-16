from flask import Flask, send_from_directory, render_template_string, abort
import os
import json
import sqlite3
from datetime import datetime

app = Flask(__name__)
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DATA_DIR, "data.db")

# ======================
# HTML Templates
# ======================

INDEX_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Reddit Crawler Data</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 900px; margin: 24px auto; }
    h1 { color: #333; }
    a { color: #1a73e8; text-decoration: none; }
    table { width:100%; border-collapse: collapse; margin-top: 12px; }
    th, td { padding: 8px 10px; border-bottom: 1px solid #eee; text-align: left; }
    .mono { font-family: monospace; color:#444; }
    .small { color:#666; font-size:0.9em; }
  </style>
</head>
<body>
  <h1>Reddit Crawler — Data Explorer</h1>

  <h2>📁 JSON Files</h2>
  {% if json_files %}
    <table>
      <thead><tr><th>#</th><th>User</th><th>File</th><th>Created</th><th>Actions</th></tr></thead>
      <tbody>
      {% for f in json_files %}
        <tr>
          <td>{{ loop.index }}</td>
          <td>{{ f.username }}</td>
          <td class="mono">{{ f.filename }}</td>
          <td class="small">{{ f.mtime }}</td>
          <td>
            <a href="/view/{{ f.filename }}">View</a> |
            <a href="/download/{{ f.filename }}">Download</a>
          </td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
  {% else %}
    <p>No JSON user files yet.</p>
  {% endif %}

  <hr>

  <h2>🧩 SQLite Tables</h2>
  {% if tables %}
    <ul>
      {% for t in tables %}
        <li><a href="/table/{{ t }}">{{ t }}</a></li>
      {% endfor %}
    </ul>
  {% else %}
    <p>No SQLite database found at <code>{{ db_path }}</code>.</p>
  {% endif %}
</body>
</html>
"""

VIEW_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>View {{ filename }}</title>
  <style>
    body { font-family: monospace; white-space: pre-wrap; background:#f7f7f9; padding:16px; }
    .box { background: #fff; padding:16px; border-radius:6px; box-shadow:0 1px 4px rgba(0,0,0,0.05); }
    a { display:inline-block; margin-bottom:12px; color:#1a73e8; }
  </style>
</head>
<body>
  <a href="/">← Back to list</a>
  <div class="box"><pre>{{ content }}</pre></div>
</body>
</html>
"""

TABLE_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Table: {{ table }}</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 1200px; margin: 24px auto; }
    table { border-collapse: collapse; width: 100%; margin-top: 16px; }
    th, td { border: 1px solid #ccc; padding: 6px 8px; text-align: left; }
    th { background: #f2f2f2; }
    a { color: #1a73e8; text-decoration: none; }
  </style>
</head>
<body>
  <a href="/">← Back to main</a>
  <h1>Table: {{ table }}</h1>
  {% if rows %}
  <table>
    <thead>
      <tr>
        {% for col in columns %}
          <th>{{ col }}</th>
        {% endfor %}
      </tr>
    </thead>
    <tbody>
      {% for row in rows %}
      <tr>
        {% for col in columns %}
          <td>{{ row[col] }}</td>
        {% endfor %}
      </tr>
      {% endfor %}
    </tbody>
  </table>
  {% else %}
    <p>No data in this table.</p>
  {% endif %}
</body>
</html>
"""

# ======================
# Utility functions
# ======================

def list_data_files():
    """Trả về danh sách file JSON trong thư mục data"""
    if not os.path.isdir(DATA_DIR):
        return []
    items = []
    for name in os.listdir(DATA_DIR):
        if not name.lower().endswith(".json"):
            continue
        path = os.path.join(DATA_DIR, name)
        if not os.path.isfile(path):
            continue
        stat = os.stat(path)
        mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        username = name
        if name.startswith("user_") and name.endswith(".json"):
            username = name[len("user_"):-len(".json")]
        items.append({"filename": name, "username": username, "mtime": mtime})
    items.sort(key=lambda x: x["mtime"], reverse=True)
    return items

def list_tables():
    """Trả về danh sách bảng trong SQLite nếu có"""
    if not os.path.isfile(DB_PATH):
        return []
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [r[0] for r in cur.fetchall()]
    return tables

# ======================
# Routes
# ======================

@app.route("/")
def index():
    files = list_data_files()
    tables = list_tables()
    return render_template_string(INDEX_HTML, json_files=files, tables=tables, db_path=DB_PATH)

@app.route("/view/<filename>")
def view_file(filename):
    safe = os.path.basename(filename)
    path = os.path.join(DATA_DIR, safe)
    if not os.path.isfile(path):
        abort(404)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        pretty = json.dumps(data, ensure_ascii=False, indent=2)
    except Exception as e:
        pretty = f"Error reading file: {e}"
    return render_template_string(VIEW_HTML, filename=safe, content=pretty)

@app.route("/download/<filename>")
def download_file(filename):
    safe = os.path.basename(filename)
    return send_from_directory(DATA_DIR, safe, as_attachment=True)

@app.route("/table/<table>")
def show_table(table):
    if not os.path.isfile(DB_PATH):
        return f"No database file found at {DB_PATH}", 404
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        try:
            cur.execute(f"SELECT * FROM {table}")
            rows = [dict(r) for r in cur.fetchall()]
            columns = [d[0] for d in cur.description]
        except Exception as e:
            return f"Error reading table {table}: {e}"
    return render_template_string(TABLE_HTML, table=table, columns=columns, rows=rows)

# ======================
# Main
# ======================
@app.route("/download_db")
def download_db():
    """Tải trực tiếp file SQLite"""
    if not os.path.isfile(DB_PATH):
        abort(404)
    return send_from_directory(DATA_DIR, os.path.basename(DB_PATH), as_attachment=True)

@app.route("/export_sql")
def export_sql():
    """Xuất toàn bộ database thành file .sql (dump text)"""
    if not os.path.isfile(DB_PATH):
        abort(404)
    import io
    buf = io.StringIO()
    with sqlite3.connect(DB_PATH) as conn:
        for line in conn.iterdump():
            buf.write(f"{line}\n")
    content = buf.getvalue()
    buf.close()
    # Lưu tạm để tải
    sql_path = os.path.join(DATA_DIR, "export.sql")
    with open(sql_path, "w", encoding="utf-8") as f:
        f.write(content)
    return send_from_directory(DATA_DIR, "export.sql", as_attachment=True)

if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
