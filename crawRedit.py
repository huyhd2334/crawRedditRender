import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime, timedelta, timezone
import time
import os
import json
from termcolor import colored
import logging

CLIENT_ID = "YBWuJ69UdK3y80J9q71rUQ"
SECRET = "eukvQu10HoBCNS28yM5sbQvl-JVl6Q"
USERNAME = "Creative-Umpire1404"
PASSWORD = "huyhd2334"
USER_AGENT = "RedditCrawler/1.0 by u/Creative-Umpire1404"

SAVE_DIR = "data"
LOG_FILE = "logs/crawler.log"
NUMBER_RETRY = 3


class RedditCrawler:
    def __init__(self):
        os.makedirs(SAVE_DIR, exist_ok=True)
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

        logging.basicConfig(
            filename=LOG_FILE,
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        self.__auth = HTTPBasicAuth(CLIENT_ID, SECRET)
        self.__data = {"grant_type": "password", "username": USERNAME, "password": PASSWORD}
        self._get_token()
        self.__count_time_404 = 0

    def log(self, msg, level="info"):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prefix = colored(f"[{now_str}]", "yellow")

        if level == "error":
            print(prefix, colored(msg, "red"))
            logging.error(msg)
        else:
            print(prefix, colored(msg, "green"))
            logging.info(msg)

    def _get_token(self):
        while True:
            try:
                res = requests.post(
                    "https://www.reddit.com/api/v1/access_token",
                    auth=self.__auth,
                    data=self.__data,
                    headers={"User-Agent": USER_AGENT}
                )
                if res.status_code != 200:
                    self.log(f"Token error: {res.status_code}", "error")
                    time.sleep(60)
                    continue

                self.__token = res.json()["access_token"]
                self.__headers = {"Authorization": f"bearer {self.__token}", "User-Agent": USER_AGENT}
                self.log("Access token received.")
                break
            except Exception as e:
                self.log(f"Token error: {e}", "error")
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
            except Exception as e:
                self.log(e, "error")
                break

            if r.status_code != 200:
                self.log(f"{r.status_code} {r.text}", "error")
                if r.status_code == 401:
                    self._get_token()
                elif r.status_code == 404:
                    break
                time.sleep(10)
                continue

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
        self.log(f"Getting data of {username} ...")

        user_data = {
            "username": username,
            "posts": self._fetch_user_content(username, "submitted"),
            "comments": self._fetch_user_content(username, "comments"),
        }

        # Lưu JSON
        file_path = os.path.join(SAVE_DIR, f"user_{username}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(user_data, f, ensure_ascii=False, indent=4)

        self.log(f"Saved data for {username} → {file_path}")

    def fetch_users_from_subreddit(self, max_users=5, subreddit="all"):
        url = f"https://oauth.reddit.com/r/{subreddit}/new.json"
        users = set()

        while len(users) < max_users:
            try:
                r = requests.get(url, headers=self.__headers, params={"limit": 100})
            except Exception as e:
                self.log(e, "error")
                time.sleep(10)
                continue

            if r.status_code != 200:
                self.log(f"{r.status_code} {r.text}", "error")
                time.sleep(30)
                continue

            for child in r.json()["data"]["children"]:
                author = child["data"]["author"]
                if author not in ("[deleted]", "AutoModerator") and author not in users:
                    users.add(author)
                    self.get_user_data(author)
                    if len(users) >= max_users:
                        break

            time.sleep(5) 

        self.log(f"Done fetching {len(users)} users!")

if __name__ == "__main__":
    crawler = RedditCrawler()
    while True:
        crawler.fetch_users_from_subreddit(max_users=5)
        time.sleep(90)  # sleep trước khi crawl tiếp
