#!/usr/bin/env python3
"""Fetch public Kalshi market data.

This uses Kalshi's unauthenticated public market-data endpoints. Authenticated
portfolio or trading endpoints need API-key signing and are intentionally out of
scope for this first data spike.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BASE_URL = "https://external-api.kalshi.com/trade-api/v2"


def fetch_json(path: str, params: dict[str, str | int] | None = None) -> dict[str, Any]:
    query = f"?{urlencode(params)}" if params else ""
    request = Request(
        f"{BASE_URL}{path}{query}",
        headers={"Accept": "application/json", "User-Agent": "prediction-market/kalshi-spike"},
    )
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Kalshi returned HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach Kalshi: {exc.reason}") from exc


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch public Kalshi market data.")
    parser.add_argument("--limit", type=positive_int, default=10, help="Number of markets to fetch.")
    parser.add_argument("--status", default="open", help="Market status filter, e.g. open, closed, settled.")
    parser.add_argument("--series-ticker", help="Optional series ticker filter, e.g. KXHIGHNY.")
    parser.add_argument(
        "--mve-filter",
        choices=["only", "exclude"],
        default="exclude",
        help="Include only or exclude multivariate event markets.",
    )
    parser.add_argument("--orderbook", help="Optional market ticker to fetch orderbook data for.")
    parser.add_argument("--depth", type=int, default=5, help="Orderbook depth when --orderbook is supplied.")
    parser.add_argument("--output", type=Path, help="Optional path for the JSON response.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    params: dict[str, str | int] = {
        "limit": args.limit,
        "status": args.status,
        "mve_filter": args.mve_filter,
    }
    if args.series_ticker:
        params["series_ticker"] = args.series_ticker

    payload: dict[str, Any] = {
        "source": BASE_URL,
        "markets_response": fetch_json("/markets", params),
    }
    if args.orderbook:
        payload["orderbook_response"] = fetch_json(
            f"/markets/{args.orderbook}/orderbook",
            {"depth": args.depth},
        )

    formatted = json.dumps(payload, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(f"{formatted}\n", encoding="utf-8")
    else:
        print(formatted)

    market_count = len(payload["markets_response"].get("markets", []))
    print(f"Fetched {market_count} market(s).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
