import hashlib
import logging
import math
from typing import Dict, List

from flask import Blueprint, jsonify, request

from api.naver_geocoding import NaverGeocodingClient
from api.naver_map import NaverMapClient
from config import Config
from database import db
from models.restaurant import Restaurant
from services.menu_service import MenuService
from utils.text_normalizer import normalize_menu_name

logger = logging.getLogger(__name__)

restaurant_bp = Blueprint("restaurant", __name__)
menu_service = MenuService()

_CATEGORY_ALIASES = {
    "한식": {"한식", "국밥", "찌개", "백반", "분식"},
    "중식": {"중식", "중국", "중국집", "짬뽕", "짜장", "마라"},
    "일식": {"일식", "일본식", "초밥", "스시", "라멘", "돈카츠", "돈까스"},
    "양식": {"양식", "파스타", "스테이크", "브런치"},
    "아시안": {"아시안", "동남아", "태국", "베트남", "인도", "쌀국수"},
    "치킨": {"치킨", "닭", "통닭", "후라이드"},
    "피자": {"피자"},
    "카페": {"카페", "디저트", "베이커리", "커피"},
    "회": {"회", "해산물", "초밥", "스시"},
    "고기": {"고기", "구이", "삼겹살", "갈비", "곱창"},
    "패스트푸드": {"패스트푸드", "햄버거", "버거", "샌드위치"},
    "족발": {"족발", "보쌈"},
}


def haversine_distance(lat1, lon1, lat2, lon2):
    """Return distance in meters between two WGS84 coordinates."""
    earth_radius = 6371000

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return earth_radius * c


def _build_place_id(item: dict) -> str:
    source_key = (
        item.get("link")
        or f"{item.get('title', '')}_{item.get('address', '')}_{item.get('road_address', '')}"
    )
    return hashlib.sha256(source_key.encode("utf-8", errors="ignore")).hexdigest()[:20]


def _normalize_text(value: str) -> str:
    return "".join((value or "").lower().split())


def _expand_category_terms(category: str) -> List[str]:
    value = (category or "").strip().lower()
    if not value:
        return []

    terms = {value}
    for alias_key, alias_values in _CATEGORY_ALIASES.items():
        if value in {alias_key.lower(), *{a.lower() for a in alias_values}}:
            terms |= {alias_key.lower(), *{a.lower() for a in alias_values}}
            break
    return list(terms)


def _matches_categories(item: Dict, categories: List[str]) -> bool:
    if not categories:
        return True

    category_text = _normalize_text(item.get("category", ""))
    title_text = _normalize_text(item.get("title", ""))
    haystack = f"{category_text} {title_text}"

    for selected in categories:
        for term in _expand_category_terms(selected):
            needle = _normalize_text(term)
            if needle and needle in haystack:
                return True

    return False


@restaurant_bp.route("/geocode/reverse", methods=["GET"])
def reverse_geocode():
    latitude = request.args.get("lat", type=float)
    longitude = request.args.get("lng", type=float) or request.args.get("lon", type=float)

    if latitude is None or longitude is None:
        return jsonify({"error": "lat and lng are required"}), 400

    geocoding_client = NaverGeocodingClient(
        Config.NAVER_CLOUD_ID,
        Config.NAVER_CLOUD_SECRET,
    )

    address = geocoding_client.coord_to_address(longitude, latitude)

    if address:
        return jsonify(
            {
                "address": address,
                "latitude": latitude,
                "longitude": longitude,
            }
        ), 200

    return jsonify(
        {
            "address": f"{latitude:.4f}, {longitude:.4f}",
            "latitude": latitude,
            "longitude": longitude,
        }
    ), 200


@restaurant_bp.route("/geocode", methods=["GET"])
def geocode_address():
    query = request.args.get("query")
    if not query:
        return jsonify({"error": "query is required"}), 400

    geocoding_client = NaverGeocodingClient(
        Config.NAVER_CLOUD_ID,
        Config.NAVER_CLOUD_SECRET,
    )

    result = geocoding_client.address_to_coord(query)
    if not result:
        return jsonify({"error": "Address not found"}), 404

    return jsonify(result), 200


@restaurant_bp.route("/restaurants/search", methods=["POST"])
def search_restaurants():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    lat = data.get("lat", data.get("latitude"))
    lng = data.get("lng", data.get("longitude"))
    if lat is None or lng is None:
        return jsonify({"error": "lat/lng are required"}), 400

    try:
        lat = float(lat)
        lng = float(lng)

        radius = int(data.get("radius", Config.DEFAULT_SEARCH_RADIUS))
        radius = max(Config.MIN_SEARCH_RADIUS, min(radius, Config.MAX_SEARCH_RADIUS))

        raw_budget = data.get("budget")
        budget = int(raw_budget) if raw_budget not in (None, "") else None

        budget_type = data.get("budget_type", data.get("budgetType", "menu"))
        categories = data.get("categories") or []
        if isinstance(categories, str):
            categories = [categories]
        categories = [value for value in categories if (value or "").strip()]

        query = (data.get("query") or "음식점").strip() or "음식점"
        location_hint = (
            data.get("location_hint")
            or data.get("locationHint")
            or data.get("address")
            or ""
        )
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid parameter values"}), 400

    logger.info(
        "Search restaurants query=%s lat=%s lng=%s radius=%s budget=%s categories=%s",
        query,
        lat,
        lng,
        radius,
        budget,
        categories,
    )

    naver_client = NaverMapClient(
        Config.NAVER_CLIENT_ID,
        Config.NAVER_CLIENT_SECRET,
        geocoding_client_id=Config.NAVER_CLOUD_ID,
        geocoding_client_secret=Config.NAVER_CLOUD_SECRET,
    )

    raw_results = naver_client.search_local(
        query=query,
        latitude=lat,
        longitude=lng,
        radius=radius,
        display=Config.MAX_SEARCH_RESULTS,
        location_hint=location_hint,
        categories=categories,
    )

    diagnostics = {
        "raw_candidates": len(raw_results),
        "within_radius": 0,
        "after_category": 0,
        "after_budget": 0,
        "missing_menu": 0,
    }

    results = []
    for item in raw_results:
        item_lat = item.get("latitude")
        item_lng = item.get("longitude")

        # Radius filtering is strict: unknown coordinates are excluded.
        if item_lat is None or item_lng is None:
            continue

        distance = haversine_distance(lat, lng, item_lat, item_lng)
        if distance > radius:
            continue

        item["distance"] = int(distance)
        diagnostics["within_radius"] += 1

        if not _matches_categories(item, categories):
            continue
        diagnostics["after_category"] += 1

        restaurant = get_or_create_restaurant(item)

        should_crawl_menus = budget is not None
        menus = menu_service.get_menus(
            restaurant,
            item.get("link"),
            allow_crawl=should_crawl_menus,
        )

        if budget is not None:
            if not menus:
                diagnostics["missing_menu"] += 1
                continue

            if budget_type == "average":
                prices = [menu.price for menu in menus if menu.price is not None]
                if not prices:
                    diagnostics["missing_menu"] += 1
                    continue
                average_price = sum(prices) / len(prices)
                if average_price > budget:
                    continue
            else:
                has_affordable = any(
                    menu.price is not None and menu.price <= budget for menu in menus
                )
                if not has_affordable:
                    continue

        diagnostics["after_budget"] += 1

        representative_menus = [
            {"name": normalize_menu_name(menu.name), "price": menu.price}
            for menu in menus
            if menu.is_representative
        ][:2]

        if not representative_menus and menus:
            priced_menus = sorted(
                [menu for menu in menus if menu.price is not None],
                key=lambda menu: menu.price,
            )
            representative_menus = [
                {"name": normalize_menu_name(menu.name), "price": menu.price}
                for menu in priced_menus[:2]
            ]

        results.append(
            {
                "place_id": restaurant.place_id,
                "name": item.get("title", restaurant.name),
                "title": item.get("title", restaurant.name),
                "category": item.get("category", ""),
                "address": item.get("address", ""),
                "road_address": item.get("road_address", ""),
                "latitude": item_lat,
                "longitude": item_lng,
                "distance": item.get("distance"),
                "phone": item.get("telephone", ""),
                "rating": restaurant.rating,
                "representative_menus": representative_menus,
                "link": item.get("link", ""),
            }
        )

    results.sort(key=lambda row: row.get("distance", 999999))

    logger.warning(
        "Search diagnostics: query=%s radius=%s budget=%s categories=%s raw=%s within_radius=%s after_category=%s after_budget=%s missing_menu=%s",
        query,
        radius,
        budget,
        categories,
        diagnostics["raw_candidates"],
        diagnostics["within_radius"],
        diagnostics["after_category"],
        diagnostics["after_budget"],
        diagnostics["missing_menu"],
    )

    return jsonify(
        {
            "results": results,
            "total": len(results),
            "count": len(results),
            "filters_applied": {
                "radius": radius,
                "budget": budget,
                "budget_type": budget_type if budget is not None else None,
                "categories": categories,
            },
            "diagnostics": diagnostics,
        }
    ), 200


def get_or_create_restaurant(item: dict) -> Restaurant:
    place_id = _build_place_id(item)

    restaurant = Restaurant.query.filter_by(place_id=place_id).first()
    if restaurant:
        return restaurant

    restaurant = Restaurant(
        place_id=place_id,
        name=item.get("title") or "Unknown",
        category=item.get("category", ""),
        address=item.get("address", ""),
        road_address=item.get("road_address", ""),
        latitude=item.get("latitude") or 0.0,
        longitude=item.get("longitude") or 0.0,
        phone=item.get("telephone", ""),
    )
    db.session.add(restaurant)

    try:
        db.session.commit()
        return restaurant
    except Exception:
        db.session.rollback()
        return Restaurant.query.filter_by(place_id=place_id).first()


@restaurant_bp.route("/restaurants/<place_id>", methods=["GET"])
def get_restaurant_detail(place_id):
    restaurant = Restaurant.query.filter_by(place_id=place_id).first()
    if not restaurant:
        return jsonify({"error": "Restaurant not found"}), 404

    return jsonify(restaurant.to_dict()), 200


@restaurant_bp.route("/restaurants/<place_id>/menus", methods=["GET"])
def get_restaurant_menus(place_id):
    restaurant = Restaurant.query.filter_by(place_id=place_id).first()
    if not restaurant:
        return jsonify({"error": "Restaurant not found"}), 404

    menus = menu_service.get_menus(restaurant, allow_crawl=True)

    return jsonify(
        {
            "restaurant_id": restaurant.id,
            "restaurant_name": restaurant.name,
            "menus": [menu.to_dict() for menu in menus],
        }
    ), 200


@restaurant_bp.route("/restaurants/<place_id>/menus/contribute", methods=["POST"])
def contribute_menu(place_id):
    data = request.get_json(silent=True)
    if not data or "menu_name" not in data:
        return jsonify({"error": "menu_name is required"}), 400

    restaurant = Restaurant.query.filter_by(place_id=place_id).first()
    if not restaurant:
        return jsonify({"error": "Restaurant not found"}), 404

    price = data.get("price")
    if price in ("", None):
        price = None
    else:
        try:
            price = int(price)
        except (TypeError, ValueError):
            return jsonify({"error": "price must be an integer"}), 400

    menu = menu_service.add_user_contribution(
        restaurant.id,
        data["menu_name"],
        price,
    )

    if not menu:
        return jsonify({"error": "Failed to add menu"}), 500

    return jsonify(menu.to_dict()), 201


@restaurant_bp.route("/restaurants/<place_id>/delivery", methods=["POST"])
def update_delivery_info(place_id):
    data = request.get_json(silent=True) or {}

    try:
        restaurant = Restaurant.query.filter_by(place_id=place_id).first()

        if not restaurant:
            restaurant = Restaurant(
                place_id=place_id,
                name=data.get("name", "Unknown"),
                latitude=float(data.get("latitude", 0.0)),
                longitude=float(data.get("longitude", 0.0)),
            )
            db.session.add(restaurant)

        if "delivery_fee" in data:
            restaurant.delivery_fee = data["delivery_fee"]
            restaurant.delivery_available = True

        if "minimum_order" in data:
            restaurant.minimum_order = data["minimum_order"]

        db.session.commit()
        return jsonify(restaurant.to_dict()), 200

    except Exception as exc:
        db.session.rollback()
        logger.error("Failed to update delivery info: %s", exc)
        return jsonify({"error": "Failed to update delivery info"}), 500


@restaurant_bp.route("/restaurants/nearby", methods=["GET"])
def nearby_restaurants():
    lat = request.args.get("lat", type=float)
    lng = request.args.get("lng", type=float) or request.args.get("lon", type=float)

    if lat is None or lng is None:
        return jsonify({"error": "lat and lng are required"}), 400

    radius = request.args.get("radius", default=3000, type=int)
    radius = max(Config.MIN_SEARCH_RADIUS, min(radius, Config.MAX_SEARCH_RADIUS))

    max_delivery_fee = request.args.get("max_delivery_fee", type=int)

    query = Restaurant.query
    if max_delivery_fee is not None:
        query = query.filter(
            Restaurant.delivery_fee.isnot(None),
            Restaurant.delivery_fee <= max_delivery_fee,
        )

    rows = []
    for restaurant in query.all():
        if restaurant.latitude is None or restaurant.longitude is None:
            continue

        distance = haversine_distance(lat, lng, restaurant.latitude, restaurant.longitude)
        if distance > radius:
            continue

        payload = restaurant.to_dict()
        payload["distance"] = int(distance)
        rows.append(payload)

    rows.sort(key=lambda row: row.get("distance", 999999))

    return jsonify(
        {
            "results": rows,
            "count": len(rows),
            "radius": radius,
            "max_delivery_fee": max_delivery_fee,
        }
    ), 200
