# focus_filter.py
# Returns one of: "whitelist", "blacklist", "unclassified"

from typing import Optional, Set
from urllib.parse import urlparse

WHITELIST_DOMAINS = {
    "khanacademy.org","coursera.org","edx.org","udemy.com",
    "ocw.mit.edu","mit.edu","brilliant.org",
    "wolframalpha.com","wikipedia.org","arxiv.org","gutenberg.org",
    "notion.so","obsidian.md","onenote.com","office.com",
    "docs.google.com","drive.google.com","sheets.google.com",
    "ankiweb.net","quizlet.com","pomofocus.io","forestapp.cc",
    "leetcode.com","hackerrank.com","codeforces.com",
    "geeksforgeeks.org","w3schools.com","developer.mozilla.org",
    "stackoverflow.com",
}

BLACKLIST_DOMAINS = {
    "reddit.com","tiktok.com","instagram.com","x.com","twitter.com",
    "netflix.com","disneyplus.com","hulu.com","twitch.tv",
    "pinterest.com","tumblr.com",
    "cnn.com","bbc.com","nytimes.com","theguardian.com",
}

SEARCH_ENGINE_DOMAINS = {
    "google.com","bing.com","duckduckgo.com","ddg.gg","search.yahoo.com","yandex.com",
}

WORK_TITLE_KEYWORDS = {
    "documentation","docs","api","mdn","w3schools",
    "leetcode","hackerrank","codeforces",
    "tutorial","course","lecture","assignment",
    "problem set","problem-set","arxiv","paper",
    "notion","obsidian","onenote","google docs","google sheets","drive",
    "quizlet","anki","pomofocus","forest",
    "wolfram","khan academy","ocw","brilliant","edx","coursera","udemy",
    "error","exception","stack overflow","stackoverflow",
}

NONWORK_TITLE_KEYWORDS = {
    "highlights","trailer","vlog","prank","meme","asmr","music video",
    "live stream","livestream","shorts","reaction","tier list",
    "tiktok","instagram","reddit","try not to","funny",
    "movie clip","behind the scenes","bts","gaming","let's play","lets play",
}

# --------- Helpers ---------
def _host(url: Optional[str]) -> str:
    if not url:
        return ""
    try:
        h = urlparse(url).netloc.lower()
        if h.startswith("www."):
            h = h[4:]
        return h
    except Exception:
        return ""

def _host_in(host: str, domset: Set[str]) -> bool:
    return any(host == d or host.endswith("." + d) for d in domset)

def _any_kw(s: str, kws: Set[str]) -> bool:
    s = (s or "").lower()
    return any(k in s for k in kws)

def classify(url: Optional[str] = None, title: Optional[str] = None) -> str:
    """
    Returns:
      label:  "whitelist" | "blacklist" | "unclassified"
      reason: brief reason for logging/UX

    Policy:
      1) If host ∈ WHITELIST_DOMAINS → whitelist.
      2) If host is YouTube → decide by TITLE keywords; if unclear → blacklist.
      3) If host ∈ BLACKLIST_DOMAINS → blacklist.
      4) If host ∈ SEARCH_ENGINE_DOMAINS → use title keywords; if unclear → unclassified.
      5) Else, use title keywords (work→whitelist, nonwork→blacklist).
      6) Default → whitelist (optimistic).
    """
    host = _host(url)
    t = (title or "").strip()

    # (1) Whitelist domains
    if host and _host_in(host, WHITELIST_DOMAINS):
        return "whitelist"

    # (2) YouTube special case
    if host and (host == "youtube.com" or host.endswith(".youtube.com")):
        if _any_kw(t, WORK_TITLE_KEYWORDS):
            return "whitelist"
        if _any_kw(t, NONWORK_TITLE_KEYWORDS):
            return "blacklist"
        return "blacklist"

    # (3) Pure blacklist domains
    if host and _host_in(host, BLACKLIST_DOMAINS):
        return "blacklist"

    # (4) Search engines → classify by title; else UNCLASSIFIED
    if host and _host_in(host, SEARCH_ENGINE_DOMAINS):
        if _any_kw(t, WORK_TITLE_KEYWORDS):
            return "whitelist"
        if _any_kw(t, NONWORK_TITLE_KEYWORDS):
            return "blacklist"
        return "unclassified"

    # (5) No decisive domain → fall back to title keywords globally
    if t:
        if _any_kw(t, WORK_TITLE_KEYWORDS):
            return "whitelist"
        if _any_kw(t, NONWORK_TITLE_KEYWORDS):
            return "blacklist"

    # (6) Default behavior (tune if you prefer strict)
    return "unclassified"
