"""Polite, resumable fetching with a receipt for every saved response.

Every kept response is written once under data/raw/ and logged in
data/raw/fetch_log.csv with its URL, sha256, size, HTTP status and UTC fetch
time. A path already in the log is never fetched again, so an interrupted run
resumes where it stopped and a rerun cannot silently replace a source.

tnsec.tn.gov.in refuses connections from outside India. Requests go through
the SOCKS5 proxy named by TN_PROXY (default socks5h://localhost:1080, an SSH
tunnel to a VM in Mumbai); set TN_PROXY="" to connect directly from India.

HTML bodies over GZIP_OVER bytes are stored gzipped (path ends .gz); the log
hashes the stored file, and `raw_sha256` hashes the body as served.
"""

import csv
import gzip
import hashlib
import logging
import os
import shutil
import time
from datetime import UTC, datetime
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw"
LOG = RAW / "fetch_log.csv"
FIELDS = [
    "path",
    "url",
    "method",
    "sha256",
    "bytes",
    "raw_sha256",
    "status",
    "fetched_at_utc",
]
HEADERS = {"User-Agent": "Mozilla/5.0 (research data collection; in-rolls)"}
PROXY = os.environ.get("TN_PROXY", "socks5h://localhost:1080")
GZIP_OVER = 1_000_000
DELAY = 2.0
# Stop rather than fill the disk (it filled once during collection, 2026-10-18).
MIN_FREE = 150_000_000

log = logging.getLogger("fetch")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def logged():
    if not LOG.exists():
        return {}
    with LOG.open(encoding="utf-8") as fh:
        return {row["path"]: row for row in csv.DictReader(fh)}


def session(proxy=True):
    s = requests.Session()
    s.headers.update(HEADERS)
    if proxy and PROXY:
        s.proxies = {"http": PROXY, "https": PROXY}
    return s


def setup_logging(logfile):
    logfile = ROOT / logfile
    logfile.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(logfile)],
    )


def contained(rel):
    """data/raw/<rel> resolved; refuse anything that would land outside data/raw/.

    Local names are partly built from server-supplied text (links, dropdown
    values), so a crafted "../" or absolute path must not escape.
    """
    path = (ROOT / rel).resolve()
    if not path.is_relative_to(RAW.resolve()):
        raise ValueError(f"refusing to write outside data/raw/: {rel!r}")
    return path


def save(content, rel, url, status, method="GET"):
    """Write a body (gzipped if large HTML) under data/raw and log it."""
    is_html = rel.endswith((".html", ".htm", ".json"))
    stored = content
    if is_html and len(content) > GZIP_OVER:
        rel += ".gz"
        stored = gzip.compress(content, mtime=0)
    path = contained(rel)
    path.parent.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(path.parent).free - len(stored) < MIN_FREE:
        raise OSError(f"less than {MIN_FREE:,} bytes would be free; not saving {rel}")
    path.write_bytes(stored)
    new = not LOG.exists()
    with LOG.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
        if new:
            writer.writeheader()
        writer.writerow(
            {
                "path": rel,
                "url": url,
                "method": method,
                "sha256": sha256(stored),
                "bytes": len(stored),
                "raw_sha256": sha256(content),
                "status": status,
                "fetched_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        )
    return path


def done(rel, held=None):
    held = logged() if held is None else held
    stored = any(r in held and (ROOT / r).exists() for r in (rel, rel + ".gz"))
    # a file over GitHub's size limit is committed as byte-split parts
    split = rel in held and any((ROOT / rel).parent.glob((ROOT / rel).name + ".part_*"))
    return stored or split


def request(s, url, method="GET", data=None, retries=6, timeout=120):
    """One request with exponential backoff on connection errors and 429/5xx."""
    for attempt in range(1, retries + 1):
        try:
            resp = s.request(method, url, data=data, timeout=timeout)
        except requests.RequestException as exc:
            wait = min(DELAY * 4**attempt, 600)
            log.warning("%s %s: %s; retry in %.0fs", method, url, exc, wait)
            if attempt == retries:
                raise
            time.sleep(wait)
            continue
        if resp.status_code == 429 or resp.status_code >= 500:
            wait = min(DELAY * 4**attempt, 600)
            log.warning("%s %s: HTTP %s; retry in %.0fs", method, url, resp, wait)
            time.sleep(wait)
            continue
        time.sleep(DELAY)
        return resp
    raise RuntimeError(f"gave up on {method} {url} after {retries} attempts")


def fetch(s, url, rel, method="GET", data=None, held=None, keep_404=False):
    """Save url to data/raw/<rel> unless already logged; return the path or None."""
    path = contained(rel)
    if done(rel, held):
        return path
    resp = request(s, url, method=method, data=data)
    if resp.status_code == 404 and not keep_404:
        log.info("404 %s", url)
        return None
    resp.raise_for_status()
    shown = url if data is None else f"{url} {data}"
    path = save(resp.content, rel, shown, resp.status_code, method)
    log.info("saved %s (%d bytes)", rel, len(resp.content))
    return path
