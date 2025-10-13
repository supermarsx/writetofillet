"""
\file _updates.py
\brief GitHub release update checking utilities.
"""

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def check_updates(repo_url: str, logger) -> int:
    """Check GitHub for the latest release and print the result.

    \param repo_url Repository HTML URL.
    \param logger Logger for warnings when network calls fail.
    \return 0 on success, non-zero on failure.
    """
    api = (
        repo_url.replace("https://github.com/", "https://api.github.com/repos/")
        + "/releases/latest"
    )
    try:
        req = Request(api, headers={"User-Agent": "writetofillet"})
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        tag = data.get("tag_name")
        html = data.get("html_url", repo_url + "/releases/latest")
        print(f"Latest tag: {tag}\nURL: {html}")
        return 0
    except (URLError, HTTPError, TimeoutError, json.JSONDecodeError) as e:
        logger.warning("update check failed: %s", e)
        print(repo_url + "/releases/latest")
        return 1
