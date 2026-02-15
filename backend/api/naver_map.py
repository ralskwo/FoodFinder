import concurrent.futures
import logging
import math
import re
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class NaverMapClient:
    """Client for Naver local search API with geocoding enrichment."""

    BASE_URL = "https://openapi.naver.com/v1/search/local.json"
    PAGE_SIZE = 5
    MAX_PAGE_STEPS = 20  # 5 * 20 = up to 100 items per query
    MAX_QUERY_VARIANTS = 8

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        geocoding_client_id: Optional[str] = None,
        geocoding_client_secret: Optional[str] = None,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.geocoding_client_id = geocoding_client_id
        self.geocoding_client_secret = geocoding_client_secret
        self.headers = {
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret,
        }

    def search_local(
        self,
        query: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius: int = 1000,
        display: int = 20,
        location_hint: Optional[str] = None,
        categories: Optional[List[str]] = None,
    ) -> List[Dict]:
        """Search places and enrich them with lat/lng via geocoding."""
        if not self.client_id or not self.client_secret:
            logger.warning("Naver client credentials are missing")
            return []

        normalized_query = (query or "음식점").strip() or "음식점"
        queries = self._build_queries(normalized_query, location_hint, categories)
        max_items = max(self.PAGE_SIZE, min(display, self.PAGE_SIZE * self.MAX_PAGE_STEPS))
        page_starts = range(1, self.PAGE_SIZE * self.MAX_PAGE_STEPS + 1, self.PAGE_SIZE)

        all_items: List[Dict] = []
        seen_keys = set()

        for query_text in queries:
            for start in page_starts:
                if len(all_items) >= max_items:
                    break

                items = self._search_page(
                    query_text,
                    start=start,
                    display=min(self.PAGE_SIZE, max_items - len(all_items)),
                )
                if not items:
                    break

                for item in items:
                    clean_title = self._clean_title(item.get("title", ""))
                    dedupe_key = (
                        f"{clean_title}_{item.get('address', '')}_{item.get('roadAddress', '')}"
                    )
                    if dedupe_key in seen_keys:
                        continue
                    seen_keys.add(dedupe_key)
                    all_items.append(item)

            if len(all_items) >= max_items:
                break

        if not all_items:
            return []

        from api.naver_geocoding import NaverGeocodingClient

        geocoder = NaverGeocodingClient(
            self.geocoding_client_id or "",
            self.geocoding_client_secret or "",
        )
        coord_cache: Dict[str, Optional[Dict]] = {}

        def convert_item(item: Dict) -> Dict:
            parsed = self._parse_item(item)
            address = parsed.get("road_address") or parsed.get("address")

            if address:
                coord = coord_cache.get(address)
                if coord is None and address not in coord_cache:
                    coord = geocoder.address_to_coord(address)
                    coord_cache[address] = coord

                if coord:
                    parsed["latitude"] = coord.get("latitude")
                    parsed["longitude"] = coord.get("longitude")

            return parsed

        results: List[Dict] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            future_to_item = {executor.submit(convert_item, item): item for item in all_items}
            for future in concurrent.futures.as_completed(future_to_item):
                try:
                    results.append(future.result())
                except Exception as exc:
                    logger.error("Failed to parse search item: %s", exc)

        if latitude is None or longitude is None:
            return results

        nearby = []
        fallback = []

        for result in results:
            lat = result.get("latitude")
            lng = result.get("longitude")

            if lat is None or lng is None:
                fallback.append(result)
                continue

            distance = self._distance_meters(latitude, longitude, lat, lng)
            result["distance"] = int(distance)

            if distance <= radius:
                nearby.append(result)
            else:
                fallback.append(result)

        if nearby:
            nearby.sort(key=lambda x: x.get("distance", 999999))
            return nearby

        # If radius filtering yields no candidates, return best-effort for caller-side filtering.
        fallback.sort(key=lambda x: x.get("distance", 999999))
        return fallback

    def _search_page(self, query: str, start: int, display: int) -> List[Dict]:
        params = {
            "query": query,
            "display": max(1, min(display, self.PAGE_SIZE)),
            "start": start,
            "sort": "sim",
        }

        try:
            response = requests.get(
                self.BASE_URL,
                headers=self.headers,
                params=params,
                timeout=7,
            )
            if response.status_code != 200:
                logger.warning(
                    "Naver local search failed: status=%s query=%s",
                    response.status_code,
                    query,
                )
                return []

            return response.json().get("items", [])
        except requests.exceptions.RequestException as exc:
            logger.error("Naver local search request failed: %s", exc)
            return []

    @staticmethod
    def _clean_title(title: str) -> str:
        return re.sub(r"<[^>]+>", "", title or "")

    @staticmethod
    def _normalize_location_hint(location_hint: Optional[str]) -> str:
        if not location_hint:
            return ""

        # Reduce long address strings to a concise local hint.
        tokens = [token for token in re.split(r"\s+", location_hint.strip()) if token]
        if not tokens:
            return ""

        return " ".join(tokens[:3])

    @staticmethod
    def _normalize_categories(categories: Optional[List[str]]) -> List[str]:
        if not categories:
            return []

        normalized = []
        for category in categories:
            value = (category or "").strip()
            if not value:
                continue
            if value in {"전체", "all"}:
                continue
            normalized.append(value)
        return normalized

    @classmethod
    def _append_query(cls, rows: List[str], value: str):
        query = " ".join(value.split()).strip()
        if not query:
            return
        if query in rows:
            return
        rows.append(query)

    def _build_queries(
        self,
        query: str,
        location_hint: Optional[str],
        categories: Optional[List[str]],
    ) -> List[str]:
        normalized_hint = self._normalize_location_hint(location_hint)
        normalized_categories = self._normalize_categories(categories)

        rows: List[str] = []

        if normalized_hint:
            self._append_query(rows, f"{normalized_hint} {query}")
        self._append_query(rows, query)

        for category in normalized_categories:
            if normalized_hint:
                self._append_query(rows, f"{normalized_hint} {category}")

            self._append_query(rows, category)

            if query != category:
                self._append_query(rows, f"{query} {category}")
                if normalized_hint:
                    self._append_query(rows, f"{normalized_hint} {query} {category}")

            if len(rows) >= self.MAX_QUERY_VARIANTS:
                break

        return rows[: self.MAX_QUERY_VARIANTS] or [query]

    @staticmethod
    def _distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        radius = 6371000

        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_phi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return radius * c

    def _parse_item(self, item: Dict) -> Dict:
        title = self._clean_title(item.get("title", ""))
        category_full = item.get("category", "")

        return {
            "title": title,
            "category": category_full,
            "address": item.get("address", ""),
            "road_address": item.get("roadAddress", ""),
            "telephone": item.get("telephone", ""),
            "link": item.get("link", ""),
            "latitude": None,
            "longitude": None,
        }
