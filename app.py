from flask import Flask, send_from_directory
from apscheduler.schedulers.background import BackgroundScheduler
from reddit_crawler import RedditCrawler
from datetime import datetime, timedelta
import os
import threading

SAVE_DIR = "data"
DELETE_AFTER_HOURS = 6
os.makedirs(SAVE_DIR, exist_ok=True)

app = Flask(__name__)
crawler = RedditCrawler()

def cleanup_old_db():
    now = datetime.now()
    for f in os.listdir(SAVE_DIR):
        if f.endswith(".db"):
            path = os.path.join(SAVE_DIR, f)
            if now - datetime.fromtimestamp(os.path.getmtime(path)) > timedelta(hours=DELETE_AFTER_HOURS):
                os.remove(path)
                print(f"[{datetime.now()}] 🗑️ Xóa DB cũ: {f}", flush=True)

def start_first_batch():
    crawler.log("🚀 Bắt đầu crawl batch đầu tiên...")
    crawler.fetch_users_from_subreddit(SAVE_DIR)
    crawler.log("✅ Hoàn thành batch đầu tiên. Tiếp tục crawl theo lịch 5 phút/lần.")

threading.Thread(target=start_first_batch, daemon=True).start()

scheduler = BackgroundScheduler()
scheduler.add_job(lambda: crawler.fetch_users_from_subreddit(SAVE_DIR), 'interval', minutes=5)
scheduler.add_job(cleanup_old_db, 'interval', minutes=5)
scheduler.start()

@app.route("/")
def home():
    files = sorted([f for f in os.listdir(SAVE_DIR) if f.endswith(".db")], reverse=True)
    if not files:
        return "<h2>📊 Chưa có dữ liệu nào. Hệ thống đang khởi động...</h2>"
    file_links = "".join([f"<li>{f} <a href='/download/{f}'>⬇️ Download</a></li>" for f in files])
    return f"""
    <div style='text-align:center;'>
        <h2>📊 Reddit Data Exporter (.db)</h2>
        <ul style='list-style:none; padding-left:0;'>{file_links}</ul>
    </div>
    """

@app.route("/download/<filename>")
def download(filename):
    return send_from_directory(SAVE_DIR, filename, as_attachment=True)

# ===== Run Flask =====
if __name__ == "__main__":
    print(f"[{datetime.now()}] 🌐 Flask server đang chạy tại http://localhost:8080")
    app.run(host="0.0.0.0", port=8080)
