from flask import Flask, send_from_directory
from apscheduler.schedulers.background import BackgroundScheduler
from reddit_crawler import RedditCrawler
import os
import threading

SAVE_DIR = "data"
os.makedirs(SAVE_DIR, exist_ok=True)

app = Flask(__name__)
crawler = RedditCrawler()

# 🔄 Scheduler chạy định kỳ
scheduler = BackgroundScheduler()
scheduler.add_job(crawler.fetch_users_from_subreddit, 'interval', hours=6)
scheduler.start()

# 🚀 Thread chạy crawler ngay khi khởi động Flask
def start_crawler():
    crawler.log("🚀 Bắt đầu chạy crawler ban đầu...")
    crawler.fetch_users_from_subreddit()
    crawler.log("✅ Hoàn thành crawl ban đầu, tiếp tục chạy định kỳ mỗi 6h.")

threading.Thread(target=start_crawler, daemon=True).start()

# ==================== Flask Routes ====================

@app.route("/")
def home():
    files = [f for f in os.listdir(SAVE_DIR) if f.endswith(".db")]
    files = sorted(files, reverse=True)

    if not files:
        return """
        <div style='text-align:center;'>
            <h2>📊 Reddit Data Exporter (.db)</h2>
            <p>Chưa có dữ liệu nào được crawl. Hệ thống đang khởi động...</p>
        </div>
        """

    file_links = "".join([
        f"<li>{f} <a href='/download/{f}' style='margin-left:10px;'>⬇️ Download</a></li>"
        for f in files
    ])

    return f"""
    <div style='text-align:center;'>
        <h2>📊 Reddit Data Exporter (.db)</h2>
        <p>Tự động crawl và lưu dữ liệu người dùng Reddit.</p>
        <ul style='list-style:none; padding-left:0;'>{file_links}</ul>
    </div>
    """

@app.route("/download/<filename>")
def download(filename):
    return send_from_directory(SAVE_DIR, filename, as_attachment=True)

# ======================================================

if __name__ == "__main__":
    print("🌐 Flask server is running at http://localhost:8080")
    print("🧠 Crawler sẽ tự chạy song song và log kết quả tại đây:\n")
    app.run(host="0.0.0.0", port=8080)
