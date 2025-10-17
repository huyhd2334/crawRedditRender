from flask import Flask, send_from_directory, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from reddit_crawler import RedditCrawler
import os

SAVE_DIR = "data"
app = Flask(__name__)
crawler = RedditCrawler()

scheduler = BackgroundScheduler()
scheduler.add_job(crawler.fetch_users_from_subreddit, 'interval', minutes=4)   # crawl 50 user mỗi 4 phút
scheduler.add_job(crawler.export_sql, 'interval', hours=12)                    # xuất SQL mới mỗi 12 giờ
scheduler.start()

@app.route("/")
def home():
    html = """
    <div style='text-align:center;'>
        <h2>Reddit SQL Exporter</h2>
        <p>Hệ thống tự crawl và lưu dữ liệu Reddit.</p>
        <a href='/list_files'>Xem file SQL</a>
    </div>
    """
    return html

@app.route("/list_files")
def list_files():
    files = [f for f in os.listdir(SAVE_DIR) if f.endswith(".sql")]
    return jsonify(sorted(files, reverse=True))

@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory(SAVE_DIR, filename, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
