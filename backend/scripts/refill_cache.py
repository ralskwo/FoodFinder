import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app import create_app
from database import db
from models.menu import Menu
from models.restaurant import Restaurant


def _build_payloads(
    lat: float,
    lng: float,
    radius: int,
    budgets: List[int],
) -> List[Dict]:
    categories = ["한식", "중식", "일식", "양식", "치킨", "피자", "카페", "고기"]

    payloads = [
        {
            "lat": lat,
            "lng": lng,
            "radius": radius,
            "query": "음식점",
            "categories": [],
        }
    ]

    for category in categories:
        payloads.append(
            {
                "lat": lat,
                "lng": lng,
                "radius": radius,
                "query": category,
                "categories": [category],
            }
        )

    for budget in budgets:
        payloads.append(
            {
                "lat": lat,
                "lng": lng,
                "radius": radius,
                "query": "음식점",
                "budget": budget,
                "budgetType": "menu",
                "categories": [],
            }
        )

    return payloads


def _request_search(client, payload: Dict) -> Dict:
    response = client.post("/api/restaurants/search", json=payload)
    data = response.get_json(silent=True) or {}
    return {
        "status": response.status_code,
        "count": data.get("count", 0),
        "diagnostics": data.get("diagnostics") or {},
        "query": payload.get("query"),
        "categories": payload.get("categories") or [],
        "budget": payload.get("budget"),
    }


def _print_result(index: int, result: Dict):
    diagnostics = result["diagnostics"]
    print(
        f"[{index:02d}] status={result['status']} query={result['query']} "
        f"categories={result['categories']} budget={result['budget']} "
        f"count={result['count']} diagnostics={json.dumps(diagnostics, ensure_ascii=False)}"
    )


def _print_db_snapshot():
    restaurant_count = Restaurant.query.count()
    menu_count = Menu.query.count()
    priced_menu_count = Menu.query.filter(Menu.price.isnot(None)).count()

    print("---- DB Snapshot ----")
    print(f"restaurants={restaurant_count}")
    print(f"menus={menu_count}")
    print(f"menus_with_price={priced_menu_count}")


def run_refill(lat: float, lng: float, radius: int, budgets: List[int]):
    app = create_app({"TESTING": True})
    client = app.test_client()
    payloads = _build_payloads(lat, lng, radius, budgets)

    with app.app_context():
        total_count = 0
        for index, payload in enumerate(payloads, 1):
            result = _request_search(client, payload)
            _print_result(index, result)
            total_count += int(result["count"] or 0)

        print("---------------------")
        print(f"total_result_count_from_requests={total_count}")
        _print_db_snapshot()

        db.session.remove()


def _parse_args():
    parser = argparse.ArgumentParser(description="Warm up FoodFinder DB cache.")
    parser.add_argument("--lat", type=float, default=37.5665, help="Latitude")
    parser.add_argument("--lng", type=float, default=126.9780, help="Longitude")
    parser.add_argument("--radius", type=int, default=3000, help="Search radius in meters")
    parser.add_argument(
        "--budgets",
        type=str,
        default="10000,17000,25000",
        help="Comma-separated menu budget list",
    )
    return parser.parse_args()


def _parse_budgets(raw: str) -> List[int]:
    rows: List[int] = []
    for chunk in (raw or "").split(","):
        value = chunk.strip()
        if not value:
            continue
        try:
            rows.append(int(value))
        except ValueError:
            continue
    return rows


if __name__ == "__main__":
    args = _parse_args()
    budgets = _parse_budgets(args.budgets)
    run_refill(args.lat, args.lng, args.radius, budgets)
