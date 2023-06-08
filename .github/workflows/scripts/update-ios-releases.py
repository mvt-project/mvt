"""
Python script to download the Apple RSS feed and parse it.
"""

import json
import os
import urllib.request
from xml.dom.minidom import parseString

from packaging import version


def download_apple_rss(feed_url):
    with urllib.request.urlopen(feed_url) as f:
        rss_feed = f.read().decode("utf-8")
    print("Downloaded RSS feed from Apple.")
    return rss_feed


def parse_latest_ios_versions(rss_feed_text):
    latest_ios_versions = []

    parsed_feed = parseString(rss_feed_text)
    for item in parsed_feed.getElementsByTagName("item"):
        title = item.getElementsByTagName("title")[0].firstChild.data
        if not title.startswith("iOS"):
            continue

        import re

        build_match = re.match(
            r"iOS (?P<version>[\d\.]+) (?P<beta>beta )?(\S*)?\((?P<build>.*)\)", title
        )
        if not build_match:
            print("Could not parse iOS build:", title)
            continue

        release_info = build_match.groupdict()
        if release_info["beta"]:
            print("Skipping beta release:", title)
            continue

        release_info.pop("beta")
        latest_ios_versions.append(release_info)

    return latest_ios_versions


def update_mvt(mvt_checkout_path, latest_ios_versions):
    version_path = os.path.join(mvt_checkout_path, "mvt/ios/data/ios_versions.json")
    with open(version_path, "r") as version_file:
        current_versions = json.load(version_file)

    new_entry_count = 0
    for new_version in latest_ios_versions:
        for current_version in current_versions:
            if new_version["build"] == current_version["build"]:
                break
        else:
            # New version that does not exist in current data
            current_versions.append(new_version)
            new_entry_count += 1

    if not new_entry_count:
        print("No new iOS versions found.")
    else:
        print("Found {} new iOS versions.".format(new_entry_count))
        new_version_list = sorted(
            current_versions, key=lambda x: version.Version(x["version"])
        )
        with open(version_path, "w") as version_file:
            json.dump(new_version_list, version_file, indent=4)


def main():
    print("Downloading RSS feed...")
    mvt_checkout_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../../")
    )

    rss_feed = download_apple_rss(
        "https://developer.apple.com/news/releases/rss/releases.rss"
    )
    latest_ios_version = parse_latest_ios_versions(rss_feed)
    update_mvt(mvt_checkout_path, latest_ios_version)


if __name__ == "__main__":
    main()
