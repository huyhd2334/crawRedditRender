from flask import Flask, jsonify, send_file
import os
import time
import threading
from datetime import datetime

app = Flask(__name__)

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# --- Giả lập hàm crawl data Reddit ---
def crawl_reddit_data():
    """Fake crawler, thay bằng crawler thật của bạn"""
    # Tạo dữ liệu mẫu (bạn có thể thay phần này bằng code crawl Reddit thật)
    data = [
        ("post1", "userA", "This is a post about AI"),
        ("post2", "userB", "Machine Learning is cool!"),
        ("post3", "userC", "Python for Data Science"),
    ]
    return data


def export_to_sql():
    """Tạo file SQL mới mỗi 12h"""
    while True:
        now = datetime.now()
        filename = f"reddit_data_{now.strftime('%Y%m%d_%H%M')}.sql"
        filepath = os.path.join(DATA_DIR, filename)

        data = crawl_reddit_data()

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("CREATE TABLE reddit_posts (id TEXT, user TEXT, content TEXT);\n")
            for post_id, user, content in data:
                content = content.replace("'", "''")
                f.write(f"INSERT INTO reddit_posts VALUES ('{post_id}', '{user}', '{content}');\n")

        print(f"[INFO] Saved {filename}")
        # Đợi 12h = 43200 giây
        time.sleep(43200)


@app.route("/")
def home():
    html = """
    <html>
    <head>
        <title>Web Reddit SQL Exporter</title>
    </head>
    <body style="font-family: sans-serif; text-align: center; margin-top: 50px;">
        <h2>Reddit SQL Exporter</h2>

        <h3>Chọn file SQL để tải:</h3>
        <select id="fileSelect" style="padding: 5px; min-width: 250px;"></select>
        <button onclick="downloadSelected()" style="padding: 5px 10px;">Tải file</button>

        <script>
        async function loadFiles() {
            const res = await fetch("/list_files");
            const files = await res.json();
            const select = document.getElementById("fileSelect");
            if (files.length === 0) {
                select.innerHTML = "<option>Chưa có file nào</option>";
                return;
            }
            select.innerHTML = files.map(f => `<option>${f}</option>`).join("");
        }

        function downloadSelected() {
            const f = document.getElementById("fileSelect").value;
            if (f && f !== "Chưa có file nào") {
                window.location = `/download/${f}`;
            }
        }

        loadFiles();
        </script>
    </body>
    </html>
    """
    return html


@app.route("/list_files")
def list_files():
    files = sorted([f for f in os.listdir(DATA_DIR) if f.endswith(".sql")])
    return jsonify(files)


@app.route("/download/<filename>")
def download_file(filename):
    """Tải file cụ thể"""
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return jsonify({"error": "File không tồn tại"}), 404
    return send_file(path, as_attachment=True)


if __name__ == "__main__":
    # Tạo 1 thread nền để crawl và export file mỗi 12h
    t = threading.Thread(target=export_to_sql, daemon=True)
    t.start()

    app.run(host="0.0.0.0", port=8080)
