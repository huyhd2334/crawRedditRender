from flask import Flask, send_from_directory, render_template_string, abort
import os
import sqlite3
from datetime import datetime

app = Flask(__name__)
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DATA_DIR, "reddit_data.db")
SQL_PATH = os.path.join(DATA_DIR, "reddit_data.sql")


INDEX_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Reddit Crawler Dashboard</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 900px; margin: 24px auto; }
    h1 { color: #333; }
    table { width:100%; border-collapse: collapse; margin-top: 12px; }
    th, td { padding: 8px 10px; border-bottom: 1px solid #eee; text-align: left; }
    a { color: #1a73e8; text-decoration: none; }
    .mono { font-family: monospace; color:#444; }
    .small { color:#666; font-size:0.9em; }
  </style>
</head>
<body>
  <h1> Reddit Crawler Dashboard</h1>
  <p>Database file: <span class="mono">{{ db_path }}</span></p>

  <h3>Available Data</h3>
  <ul>
    <li><a href="/users">View Users</a></li>
    <li><a href="/download-sql">Download SQL Dump</a></li>
  </ul>

  <hr>
  <p class="small">Last updated: {{ last_update or 'N/A' }}</p>
</body>
</html>
"""

USERS_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Reddit Users</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 1000px; margin: 24px auto; }
    table { width:100%; border-collapse: collapse; }
    th, td { border-bottom:1px solid #eee; padding:8px; text-align:left; }
    th { background:#f7f7f7; }
    a { text-decoration:none; color:#1a73e8; }
  </style>
</head>
<body>
  <h1>Reddit Users</h1>
  <p>Total users: <strong>{{ total }}</strong></p>
  <table>
    <thead>
      <tr>
        <th>#</th><th>Username</th><th>Link Karma</th><th>Comment Karma</th><th>Premium</th><th>Email Verified</th><th>Created</th>
      </tr>
    </thead>
    <tbody>
    {% for u in users %}
      <tr>
        <td>{{ loop.index }}</td>
        <td>{{ u.username }}</td>
        <td>{{ u.link_karma }}</td>
        <td>{{ u.comment_karma }}</td>
        <td>{{ "✅" if u.premium else "❌" }}</td>
        <td>{{ "✅" if u.verified_email else "❌" }}</td>
        <td>{{ u.created }}</td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
  <p><a href="/">← Back to dashboard</a></p>
</body>
</html>
"""

# ==============================
# Helper functions
# ==============================

def get_last_update():
    """Lấy thời gian cập nhật gần nhất của database"""
    if os.path.exists(DB_PATH):
        ts = os.path.getmtime(DB_PATH)
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    return None


def fetch_users():
    """Lấy danh sách user trong bảng r_user"""
    if not os.path.exists(DB_PATH):
        return []
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM r_user ORDER BY link_karma DESC LIMIT 100;")
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ==============================
# ROUTES
# ==============================

@app.route("/")
def index():
    last_update = get_last_update()
    return render_template_string(INDEX_HTML, db_path=DB_PATH, last_update=last_update)

@app.route("/users")
def users_page():
    users = fetch_users()
    return render_template_string(USERS_HTML, users=users, total=len(users))

@app.route("/download-sql")
def download_sql():
    if not os.path.exists(SQL_PATH):
        abort(404, "SQL dump not found.")
    return send_from_directory(DATA_DIR, os.path.basename(SQL_PATH), as_attachment=True)

# ==============================
# RUN
# ==============================
if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
