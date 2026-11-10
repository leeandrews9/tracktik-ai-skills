"""Read-only TrackTik REST client used by every skill in this repo.

    python tracktik_client.py            # checks auth and prints a few counts

Two modes:
  * LIVE      - set TT_BASE_URL, TT_USERNAME, TT_PASSWORD (+ TT_CLIENT_ID / TT_CLIENT_SECRET
                if your tenant issued them) in a .env file or the environment.
  * FIXTURES  - set TT_FIXTURES=<path to the repo's fixtures folder>. No tenant needed; the
                client reads synthetic JSON and applies the same filters locally. Use this to
                demo the skills or to develop without touching production data.

This client only ever sends HTTP GET. There is deliberately no post/patch/delete method.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

PAGE = 100            # TrackTik's max page size
MIN_INTERVAL = 0.25   # ~4 requests/second ceiling - be a good tenant citizen


def _load_dotenv() -> None:
    """Load a .env from the current directory or any parent (no dependency required)."""
    try:
        from dotenv import find_dotenv, load_dotenv
        load_dotenv(find_dotenv(usecwd=True))
        return
    except ImportError:
        pass
    for d in [Path.cwd(), *Path.cwd().parents]:
        f = d / ".env"
        if f.is_file():
            for line in f.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
            return


_load_dotenv()
TZ = ZoneInfo(os.getenv("TT_TZ", "America/Los_Angeles"))


# ---------------------------------------------------------------- time helpers
def epoch(day: str, end_of_day: bool = False) -> int:
    """'2026-09-01' -> epoch seconds at local midnight (or 23:59:59).

    TrackTik date filters only honour epoch seconds. ISO strings are SILENTLY IGNORED and
    you get the whole tenant back - see references/api-gotchas.md.
    """
    d = datetime.fromisoformat(day).replace(tzinfo=TZ)
    if end_of_day:
        d = d.replace(hour=23, minute=59, second=59)
    return int(d.timestamp())


def parse_dt(value) -> datetime | None:
    """TrackTik ISO-8601 string (or None) -> aware datetime."""
    if not value:
        return None
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def local(value) -> datetime | None:
    d = parse_dt(value)
    return d.astimezone(TZ) if d else None


def ref_id(value):
    """A relation can come back as an id or (with include=) as an object. Return the id."""
    return value.get("id") if isinstance(value, dict) else value


# ---------------------------------------------------------------- client
class TrackTik:
    def __init__(self):
        self.fixtures = os.getenv("TT_FIXTURES")
        self.requests = 0
        if self.fixtures:
            self.fx = Path(self.fixtures)
            meta = json.loads((self.fx / "_meta.json").read_text(encoding="utf-8"))
            self._now = datetime.fromisoformat(meta["now"]).astimezone(TZ)
            return
        import requests  # only needed in live mode
        base = os.getenv("TT_BASE_URL", "").rstrip("/")
        if not base or not os.getenv("TT_PASSWORD"):
            sys.exit("Set TT_BASE_URL / TT_USERNAME / TT_PASSWORD in .env (or TT_FIXTURES for demo mode).")
        self.base = base + os.getenv("TT_REST_PREFIX", "/rest/v1")
        self.token_url = os.getenv("TT_TOKEN_URL", base + "/rest/oauth2/access_token")
        self.sess = requests.Session()
        self._token, self._exp, self._last = None, 0.0, 0.0
        self._now = None

    # -- auth (password grant; token kept in memory only, never written to disk)
    def _header(self) -> dict:
        if not self._token or time.time() >= self._exp:
            data = {"grant_type": "password", "username": os.getenv("TT_USERNAME", ""),
                    "password": os.getenv("TT_PASSWORD", "")}
            for k, env in (("client_id", "TT_CLIENT_ID"), ("client_secret", "TT_CLIENT_SECRET")):
                if os.getenv(env):
                    data[k] = os.getenv(env)
            r = self.sess.post(self.token_url, data=data, timeout=30)
            if r.status_code != 200:
                sys.exit(f"Token request failed: HTTP {r.status_code} (check credentials / TT_TOKEN_URL)")
            p = r.json()
            self._token = p["access_token"]
            self._exp = time.time() + max(int(p.get("expires_in", 3600)) - 60, 30)
        return {"Authorization": f"Bearer {self._token}"}

    def now(self) -> datetime:
        """Current local time (in fixture mode: the dataset's 'now', so demos are repeatable)."""
        return self._now or datetime.now(TZ)

    # -- one GET
    def get(self, path: str, params: dict | None = None) -> tuple[int, dict]:
        if self.fixtures:
            return self._fixture_get(path, params or {})
        for attempt in range(4):
            wait = MIN_INTERVAL - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            r = self.sess.get(self.base + path, params=params or {}, headers=self._header(), timeout=90)
            self._last = time.monotonic()
            self.requests += 1
            if r.status_code in (429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(3 + 5 * attempt)
                continue
            try:
                return r.status_code, r.json()
            except ValueError:
                return r.status_code, {"_raw": r.text[:300]}
        return 599, {}

    def all(self, path: str, params: dict | None = None, max_rows: int | None = None) -> list[dict]:
        """Page a collection until meta.count. Warns if the result looks unfiltered."""
        rows, off, count = [], 0, None
        while True:
            st, body = self.get(path, {**(params or {}), "limit": PAGE, "offset": off})
            if st != 200:
                raise RuntimeError(f"GET {path} -> HTTP {st}: {json.dumps(body)[:300]}")
            data = body.get("data") or []
            count = (body.get("meta") or {}).get("count", count)
            rows.extend(data)
            off += len(data)
            if not data or (count is not None and off >= count) or (max_rows and len(rows) >= max_rows):
                return rows

    def count(self, path: str, params: dict | None = None) -> int | None:
        """meta.count for a filter, for the cost of one request."""
        st, body = self.get(path, {**(params or {}), "limit": 1})
        return (body.get("meta") or {}).get("count") if st == 200 else None

    def check_filter(self, path: str, params: dict, required: bool = False) -> None:
        """Guard against TrackTik silently ignoring a filter: if the filtered count equals the
        unfiltered count, the filter was probably dropped. Warns on stderr.
        Pass required=True for endpoints (like /reports) that reject unfiltered calls."""
        if required or self.fixtures:
            return
        a, b = self.count(path, params), self.count(path, {})
        if a is not None and a == b and a > PAGE:
            print(f"WARNING: filter on {path} returned the full collection ({a} rows) - "
                  f"it was probably ignored. Filter client-side.", file=sys.stderr)

    # -- fixture mode: same interface, local JSON
    def _fixture_get(self, path: str, params: dict) -> tuple[int, dict]:
        parts = path.strip("/").split("/")
        f = self.fx / f"{parts[0]}.json"
        if not f.exists():
            return 404, {"message": f"no fixture for {parts[0]}"}
        rows = json.loads(f.read_text(encoding="utf-8"))
        if len(parts) > 1:
            hit = [r for r in rows if str(r.get("id")) == parts[1]]
            return (200, {"data": hit[0]}) if hit else (404, {"message": "not found"})
        for key, val in params.items():
            if key in ("limit", "offset", "include", "fields", "sort", "includeInactive"):
                continue
            if key == "scope" and val == "HAS_INCIDENT":
                rows = [r for r in rows if r.get("reportFlag")]
            elif key.endswith((":gte", ":lte")):
                field, op = key.rsplit(":", 1)
                def ok(r):
                    d = parse_dt(r.get(field))
                    if d is None:
                        return False
                    return d.timestamp() >= int(val) if op == "gte" else d.timestamp() <= int(val)
                rows = [r for r in rows if ok(r)]
            else:
                rows = [r for r in rows if str(ref_id(r.get(key))) == str(val)]
        off, lim = int(params.get("offset", 0)), int(params.get("limit", PAGE))
        return 200, {"data": rows[off:off + lim], "meta": {"count": len(rows)}}


def window(tt: TrackTik, days: int) -> tuple[datetime, datetime]:
    end = tt.now()
    return end - timedelta(days=days), end


if __name__ == "__main__":
    tt = TrackTik()
    mode = f"FIXTURES ({tt.fixtures})" if tt.fixtures else f"LIVE ({tt.base})"
    st, me = tt.get("/accounts", {"limit": 1})
    print(f"Mode: {mode}")
    print("AUTH OK" if st == 200 else f"AUTH FAILED HTTP {st}: {str(me)[:200]}")
    if st == 200:
        print("accounts:", tt.count("/accounts", {"includeInactive": "true"}))
        print("employees (active):", tt.count("/employees"))
