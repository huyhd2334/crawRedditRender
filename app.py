from flask import Flask, jsonify, send_file
import os
import threading
import time
from datetime import datetime
from reddit_crawler import RedditCrawler

app = Flask(__name__)

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

crawler = RedditCrawler()  # Tạo instance toàn cục

# --- Hàm chạy định kỳ mỗi 12h ---
def crawl_periodically():
    while True:
        try:
            crawler.fetch_users_from_subreddit()
        except Exception as e:
            print(f"[ERROR] Crawl failed: {e}")
        # Lặp lại sau 12h (43200 giây)
        time.sleep(43200)


@app.route("/")
def home():
    html = """
    <html>
    <head><title>Reddit SQL Exporter</title></head>
    <body style="font-family: sans-serif; text-align: center; margin-top: 50px;">
        <h2>📦 Reddit SQL Exporter</h2>
        <p>Tự động crawl và xuất file SQL mới mỗi 12 giờ.</p>

        <h3>Chọn file để tải:</h3>
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
    """Trả danh sách file SQL"""
    files = sorted([f for f in os.listdir(DATA_DIR) if f.endswith(".sql")])
    return jsonify(files)


@app.route("/download/<filename>")
def download_file(filename):
    """Tải file SQL"""
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return jsonify({"error": "File không tồn tại"}), 404
    return send_file(path, as_attachment=True)


if __name__ == "__main__":
    # Thread nền để tự crawl
    t = threading.Thread(target=crawl_periodically, daemon=True)
    t.start()

    app.run(host="0.0.0.0", port=8080)
