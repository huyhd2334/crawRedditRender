from flask import Flask, send_from_directory, jsonify
from crawler import RedditCrawler
import os
import threading

app = Flask(__name__)

SAVE_DIR = "data"
SQL_EXPORT = os.path.join(SAVE_DIR, "reddit_data.sql")

crawler = RedditCrawler()

@app.route("/")
def home():
    html = """
    <h2>📊 Reddit SQL Exporter</h2>
    <p>Hệ thống tự crawl và lưu dữ liệu Reddit vào file <b>reddit_data.sql</b>.</p>
    <a href='/download'>⬇️ Tải file SQL</a><br><br>
    <a href='/show'>👀 Xem 30 dòng cuối của file SQL</a>
    """
    return html

@app.route("/download")
def download_sql():
    if os.path.exists(SQL_EXPORT):
        return send_from_directory(SAVE_DIR, "reddit_data.sql", as_attachment=True)
    return jsonify({"error": "File SQL chưa được tạo."}), 404

@app.route("/show")
def show_sql():
    if not os.path.exists(SQL_EXPORT):
        return "<p>⚠️ Chưa có file SQL để hiển thị.</p>"
    with open(SQL_EXPORT, "r", encoding="utf-8") as f:
        lines = f.readlines()[-30:]
    return "<pre>" + "".join(lines) + "</pre>"

def run_crawler():
    crawler.fetch_users_from_subreddit()

# Chạy crawler ở thread riêng
threading.Thread(target=run_crawler, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
