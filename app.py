from flask import Flask, send_from_directory, render_template_string, abort
import os
import json
from datetime import datetime

app = Flask(__name__)
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# HTML template hiển thị danh sách người dùng
INDEX_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Reddit Crawler - Users</title>
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
  <h1>Reddit Crawler — Users</h1>
  <p>Folder: <span class="mono">{{ data_dir }}</span></p>
  <p>Total users: <strong>{{ total }}</strong></p>

  {% if files %}
  <table>
    <thead><tr><th>#</th><th>User</th><th>File</th><th>Created</th><th>Actions</th></tr></thead>
    <tbody>
    {% for f in files %}
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
    <p>No user files yet. Wait for crawler to create JSON in <code>data/</code>.</p>
  {% endif %}
  <hr>
  <p class="small">Auto-updated when files appear. Refresh to see new users.</p>
</body>
</html>
"""

# Template hiển thị nội dung JSON đẹp
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

def list_data_files():
    """Trả về danh sách dict: {filename, username, mtime} theo thời gian chỉnh sửa mới nhất"""
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

@app.route("/")
def index():
    files = list_data_files()
    return render_template_string(INDEX_HTML, files=files, total=len(files), data_dir=DATA_DIR)

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

if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
