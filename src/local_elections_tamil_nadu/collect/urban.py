"""Fetch the enumerated urban source packet; parsing is entirely offline."""

import csv
import json
from datetime import UTC, datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from local_elections_tamil_nadu.collect.fetch import ROOT, done, save

FRAME = ROOT / "data/manual/urban/sources.csv"


def collect():
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (research; in-rolls)"})
    retries = Retry(total=2, backoff_factor=2, status_forcelist=[429, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retries))
    log = ROOT / "data/search_log/urban/collect_attempts.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    with FRAME.open() as stream:
        for source in csv.DictReader(stream):
            if done(source["path"]):
                continue
            receipt = {
                "path": source["path"],
                "url": source["url"],
                "checked_at": datetime.now(UTC).isoformat(),
            }
            try:
                response = session.get(source["url"], timeout=(15, 60))
                receipt["status"] = response.status_code
                receipt["response_url"] = response.url
                response.raise_for_status()
                payload = response.content
                if source["format"] == "pdf" and not payload.startswith(b"%PDF"):
                    raise ValueError("Response is not a PDF")
                if source["format"] == "csv" and b"<html" in payload[:100].lower():
                    raise ValueError("Response is HTML, not CSV")
                if (ROOT / source["path"]).exists():
                    raise ValueError("Unlogged existing file; refusing to overwrite")
                path = save(
                    payload, source["path"], source["url"], response.status_code
                )
                receipt.update(saved_path=str(path.relative_to(ROOT)), ok=True)
            except (requests.RequestException, ValueError) as error:
                receipt.update(ok=False, error=str(error))
            with log.open("a") as stream:
                stream.write(json.dumps(receipt) + "\n")
            print(json.dumps(receipt), flush=True)


if __name__ == "__main__":
    collect()
