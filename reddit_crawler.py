import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime, timezone, timedelta
import time
import os
import json

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account

# ---------------- CONFIG ----------------
CLIENT_ID = "YBWuJ69UdK3y80J9q71rUQ"
SECRET = "eukvQu10HoBCNS28yM5sbQvl-JVl6Q"
USERNAME = "Creative-Umpire1404"
PASSWORD = "huyhd2334"
USER_AGENT = "RedditCrawler/1.0 by u/Creative-Umpire1404"

SAVE_DIR = "data"
NUMBER_RETRY = 3

GDRIVE_CREDENTIALS = "gdrive_service.json"  # upload lên repo
GDRIVE_FOLDER_ID = "1-rUnQF8tpRYqMCNuYj8YehI70OSeMoEQ"   # folder ID trên Drive
# ----------------------------------------

os.makedirs(SAVE_DIR, exist_ok=True)

# Khởi tạo Google Drive service
creds = service_account.Credentials.from_service_account_file(GDRIVE_CREDENTIALS)
drive_service = build('drive', 'v3', credentials=creds)

def upload_to_drive(file_path, file_name):
    file_metadata = {"name": file_name, "parents": [GDRIVE_FOLDER_ID]}
    media = MediaFileUpload(file_path, mimetype="application/json")
    file = drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    print(f"Uploaded {file_name} → Drive (ID: {file['id']})")

class RedditCrawler:
    def __init__(self):
        self.__auth = HTTPBasicAuth(CLIENT_ID, SECRET)
        self.__data = {"grant_type": "password", "username": USERNAME, "password": PASSWORD}
        self._get_token()

    def _get_token(self):
        while True:
            try:
                res = requests.post(
                    "https://www.reddit.com/api/v1/access_token",
                    auth=self.__auth,
                    data=self.__data,
                    headers={"User-Agent": USER_AGENT}
                )
                if res.status_code == 200:
                    self.__token = res.json()["access_token"]
                    self.__headers = {"Authorization": f"bearer {self.__token}", "User-Agent": USER_AGENT}
                    break
                else:
                    print("Token error:", res.status_code)
            except Exception as e:
                print("Token error:", e)
            time.sleep(30)

    def _fetch_user_content(self, username, kind="submitted", limit=1000):
        url = f"https://oauth.reddit.com/user/{username}/{kind}.json"
        all_items = []
        after = None

        while True:
            params = {"limit": 100}
            if after:
                params["after"] = after
            try:
                r = requests.get(url, headers=self.__headers, params=params)
                if r.status_code != 200:
                    if r.status_code == 401:
                        self._get_token()
                    elif r.status_code == 404:
                        break
                    time.sleep(10)
                    continue
            except:
                break

            data = r.json()["data"]
            children = data["children"]
            if not children:
                break

            all_items.extend(children)
            after = data.get("after")
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

        upload_to_drive(file_path, f"user_{username}.json")

    def fetch_users_from_subreddit(self, max_users=5, subreddit="all"):
        url = f"https://oauth.reddit.com/r/{subreddit}/new.json"
        users = set()
        while len(users) < max_users:
            try:
                r = requests.get(url, headers=self.__headers, params={"limit": 100})
                if r.status_code != 200:
                    if r.status_code == 401:
                        self._get_token()
                    time.sleep(10)
                    continue
            except:
                time.sleep(10)
                continue

            for child in r.json()["data"]["children"]:
                author = child["data"]["author"]
                if author not in ("[deleted]", "AutoModerator") and author not in users:
                    users.add(author)
                    self.get_user_data(author)
                    if len(users) >= max_users:
                        break
            time.sleep(5)

if __name__ == "__main__":
    crawler = RedditCrawler()
    while True:
        crawler.fetch_users_from_subreddit(max_users=5)
        time.sleep(90)
