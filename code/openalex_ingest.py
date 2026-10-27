"""
OpenAlex ingest — pull metadata + abstracts for a discipline, reconstruct
abstract text, fingerprint + MinHash each work into the local index.

This is the "millions of papers on a 1 TB disk" trick from docs/01+07:
store metadata + abstract + fingerprints; NEVER bulk-store full text.
Full text is fetched on demand for suspected matches only (resolve_oa below).

Requires: pip install requests  (+ your fingerprint.py / minhash_index.py)
Run `python openalex_ingest.py --limit 2000` for a smoke pull.
Adapt into bi-plagiarism/backend/ingest/openalex.py.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import time

import requests

BASE = "https://api.openalex.org/works"
MAILTO = "you@college.ac.in"  # <- put your real address: joins OpenAlex's polite pool
PER_PAGE = 200

SCHEMA = """
CREATE TABLE IF NOT EXISTS works(
  oa_id TEXT PRIMARY KEY, title TEXT, doi TEXT, year INTEGER,
  venue TEXT, oa_url TEXT, abstract TEXT, ingested_at TEXT);
CREATE TABLE IF NOT EXISTS work_fingerprints(
  oa_id TEXT, hash INTEGER);          -- winnowing (pos,hash): hash is what matches
CREATE INDEX IF NOT EXISTS wf_hash ON work_fingerprints(hash);
"""


def abstract_from_inverted(inv: dict | None) -> str:
    """OpenAlex stores abstracts as {word: [positions]}. Rebuild the sentence."""
    if not inv:
        return ""
    pairs = sorted((pos, w) for w, poss in inv.items() for pos in poss)
    return " ".join(w for _, w in pairs)


def fetch_field(field_id: str = "fields/17", from_date: str = "2015-01-01",
                limit: int = 100_000) -> iter:
    """Cursor-paginated pull. fields/17 = Computer Science (see openalex.org/fields)."""
    cursor, got = "*", 0
    while got < limit:
        r = requests.get(
            BASE,
            params={
                "filter": f"from_publication_date:{from_date},primary_topic.field.id:{field_id}",
                "per-page": PER_PAGE,
                "cursor": cursor,
                "mailto": MAILTO,
                "select": "id,title,doi,publication_year,abstract_inverted_index,"
                          "open_access,primary_location",
            },
            timeout=60,
        )
        r.raise_for_status()
        body = r.json()
        for w in body.get("results", []):
            yield w
            got += 1
        cursor = body.get("meta", {}).get("next_cursor")
        if not cursor:
            break
        time.sleep(0.12)  # ~8 req/s: polite-pool safe


def ingest(db_path: str = "catalog.db", field_id: str = "fields/17",
           from_date: str = "2015-01-01", limit: int = 100_000) -> int:
    from fingerprint import K, fingerprint  # your local module

    db = sqlite3.connect(db_path)
    db.executescript(SCHEMA)
    n = 0
    for w in fetch_field(field_id, from_date, limit):
        oa_id = w["id"].rsplit("/", 1)[-1]
        abstract = abstract_from_inverted(w.get("abstract_inverted_index"))
        oa = w.get("open_access") or {}
        loc = w.get("primary_location") or {}
        src = (loc.get("source") or {}).get("display_name") if loc else None
        db.execute(
            "INSERT OR REPLACE INTO works VALUES (?,?,?,?,?,?,?,datetime('now'))",
            (oa_id, w.get("title"), w.get("doi"), w.get("publication_year"),
             src, oa.get("oa_url"), abstract),
        )
        if abstract:
            _, fps = fingerprint(abstract, K)
            db.executemany(
                "INSERT INTO work_fingerprints VALUES (?,?)", [(oa_id, h) for _, h in fps]
            )
        n += 1
        if n % 2000 == 0:
            db.commit()
            print(f"  {n} works ingested...")
    db.commit()
    db.close()
    return n


def resolve_oa(doi: str) -> str | None:
    """Fetch-on-demand resolver: legal free-PDF URL for a matched source.
    Only called AFTER a match — full text is never bulk-stored (docs/07)."""
    doi = (doi or "").replace("https://doi.org/", "")
    if not doi:
        return None
    try:
        r = requests.get(f"https://api.unpaywall.org/v2/{doi}",
                         params={"email": MAILTO}, timeout=30)
        r.raise_for_status()
        loc = r.json().get("best_oa_location") or {}
        return loc.get("url_for_pdf") or loc.get("url")
    except Exception:
        return None


def save_snapshot(db_path: str = "catalog.db", out: str = "works_snapshot.jsonl") -> int:
    db = sqlite3.connect(db_path)
    rows = db.execute("SELECT oa_id,title,doi,year,venue,oa_url,abstract FROM works")
    n = 0
    with open(out, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(dict(zip(
                ["oa_id", "title", "doi", "year", "venue", "oa_url", "abstract"], row)),
                ensure_ascii=False) + "\n")
            n += 1
    db.close()
    return n


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="catalog.db")
    ap.add_argument("--field", default="fields/17", help="OpenAlex field id (docs/07)")
    ap.add_argument("--from", dest="from_date", default="2015-01-01")
    ap.add_argument("--limit", type=int, default=2000, help="smoke-test default: 2000")
    args = ap.parse_args()
    n = ingest(args.db, args.field, args.from_date, args.limit)
    print(f"ingested {n} works into {args.db}")
    print("next: run minhash ingestion over the abstracts, then embed them (bge-m3)")
