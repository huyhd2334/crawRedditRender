import requests
import time
import os
import json
from requests.auth import HTTPBasicAuth
from datetime import datetime, timezone, timedelta

# ---------------- Config Reddit ----------------
CLIENT_ID = "YOUR_CLIENT_ID"
SECRET = "YOUR_SECRET"
USERNAME = "YOUR_REDDIT_USERNAME"
PASSWORD = "YOUR_REDDIT_PASSWORD"
USER_AGENT = "RedditCrawler/1.0 by u/YOUR_REDDIT_USERNAME"

# ---------------- Folder lưu file ----------------
SAVE_DIR = "data"
os.makedirs(SAVE_DIR, exist_ok=True)

# ---------------- Crawler class ----------------
class RedditCrawler:
    def __init__(self):
        self.auth = HTTPBasicAuth(CLIENT_ID, SECRET)
        self.data = {
            "grant_type": "password",
            "username": USERNAME,
            "password": PASSWORD
        }
        self._get_token()

    def _get_token(self):
        while True:
            res = requests.post(
                "https://www.reddit.com/api/v1/access_token",
                auth=self.auth,
                data=self.data,
                headers={"User-Agent": USER_AGENT}
            )
            if res.status_code == 200:
                self.token = res.json()["access_token"]
                self.headers = {"Authorization": f"bearer {self.token}", "User-Agent": USER_AGENT}
                print("Access token received.")
                break
            else:
                print(f"Token error: {res.status_code}, retrying in 10s")
                time.sleep(10)

    def _fetch_user_content(self, username, kind="submitted", limit=100):
        url = f"https://oauth.reddit.com/user/{username}/{kind}.json"
        all_items = []
        after = None

        while True:
            params = {"limit": 100}
            if after:
                params["after"] = after

            r = requests.get(url, headers=self.headers, params=params)
            if r.status_code != 200:
                if r.status_code == 401:  # token hết hạn
                    self._get_token()
                    continue
                else:
                    break

            children = r.json()["data"]["children"]
            if not children:
                break

            all_items.extend(children)
            after = r.json()["data"].get("after")
            if not after or len(all_items) >= limit:
                break

        return all_items

    def get_user_data(self, username):
        user_data = {
            "username": username,
            "posts": self._fetch_user_content(username, "submitted"),
            "comments": self._fetch_user_content(username, "comments")
        }

        file_path = os.path.join(SAVE_DIR, f"user_{username}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(user_data, f, ensure_ascii=False, indent=4)
        print(f"Saved {username}.json")

    def fetch_users_from_subreddit(self, max_users=5, subreddit="all"):
        url = f"https://oauth.reddit.com/r/{subreddit}/new.json"
        users = set()

        while len(users) < max_users:
            r = requests.get(url, headers=self.headers, params={"limit": 100})
            if r.status_code != 200:
                time.sleep(10)
                continue

            for post in r.json()["data"]["children"]:
                author = post["data"]["author"]
                if author not in ("[deleted]", "AutoModerator") and author not in users:
                    users.add(author)
                    self.get_user_data(author)
                    if len(users) >= max_users:
                        break

            time.sleep(5)  # delay giữa các request

# ---------------- Main ----------------
if __name__ == "__main__":
    crawler = RedditCrawler()
    while True:
        crawler.fetch_users_from_subreddit(max_users=5)
        time.sleep(90)  # pause trước khi crawl tiếp
