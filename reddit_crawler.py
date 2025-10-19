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

MAX_USERS = 100          # Mỗi batch lấy 100 user
SUBREDDIT = "all"
FETCH_DELAY = 1          # Delay giữa các user

class RedditCrawler:
    def __init__(self):
        self.auth = HTTPBasicAuth(CLIENT_ID, SECRET)
        self.data = {"grant_type": "password", "username": USERNAME, "password": PASSWORD}
        self.token = None
        self.headers = None
        self.get_token()

    def log(self, msg):
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

    def get_token(self):
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

    def setup_database(self, db_path):
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.executescript("""
        CREATE TABLE IF NOT EXISTS r_user (
            username TEXT PRIMARY KEY,
            link_karma INTEGER,
            comment_karma INTEGER,
            created TEXT,
            premium INTEGER,
            verified_email INTEGER
        );
        CREATE TABLE IF NOT EXISTS post (
            id TEXT PRIMARY KEY,
            subreddit TEXT,
            title TEXT,
            content TEXT,
            p_url TEXT,
            score INTEGER,
            created TEXT,
            username TEXT,
            FOREIGN KEY (username) REFERENCES r_user(username)
        );
        CREATE TABLE IF NOT EXISTS comment (
            id TEXT PRIMARY KEY,
            body TEXT,
            subreddit TEXT,
            score INTEGER,
            created TEXT,
            username TEXT,
            FOREIGN KEY (username) REFERENCES r_user(username)
        );
        CREATE TABLE IF NOT EXISTS achievement (
            achievement_name TEXT PRIMARY KEY
        );
        CREATE TABLE IF NOT EXISTS user_achievement (
            username TEXT NOT NULL,
            achievement_name TEXT NOT NULL,
            PRIMARY KEY (username, achievement_name),
            FOREIGN KEY (username) REFERENCES r_user(username),
            FOREIGN KEY (achievement_name) REFERENCES achievement(achievement_name)
        );
        """)
        conn.commit()
        conn.close()

    def fetch_user_info(self, username):
        url = f"https://oauth.reddit.com/user/{username}/about"
        try:
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
        except:
            return None

    def fetch_user_content(self, username, kind="submitted", limit=50):
        url = f"https://oauth.reddit.com/user/{username}/{kind}.json"
        items, after = [], None
        while len(items) < limit:
            params = {"limit": 25}
            if after:
                params["after"] = after
            try:
                r = requests.get(url, headers=self.headers, params=params)
                if r.status_code != 200:
                    break
                data = r.json()["data"]
                for child in data["children"]:
                    d = child["data"]
                    if kind == "submitted":
                        items.append({
                            "id": d["id"], "subreddit": d["subreddit"],
                            "title": d["title"], "content": d.get("selftext", ""),
                            "p_url": f"https://reddit.com{d['permalink']}",
                            "score": d["score"], "created": datetime.utcfromtimestamp(d["created_utc"]).isoformat()
                        })
                    else:
                        items.append({
                            "id": d["id"], "body": d["body"], "subreddit": d["subreddit"],
                            "score": d["score"], "created": datetime.utcfromtimestamp(d["created_utc"]).isoformat()
                        })
                after = data.get("after")
                if not after:
                    break
            except:
                break
        return items

    def get_user_achievement(self, username, db_path):
        self.log(f"🔹 Lấy achievement của {username} ...")
        trophies_url = f"https://oauth.reddit.com/api/v1/user/{username}/trophies.json"
        while True:
            try:
                r = requests.get(trophies_url, headers=self.headers)
                if r.status_code != 200:
                    self.log(f"Lỗi {r.status_code} khi lấy achievement, đợi 60s")
                    if r.status_code == 401:
                        self.get_token()
                    time.sleep(60)
                    continue
                break
            except Exception as e:
                self.log(f"Exception khi lấy achievement: {e}, đợi 30s")
                time.sleep(30)

        trophies = r.json()["data"]["trophies"]

        if not trophies:
            self.log("  Không có achievement nào.")
            return

        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        for t in trophies:
            trophy_name = t["data"]["name"]
            try:
                cur.execute("INSERT OR IGNORE INTO achievement (achievement_name) VALUES (?)", (trophy_name,))
                cur.execute(
                    "INSERT OR IGNORE INTO user_achievement (username, achievement_name) VALUES (?, ?)",
                    (username, trophy_name)
                )
            except Exception as e:
                self.log(f"Lỗi lưu achievement: {e}")
        conn.commit()
        conn.close()
        self.log(f"✅ Lưu achievement cho {username} xong.")

    def save_user(self, username, db_path):
        self.log(f"🔍 Đang tải thông tin user: {username} ...")
        user = self.fetch_user_info(username)
        if not user:
            self.log(f"⚠️ Không thể lấy dữ liệu user: {username}")
            return

        posts = self.fetch_user_content(username, "submitted", 30)
        comments = self.fetch_user_content(username, "comments", 30)

        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO r_user VALUES (?, ?, ?, ?, ?, ?)
        """, (user["username"], user["link_karma"], user["comment_karma"],
              user["created"], user["premium"], user["verified_email"]))
        for p in posts:
            cur.execute("""
                INSERT OR REPLACE INTO post VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (p["id"], p["subreddit"], p["title"], p["content"], p["p_url"],
                  p["score"], p["created"], username))
        for c in comments:
            cur.execute("""
                INSERT OR REPLACE INTO comment VALUES (?, ?, ?, ?, ?, ?)
            """, (c["id"], c["body"], c["subreddit"], c["score"], c["created"], username))
        conn.commit()
        conn.close()

        # Lưu achievement sau khi lưu user xong
        self.get_user_achievement(username, db_path)

    def fetch_users_from_subreddit(self, save_dir):
        db_path = os.path.join(save_dir, f"reddit_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
        self.setup_database(db_path)
        self.log(f"📁 Tạo DB mới: {db_path}")

        user_count = 0
        url = f"https://oauth.reddit.com/r/{SUBREDDIT}/new.json"
        users = set()
        while len(users) < MAX_USERS:
            try:
                r = requests.get(url, headers=self.headers, params={"limit": 100})
                if r.status_code != 200:
                    self.log(f"Lỗi {r.status_code}, đợi 30s")
                    time.sleep(30)
                    continue
                for child in r.json()["data"]["children"]:
                    author = child["data"]["author"]
                    if author not in ("[deleted]", "AutoModerator") and author not in users:
                        users.add(author)
                        self.save_user(author, db_path)
                        user_count += 1
                        if len(users) >= MAX_USERS:
                            self.log(f"🎯 Hoàn thành crawl {len(users)} user.")
                            self.log(f"💾 Dữ liệu lưu trong {db_path}")
                            return
                time.sleep(FETCH_DELAY)
            except Exception as e:
                self.log(f"Exception khi crawl subreddit: {e}, đợi 30s")
                time.sleep(30)
