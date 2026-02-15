import json
import logging
import re
import time
from html import unescape
from urllib.parse import quote

import requests
from utils.text_normalizer import normalize_menu_name

logger = logging.getLogger(__name__)

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover - optional dependency in local env
    BeautifulSoup = None


class NaverPlaceCrawler:
    """Crawl menu data from Naver Place pages."""

    BASE_URL = "https://pcmap.place.naver.com/restaurant/{place_id}/menu"
    HOME_URL = "https://pcmap.place.naver.com/restaurant/{place_id}/home"
    SEARCH_URL_TEMPLATES = [
        "https://map.naver.com/v5/search/{query}",
        "https://m.map.naver.com/search2/search.naver?query={query}",
    ]
    PLACE_ID_PATTERNS = [
        r"/restaurant/(\d+)",
        r"/entry/place/(\d+)",
        r"/place/(\d+)",
        r'"placeId"\s*:\s*"(\d{5,})"',
        r'"id"\s*:\s*"(\d{5,})"',
    ]

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    def __init__(self, delay: float = 0.4):
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def get_menus(self, place_id: str) -> list:
        """
        Crawl menu list from a Naver Place page.

        Returns:
            [{'name': str, 'price': int|None, 'is_representative': bool}, ...]
        """
        if not place_id:
            return []

        urls = [
            self.BASE_URL.format(place_id=place_id),
            self.HOME_URL.format(place_id=place_id),
        ]

        for url in urls:
            try:
                time.sleep(self.delay)
                response = self.session.get(url, timeout=10)
                if response.status_code != 200:
                    logger.warning("Naver Place returned %s for %s", response.status_code, place_id)
                    continue

                menus = self._extract_menus(response.text)
                if menus:
                    logger.info("Crawled %s menus from Naver Place %s", len(menus), place_id)
                    return menus
            except requests.RequestException as exc:
                logger.error("Naver Place crawl failed for %s: %s", place_id, exc)
            except Exception as exc:
                logger.error("Unexpected error crawling %s: %s", place_id, exc)

        return []

    def find_place_id(self, restaurant_name: str, address: str = "") -> str:
        """Find Naver place id by restaurant name/address when link is missing."""
        queries = self._build_lookup_queries(restaurant_name, address)
        for query in queries:
            encoded = quote(query, safe="")
            for template in self.SEARCH_URL_TEMPLATES:
                url = template.format(query=encoded)
                try:
                    time.sleep(self.delay / 2)
                    response = self.session.get(url, timeout=10)
                    if response.status_code != 200:
                        continue

                    place_id = self._extract_place_id_from_text(response.text)
                    if place_id:
                        return place_id
                except requests.RequestException:
                    continue
                except Exception:
                    continue

        return None

    def get_place_id_from_link(self, naver_link: str) -> str:
        """Extract place id from a Naver-related URL."""
        if not naver_link:
            return None

        patterns = [
            r"restaurant/(\d+)",
            r"entry/place/(\d+)",
            r"place/(\d+)",
            r"place_id=(\d+)",
            r"/(\d{8,})",
        ]

        for pattern in patterns:
            match = re.search(pattern, naver_link)
            if match:
                return match.group(1)

        return None

    def _extract_menus(self, html: str) -> list:
        rows = []

        if BeautifulSoup is not None:
            try:
                soup = BeautifulSoup(html, "html.parser")
                rows.extend(self._extract_menus_from_dom(soup))
                rows.extend(self._extract_menus_from_json_soup(soup))
            except Exception as exc:
                logger.debug("BeautifulSoup parse failed, fallback to regex parser: %s", exc)
        else:
            logger.info("beautifulsoup4 is missing. Using text-based menu parser fallback.")

        rows.extend(self._extract_menus_from_json_text(html))
        rows.extend(self._extract_menus_from_text(html))

        return self._dedupe_and_rank(rows)

    def _extract_menus_from_dom(self, soup) -> list:
        rows = []
        menu_items = soup.select(
            ".menu_item, .item_menu, [class*='menu'], li[class*='Menu'], div[class*='Menu']"
        )

        for item in menu_items:
            name_elem = item.select_one(".name, .menu_name, [class*='name']")
            price_elem = item.select_one(".price, .menu_price, [class*='price']")

            name = name_elem.get_text(strip=True) if name_elem else ""
            if not name:
                continue

            price_text = price_elem.get_text(strip=True) if price_elem else None
            rows.append({"name": name, "price": price_text})

        return rows

    def _extract_menus_from_json_soup(self, soup) -> list:
        rows = []
        script_nodes = []

        next_data = soup.find("script", id="__NEXT_DATA__")
        if next_data and next_data.string:
            script_nodes.append(next_data.string)

        for node in soup.find_all("script", {"type": "application/json"}):
            text = node.string or node.get_text(strip=False)
            if text:
                script_nodes.append(text)

        for text in script_nodes:
            rows.extend(self._extract_menus_from_json_blob(text))

        return rows

    def _extract_menus_from_json_text(self, html: str) -> list:
        rows = []
        patterns = [
            r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>',
            r"<script[^>]*type=\"application/json\"[^>]*>(.*?)</script>",
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, html, re.IGNORECASE | re.DOTALL):
                rows.extend(self._extract_menus_from_json_blob(match.group(1)))

        return rows

    def _extract_menus_from_json_blob(self, text: str) -> list:
        rows = []
        if not text:
            return rows

        text = unescape(text).strip()
        if not text:
            return rows

        try:
            payload = json.loads(text)
        except Exception:
            return rows

        self._walk_json(payload, rows)
        return rows

    def _walk_json(self, payload, rows):
        if isinstance(payload, dict):
            name = (
                payload.get("menuName")
                or payload.get("menuNm")
                or payload.get("name")
                or payload.get("title")
            )
            price = (
                payload.get("menuPrice")
                or payload.get("price")
                or payload.get("priceValue")
                or payload.get("amount")
            )
            if isinstance(price, dict):
                price = price.get("value") or price.get("price")

            if name:
                rows.append({"name": name, "price": price})

            for value in payload.values():
                self._walk_json(value, rows)
            return

        if isinstance(payload, list):
            for value in payload:
                self._walk_json(value, rows)

    def _extract_menus_from_text(self, html: str) -> list:
        rows = []
        patterns = [
            (
                r'"menu(?:Name|Nm|name)"\s*:\s*"([^"]{1,80})".{0,200}?"(?:menuPrice|price|amount)"\s*:\s*"?(\\?[\d,]{3,7})"?',
                re.IGNORECASE | re.DOTALL,
            ),
            (
                r'"name"\s*:\s*"([^"]{1,80})".{0,200}?"(?:menuPrice|price|amount)"\s*:\s*"?(\\?[\d,]{3,7})"?',
                re.IGNORECASE | re.DOTALL,
            ),
            (
                r'>([^<]{2,40})<.{0,80}?([\d,]{3,7})\s*원',
                re.IGNORECASE | re.DOTALL,
            ),
        ]

        for pattern, flags in patterns:
            for match in re.finditer(pattern, html, flags):
                rows.append({"name": match.group(1), "price": match.group(2)})

        return rows

    def _dedupe_and_rank(self, rows: list) -> list:
        deduped = []
        seen = set()

        for row in rows:
            name = self._normalize_menu_name(row.get("name", ""))
            if not self._is_valid_menu_name(name):
                continue

            price = self._parse_price(row.get("price"))
            key = (name, price)
            if key in seen:
                continue

            seen.add(key)
            deduped.append(
                {
                    "name": name,
                    "price": price,
                    "is_representative": False,
                }
            )

            if len(deduped) >= 30:
                break

        for row in deduped[:2]:
            row["is_representative"] = True

        return deduped

    def _build_lookup_queries(self, restaurant_name: str, address: str) -> list:
        name = (restaurant_name or "").strip()
        if not name:
            return []

        queries = []
        short_address = " ".join((address or "").split()[:3]).strip()
        if short_address:
            queries.append(f"{name} {short_address}")
        queries.append(name)

        normalized = re.sub(r"\s*[\(\[].*?[\)\]]", "", name).strip()
        if normalized and normalized != name:
            if short_address:
                queries.append(f"{normalized} {short_address}")
            queries.append(normalized)

        unique_queries = []
        for query in queries:
            compact = " ".join(query.split()).strip()
            if compact and compact not in unique_queries:
                unique_queries.append(compact)

        return unique_queries[:4]

    def _extract_place_id_from_text(self, text: str) -> str:
        for pattern in self.PLACE_ID_PATTERNS:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return None

    @staticmethod
    def _normalize_menu_name(name: str) -> str:
        return normalize_menu_name(name, fallback="")

    @staticmethod
    def _is_valid_menu_name(name: str) -> bool:
        if not name or len(name) < 2:
            return False

        invalid_tokens = {
            "메뉴",
            "대표",
            "전체",
            "더보기",
            "원산지",
            "공지",
            "이벤트",
            "바로가기",
        }
        if name in invalid_tokens:
            return False

        if name.isdigit():
            return False

        return True

    @staticmethod
    def _parse_price(raw_value):
        if raw_value is None:
            return None

        if isinstance(raw_value, (int, float)):
            value = int(raw_value)
            return value if value > 0 else None

        text = str(raw_value)
        number_chunks = re.findall(r"[\d,]+", text)
        if not number_chunks:
            return None

        try:
            value = int(number_chunks[0].replace(",", ""))
            if value <= 0:
                return None
            if value > 500000:
                return None
            return value
        except Exception:
            return None
