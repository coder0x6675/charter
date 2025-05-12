#!/usr/bin/env python
# Notifies subscribers of newly released TV-show episodes.

import os
import re
import sys
import time
import json
import signal

import feedparser
feedparser.USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"


DEBUG = False
PULL_INTERVAL = 120
WATCHLIST_FILE = "./watchlist.json"
SUBSCRIBER_DIRECTORY = "./subscribers"

REGEX_POSITION = r"S(\d+)E(\d+)"
REGEX_TITLE    = f"^(.+)({REGEX_POSITION})"
REGEX_POSITION = re.compile(REGEX_POSITION, re.IGNORECASE)
REGEX_TITLE    = re.compile(REGEX_TITLE, re.IGNORECASE)

is_scanning = True
should_exit = False

# Keeps track of subscribers: their email and watched shows
#subscribers = {"user-email": (show1, show2, show3)}
subscribers = {}

# Keeps track of all shows that are being subscribed on, and their position
#watchlist = (show1, show2, show3)
watchlist = set()


class Episode:

    def __init__(self, title, season=0, episode=0):
        self.title = title
        self.season = season
        self.episode = episode

    def __hash__(self):
        return hash(self.title)

    def __eq__(self, other):
        return self.title == other.title

    def __lt__(self, other):
        if self.title != other.title:
            raise ValueError("Comparison of two different shows is illegal")
        if self.season != other.season:
            return self.season < other.season
        else:
            return self.episode < other.episode

    def __str__(self):
        return f"{self.title.capitalize()} S{self.season:02d}E{self.episode:02d}"

    def __repr__(self):
        return f"{self.title.capitalize()} S{self.season:02d}E{self.episode:02d}"


def log_debug(text):
    if DEBUG:
        print(f"[?] {text}")

def log_info(text):
    print(f"[+] {text}")

def log_warning(text):
    print(f"[!] {text}", file=sys.stderr)

def log_error(text, exit_code=1):
    print(f"[-] {text}", file=sys.stderr)
    sys.exit(exit_code)


def set_get(set_t, item):
    if item not in set_t:
        return None
    for e in set_t:
        if e == item:
            return e

def set_add(set_t, item):
    set_t.discard(item)
    set_t.add(item)


def load_subscribers():
    if not os.path.exists(SUBSCRIBER_DIRECTORY):
        log_error(f"Directory '{SUBSCRIBER_DIRECTORY}' does not exist")
    for filename in os.listdir(SUBSCRIBER_DIRECTORY):
        filepath = os.path.join(SUBSCRIBER_DIRECTORY, filename)
        if not os.path.isfile(filepath):
            log_warning(f"Non-file entry present in subscriber-directory: {filename}")
        with open(filepath, "r") as fd:
            wishlist = set()
            for row in fd:
                row = row.strip()
                row = row.lower()
                if row    == "":
                    continue
                if row[0] == "#":
                    continue
                if not row.isalnum:
                    log_error(f"File {filename} contains invalid entry: {row}")
                wishlist.add(Episode(row))
            subscribers[filename] = wishlist

def load_watchlist():
    if not os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, "w") as fd:
            json.dump([], fd)
    with open(WATCHLIST_FILE, "r") as fd:
        try:
            memory = json.load(fd)
        except Exception:
            log_error(f"Could not load watchlist file: {WATCHLIST_FILE}")
    memory = [Episode(entry["title"], entry["season"], entry["episode"]) for entry in memory]
    for episode in memory:
        if episode in watchlist:
            set_add(watchlist, episode)
        else:
            log_warning(f"Removing show from watchlist: {episode}")

def save_watchlist():
    if DEBUG:
        log_debug("*Saving watchlist*")
        return
    json_episodes = [{"title": e.title, "season": e.season, "episode": e.episode} for e in watchlist]
    with open(WATCHLIST_FILE, "w") as fd:
        json.dump(json_episodes, fd)


def get_feed(debug=False):
    # Category to ID: https://torrentgalaxy.to/forums.php?action=viewtopic&topicid=138
    FEED_URL = "https://torrentgalaxy.to/rss.php?cat=5,9,11,28,41"
    if debug:
        with open("example_feed.rss", "r") as fd:
            feed = json.load(fd)
    else:
        feed = feedparser.parse(FEED_URL)
    episodes = []
    for entry in feed["entries"]:
        entry = extract_episode_data(entry["title"])
        if entry:
            episodes.append(Episode(entry[0], entry[1], entry[2]))
    return episodes

def extract_episode_data(feed_title):
    title = re.search(REGEX_TITLE, feed_title)
    if not title:
        return None
    title    = title.group(1).replace(".", " ").lower()
    position = re.search(REGEX_POSITION, feed_title)
    season   = int(position.group(1))
    episode  = int(position.group(2))
    return (title, season, episode)


def notify(email, episodes):
    EMAIL_SUBJECT = "FTJ! FTJ!"
    EMAIL_HEADER  = "Just released:"
    EMAIL_FOOTER  = "Enjoy!"
    str_episodes  = "\n".join([f"- {episode}" for episode in episodes])
    email_content = f"{EMAIL_HEADER}\n\n{str_episodes}\n\n{EMAIL_FOOTER}\n"
    email_command = f"echo 'Subject: {EMAIL_SUBJECT}\n\n{email_content}' | /usr/bin/msmtp '{email}'"
    if DEBUG:
        log_debug("*Running shell command*")
        print(f"{email_command}")
    else:
        os.system(email_command)
        pass


def exit_handler(signum, frame):
    global is_scanning, should_exit
    if is_scanning:
        should_exit = True
    else:
        sys.exit(0)


signal.signal(signal.SIGINT, exit_handler)
signal.signal(signal.SIGTERM, exit_handler)

load_subscribers()
watchlist.update(*subscribers.values())
load_watchlist()
save_watchlist()

for subscriber, wishlist in subscribers.items():
    log_info(f"Added subscriber {subscriber}: {wishlist}")
log_info(f"Compiled watchlist: {watchlist}")

log_info("Scanner started")
while True:

    is_scanning = True
    feed = get_feed(debug=DEBUG)

    new_episodes = set()
    for new_episode in feed:
        log_debug(f"New episode {new_episode}")
        known_episode = set_get(watchlist, new_episode)
        if known_episode and new_episode > known_episode:
            log_debug(f"New episode matches {known_episode}!")
            set_add(new_episodes, new_episode)
            set_add(watchlist, new_episode)

    if new_episodes:
        for user, wishlist in subscribers.items():
            new_user_episodes = [episode for episode in new_episodes if episode in wishlist]
            if new_user_episodes:
                log_info(f"Notifying {user}: {new_user_episodes}")
                notify(user, new_user_episodes)
        save_watchlist()

    if should_exit:
        sys.exit(0)
    is_scanning = False
    time.sleep(PULL_INTERVAL)

