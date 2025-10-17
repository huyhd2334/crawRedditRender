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

# ===== Hàm xóa DB cũ =====
def cleanup_old_db(save_dir):
    now = datetime.now()
    for f in os.listdir(save_dir):
        if f.endswith(".db"):
            path = os.path.join(save_dir, f)
            if now - datetime.fromtimestamp(os.path.getmtime(path)) > timedelta(hours=DELETE_AFTER_HOURS):
                os.remove(path)
                print(f"[{datetime.now()}] 🗑️ Xóa file cũ: {f}", flush=True)

# ===== Thread crawl batch đầu tiên =====
def start_crawler():
    crawler.log("🚀 Bắt đầu crawl batch đầu tiên...")
    crawler.fetch_users_from_subreddit(SAVE_DIR)
    crawler.log("✅ Hoàn thành batch đầu tiên, tiếp tục chạy định kỳ mỗi 6h.")

threading.Thread(target=start_crawler, daemon=True).start()

# ===== Scheduler định kỳ =====
scheduler = BackgroundScheduler()
scheduler.add_job(lambda: crawler.fetch_users_from_subreddit(SAVE_DIR), 'interval', hours=6)
scheduler.add_job(lambda: cleanup_old_db(SAVE_DIR), 'interval', hours=1)
scheduler.start()

# ===== Flask Routes =====
@app.route("/")
def home():
    files = [f for f in os.listdir(SAVE_DIR) if f.endswith(".db")]
    files = sorted(files, reverse=True)
    if not files:
        return "<h2>📊 Chưa có dữ liệu nào được crawl. Hệ thống đang khởi động...</h2>"
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
