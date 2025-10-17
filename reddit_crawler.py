import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
import time
import os
import sqlite3

# ===== Cấu hình =====
CLIENT_ID = "_ZEYwc8FsUUF5MZipFMGzQ"
SECRET = "lyC23drNrBY9rQ-7EUlYIxpYjabQvQ"
USERNAME = "Creative-Umpire1404"
PASSWORD = "huyhd2334"
USER_AGENT = "RedditCrawler/1.0 by u/Creative-Umpire1404"

SAVE_DIR = "data"
DB_PATH = os.path.join(SAVE_DIR, "reddit_data.db")
SQL_EXPORT = os.path.join(SAVE_DIR, "reddit_data.sql")

MAX_USERS = 50
SUBREDDIT = "all"
FETCH_DELAY = 5
CYCLE_DELAY = 90


class RedditCrawler:
    def __init__(self):
        os.makedirs(SAVE_DIR, exist_ok=True)
        self.auth = HTTPBasicAuth(CLIENT_ID, SECRET)
        self.data = {"grant_type": "password", "username": USERNAME, "password": PASSWORD}
        self.token = None
        self.headers = None
        self.get_token()
        self.setup_database()

    def log(self, msg):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{now}] {msg}")

    def get_token(self):
        """Lấy access token từ Reddit API"""
        while True:
            try:
                r = requests.post(
                    "https://www.reddit.com/api/v1/access_token",
                    auth=self.auth,
                    data=self.data,
                    headers={"User-Agent": USER_AGENT}
                )
                if r.status_code == 200:
                    self.token = r.json()["access_token"]
                    self.headers = {"Authorization": f"bearer {self.token}", "User-Agent": USER_AGENT}
                    self.log("✅ Access token received.")
                    break
                else:
                    self.log(f"Token error {r.status_code}, retry 60s")
                    time.sleep(60)
            except Exception as e:
                self.log(f"Token exception: {e}, retry 30s")
                time.sleep(30)

    def setup_database(self):
        """Tạo 4 bảng chính"""
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        cur.executescript("""
        CREATE TABLE IF NOT EXISTS r_user (
            username TEXT PRIMARY KEY,
            link_karma INTEGER NOT NULL,
            comment_karma INTEGER NOT NULL,
            created TEXT NOT NULL,
            premium INTEGER NOT NULL,
            verified_email INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS post (
            id TEXT PRIMARY KEY,
            subreddit TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT,
            p_url TEXT NOT NULL,
            score INTEGER NOT NULL,
            created TEXT NOT NULL,
            username TEXT NOT NULL,
            FOREIGN KEY (username) REFERENCES r_user(username)
        );

        CREATE TABLE IF NOT EXISTS comment (
            id TEXT PRIMARY KEY,
            body TEXT NOT NULL,
            subreddit TEXT NOT NULL,
            score INTEGER NOT NULL,
            created TEXT NOT NULL,
            username TEXT NOT NULL,
            FOREIGN KEY (username) REFERENCES r_user(username)
        );

        CREATE TABLE IF NOT EXISTS achievement (
            username TEXT NOT NULL,
            achievement_name TEXT NOT NULL,
            PRIMARY KEY (username, achievement_name),
            FOREIGN KEY (username) REFERENCES r_user(username)
        );
        """)
        conn.commit()
        conn.close()

    def fetch_user_info(self, username):
        """Lấy thông tin user"""
        url = f"https://oauth.reddit.com/user/{username}/about"
        r = requests.get(url, headers=self.headers)
        if r.status_code != 200:
            return None
        d = r.json()["data"]
        return {
            "username": d["name"],
            "link_karma": d.get("link_karma", 0),
            "comment_karma": d.get("comment_karma", 0),
            "created": datetime.utcfromtimestamp(d["created_utc"]).isoformat(),
            "premium": int(d.get("is_gold", False)),
            "verified_email": int(d.get("has_verified_email", False))
        }

    def fetch_user_content(self, username, kind="submitted", limit=50):
        """Lấy bài post hoặc comment"""
        url = f"https://oauth.reddit.com/user/{username}/{kind}.json"
        items = []
        after = None
        while len(items) < limit:
            params = {"limit": 25}
            if after:
                params["after"] = after
            r = requests.get(url, headers=self.headers, params=params)
            if r.status_code != 200:
                break
            data = r.json()["data"]
            for child in data["children"]:
                d = child["data"]
                if kind == "submitted":
                    items.append({
                        "id": d["id"],
                        "subreddit": d["subreddit"],
                        "title": d["title"],
                        "content": d.get("selftext", ""),
                        "p_url": f"https://reddit.com{d['permalink']}",
                        "score": d["score"],
                        "created": datetime.utcfromtimestamp(d["created_utc"]).isoformat(),
                    })
                else:
                    items.append({
                        "id": d["id"],
                        "body": d["body"],
                        "subreddit": d["subreddit"],
                        "score": d["score"],
                        "created": datetime.utcfromtimestamp(d["created_utc"]).isoformat(),
                    })
            after = data.get("after")
            if not after:
                break
        return items

    def save_user(self, username):
        """Lưu user + post + comment"""
        user = self.fetch_user_info(username)
        if not user:
            return

        posts = self.fetch_user_content(username, "submitted", 30)
        comments = self.fetch_user_content(username, "comments", 30)

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        # user
        cur.execute("""
            INSERT OR REPLACE INTO r_user (username, link_karma, comment_karma, created, premium, verified_email)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            user["username"], user["link_karma"], user["comment_karma"],
            user["created"], user["premium"], user["verified_email"]
        ))

        # posts
        for p in posts:
            cur.execute("""
                INSERT OR REPLACE INTO post (id, subreddit, title, content, p_url, score, created, username)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (p["id"], p["subreddit"], p["title"], p["content"], p["p_url"],
                  p["score"], p["created"], username))

        # comments
        for c in comments:
            cur.execute("""
                INSERT OR REPLACE INTO comment (id, body, subreddit, score, created, username)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (c["id"], c["body"], c["subreddit"], c["score"], c["created"], username))

        conn.commit()
        conn.close()
        self.log(f"Đã lưu user {username}")

    def export_sql(self):
        """Xuất database thành file .sql"""
        conn = sqlite3.connect(DB_PATH)
        with open(SQL_EXPORT, "w", encoding="utf-8") as f:
            for line in conn.iterdump():
                f.write(f"{line}\n")
        conn.close()
        self.log(f"📦 Đã xuất file SQL: {SQL_EXPORT}")

    def fetch_users_from_subreddit(self):
        """Crawl user từ subreddit"""
        url = f"https://oauth.reddit.com/r/{SUBREDDIT}/new.json"
        users = set()

        while len(users) < MAX_USERS:
            try:
                r = requests.get(url, headers=self.headers, params={"limit": 100})
            except Exception as e:
                self.log(f"Lỗi khi tải subreddit: {e}")
                time.sleep(10)
                continue

            if r.status_code != 200:
                self.log(f"Lỗi {r.status_code}, chờ 30s")
                time.sleep(30)
                continue

            for child in r.json()["data"]["children"]:
                author = child["data"]["author"]
                if author not in ("[deleted]", "AutoModerator") and author not in users:
                    users.add(author)
                    self.log(f"Đang crawl user: {author}")
                    self.save_user(author)
                    if len(users) >= MAX_USERS:
                        break
            time.sleep(FETCH_DELAY)

        self.export_sql()
        self.log(f"✅ Hoàn thành crawl {len(users)} users.")
