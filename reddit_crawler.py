import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
import time
import os
import json

# ===== Cấu hình =====
CLIENT_ID = "_ZEYwc8FsUUF5MZipFMGzQ"
SECRET = "lyC23drNrBY9rQ-7EUlYIxpYjabQvQ"
USERNAME = "Creative-Umpire1404"
PASSWORD = "huyhd2334"
USER_AGENT = "RedditCrawler/1.0 by u/Creative-Umpire1404"

SAVE_DIR = "data"
MAX_AGE = 24*3600   # giữ 24 giờ
FETCH_DELAY = 5
CYCLE_DELAY = 90
SUBREDDIT = "all"  # chọn subreddit nhiều user post
MAX_USERS = 5

class RedditCrawler:
    def __init__(self):
        os.makedirs(SAVE_DIR, exist_ok=True)
        self.auth = HTTPBasicAuth(CLIENT_ID, SECRET)
        self.data = {"grant_type":"password", "username":USERNAME, "password":PASSWORD}
        self.token = None
        self.headers = None
        self.get_token()

    def log(self, msg):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{now}] {msg}")

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
                    self.log("Access token received.")
                    break
                else:
                    self.log(f"Token error {r.status_code}, retry 60s")
                    time.sleep(60)
            except Exception as e:
                self.log(f"Token exception: {e}, retry 30s")
                time.sleep(30)

    def fetch_user_content(self, username, kind="submitted", limit=1000):
        url = f"https://oauth.reddit.com/user/{username}/{kind}.json"
        all_items = []
        after = None
        while True:
            params = {"limit": 100}
            if after: params["after"] = after
            try:
                r = requests.get(url, headers=self.headers, params=params)
            except Exception as e:
                self.log(f"Error fetching {username}: {e}")
                break
            if r.status_code != 200:
                if r.status_code == 401:
                    self.get_token()
                    continue
                elif r.status_code == 404:
                    break
                else:
                    self.log(f"{r.status_code} error for {username}, retry 10s")
                    time.sleep(10)
                    continue
            data = r.json()["data"]
            children = data["children"]
            if not children: break
            all_items.extend(children)
            after = data.get("after")
            if not after or len(all_items) >= limit: break
        return all_items

    def save_user(self, username):
        # Xóa file quá tuổi
        for f in os.listdir(SAVE_DIR):
            path = os.path.join(SAVE_DIR, f)
            if os.path.isfile(path) and time.time() - os.path.getmtime(path) > MAX_AGE:
                os.remove(path)
        # Lấy data
        user_data = {
            "username": username,
            "posts": self.fetch_user_content(username, "submitted"),
            "comments": self.fetch_user_content(username, "comments")
        }
        file_path = os.path.join(SAVE_DIR, f"user_{username}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(user_data, f, ensure_ascii=False, indent=4)
        self.log(f"Saved user {username} → {file_path}")

    def fetch_users_from_subreddit(self):
        url = f"https://oauth.reddit.com/r/{SUBREDDIT}/new.json"
        users = set()
        while len(users) < MAX_USERS:
            try:
                r = requests.get(url, headers=self.headers, params={"limit":100})
            except Exception as e:
                self.log(f"Error fetching subreddit: {e}")
                time.sleep(10)
                continue
            if r.status_code != 200:
                self.log(f"{r.status_code} error on subreddit, retry 30s")
                time.sleep(30)
                continue
            for child in r.json()["data"]["children"]:
                author = child["data"]["author"]
                if author not in ("[deleted]", "AutoModerator") and author not in users:
                    users.add(author)
                    self.log(f"Found user: {author}")
                    self.save_user(author)
                    if len(users) >= MAX_USERS:
                        break
            time.sleep(FETCH_DELAY)
        self.log(f"Done fetching {len(users)} users!")

if __name__ == "__main__":
    crawler = RedditCrawler()
    while True:
        crawler.fetch_users_from_subreddit()
        time.sleep(CYCLE_DELAY)
