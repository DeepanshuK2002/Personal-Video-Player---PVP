"""Smoke test for the Enma sidecar.

Starts `server.py` as a subprocess on a dedicated port, exercises every public
endpoint against the real upstream (nhentai official API v2), and asserts the
JSON contract the TypeScript adapter depends on. Run it with the sidecar venv:

    .venv\\Scripts\\python smoke.py

Exit code 0 = all checks passed. Requests are kept well inside the published
rate limits (1 search, 2 details, 1 list, 1 popular per run).
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

PORT = int(os.getenv("SMOKE_PORT", "8791"))
BASE = f"http://127.0.0.1:{PORT}"
HERE = os.path.dirname(os.path.abspath(__file__))

CHECKS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    CHECKS.append((name, ok, detail))
    print(f"  [{'ok' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def get(path: str, timeout: float = 30.0) -> tuple[int, dict]:
    try:
        with urllib.request.urlopen(BASE + path, timeout=timeout) as res:
            import json

            return res.status, json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        import json

        body = exc.read().decode("utf-8")
        try:
            return exc.code, json.loads(body)
        except ValueError:
            return exc.code, {"raw": body}
    except Exception as exc:  # noqa: BLE001
        return 0, {"error": type(exc).__name__, "message": str(exc)}


def main() -> int:
    env = {**os.environ, "ENMA_PORT": str(PORT), "ENMA_HOST": "127.0.0.1"}
    server = subprocess.Popen(
        [sys.executable, os.path.join(HERE, "server.py")],
        env=env,
        cwd=HERE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        # Wait for liveness.
        status, health = (0, {})
        for _ in range(60):
            status, health = get("/health", timeout=3)
            if status == 200:
                break
            time.sleep(0.5)
        check("health", status == 200 and health.get("ok") is True, str(health))
        if status != 200:
            return 1

        # Search (verified-working query syntax: `artist:` prefixes).
        status, search = get("/v1/search?query=artist%3Adr.bug&page=1")
        results = search.get("results") or []
        check(
            "search",
            status == 200 and search.get("source") == "nhentai" and len(results) > 0,
            f"n={len(results)} total={search.get('total')}",
        )
        if not results:
            return 1
        first = results[0]
        check(
            "search item shape",
            bool(first.get("id"))
            and bool(first.get("title"))
            and bool((first.get("cover") or {}).get("url", "").startswith("https://")),
            f"id={first.get('id')} cover={((first.get('cover') or {}).get('url'))[:60]}",
        )

        # Title detail (symbolic links -> chapters carry a link).
        title_id = first["id"]
        status, title = get(f"/v1/title/{title_id}")
        chapters = title.get("chapters") or []
        check(
            "title",
            status == 200 and title.get("id") == title_id and len(chapters) >= 1,
            f"chapters={len(chapters)} numPages={title.get('numPages')}",
        )
        check(
            "title metadata",
            bool(title.get("title", {}).get("english") or title.get("title", {}).get("pretty"))
            and isinstance(title.get("numFavorites"), int)
            and bool(title.get("genres")) and bool(title.get("tags")),
            f"authors={title.get('authors')} lang={title.get('language')}",
        )
        ch0 = chapters[0]
        check(
            "chapter shape",
            ch0.get("index") == 0 and ch0.get("number") == "1" and (ch0.get("pagesCount") or 0) > 0,
            f"number={ch0.get('number')} pagesCount={ch0.get('pagesCount')}",
        )

        # Pages (CDN image URLs; verified reachable without referer).
        status, pages = get(f"/v1/title/{title_id}/chapters/0/pages")
        page_list = pages.get("pages") or []
        first_url = (page_list[0] or {}).get("url", "") if page_list else ""
        check(
            "pages",
            status == 200 and len(page_list) > 0 and first_url.startswith("https://i"),
            f"n={len(page_list)} first={first_url}",
        )
        if page_list:
            # Spot-check that the first page URL actually serves bytes.
            try:
                with urllib.request.urlopen(first_url, timeout=20) as res:
                    head = res.read(64)
                check("page bytes", res.status == 200 and len(head) > 0, f"{res.status}")
            except Exception as exc:  # noqa: BLE001
                check("page bytes", False, str(exc))

        # Newest listing + official popular list.
        status, listing = get("/v1/list?page=1")
        check(
            "list",
            status == 200 and len(listing.get("results") or []) > 0,
            f"n={len(listing.get('results') or [])} total={listing.get('total')}",
        )
        status, popular = get("/v1/popular")
        check(
            "popular",
            status == 200 and len(popular.get("results") or []) > 0,
            f"n={len(popular.get('results') or [])}",
        )

        # Error contract: unknown title -> 404 with {error, message}.
        status, err = get("/v1/title/999999999")
        check(
            "not found",
            status == 404 and bool(err.get("error")),
            f"status={status} error={err.get('error')}",
        )
        # Validation contract: page=0 -> 4xx (422 from FastAPI validation).
        status, _ = get("/v1/list?page=0")
        check("validation", 400 <= status < 500, f"status={status}")

        failed = [name for name, ok, _ in CHECKS if not ok]
        print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
        if failed:
            print("failed: " + ", ".join(failed))
        return 1 if failed else 0
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    raise SystemExit(main())
