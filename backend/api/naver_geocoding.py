import logging
from typing import Dict, Optional

import requests

logger = logging.getLogger(__name__)


class NaverGeocodingClient:
    """Client for Naver Maps geocoding APIs with OSM fallback."""

    REVERSE_GEOCODING_URLS = (
        "https://maps.apigw.ntruss.com/map-reversegeocode/v2/gc",
        "https://naveropenapi.apigw.ntruss.com/map-reversegeocode/v2/gc",
    )
    GEOCODING_URLS = (
        "https://maps.apigw.ntruss.com/map-geocode/v2/geocode",
        "https://naveropenapi.apigw.ntruss.com/map-geocode/v2/geocode",
        "https://naveropenapi.apigw.ntruss.com/map-geocoding/v2/geocode",
    )
    TIMEOUT_SECONDS = 10
    OSM_TIMEOUT_SECONDS = 15
    OSM_USER_AGENT = "FoodFinder/1.0 (dev_test)"

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.headers = {
            "x-ncp-apigw-api-key-id": client_id,
            "x-ncp-apigw-api-key": client_secret,
        }

        masked_id = f"{client_id[:4]}...{client_id[-4:]}" if client_id else "None"
        logger.debug("NaverGeocodingClient initialized with key id: %s", masked_id)

    def coord_to_address(self, longitude: float, latitude: float) -> Optional[str]:
        """Convert coordinates to address using Naver reverse geocoding."""
        params = {
            "coords": f"{longitude},{latitude}",
            "orders": "roadaddr,addr",
            "output": "json",
        }

        data = self._request_with_fallback(self.REVERSE_GEOCODING_URLS, params)
        if data:
            address = self._extract_reverse_address(data)
            if address:
                return address

        return self._fallback_reverse_nominatim(longitude, latitude)

    def address_to_coord(self, query: str) -> Optional[Dict]:
        """Convert address/place name to coordinates using Naver geocoding."""
        params = {
            "query": query,
        }

        data = self._request_with_fallback(self.GEOCODING_URLS, params)
        if data:
            coord = self._extract_geocoding_result(data)
            if coord:
                return coord

        return self._fallback_search_nominatim(query)

    def _request_with_fallback(self, urls: tuple, params: Dict) -> Optional[Dict]:
        if not self.client_id or not self.client_secret:
            logger.warning(
                "Naver Cloud API key is missing. Skip Naver Maps request and use fallback."
            )
            return None

        for url in urls:
            try:
                response = requests.get(
                    url,
                    headers=self.headers,
                    params=params,
                    timeout=self.TIMEOUT_SECONDS,
                )

                if response.status_code == 200:
                    return response.json()

                logger.warning(
                    "Naver Maps API failed: status=%s url=%s body=%s",
                    response.status_code,
                    url,
                    response.text[:300],
                )
            except requests.exceptions.RequestException as exc:
                logger.warning("Naver Maps API request error at %s: %s", url, exc)

        return None

    def _extract_reverse_address(self, data: Dict) -> Optional[str]:
        results = data.get("results", [])
        if not results:
            return None

        preferred = ("roadaddr", "addr")
        for name in preferred:
            for result in results:
                if result.get("name") != name:
                    continue

                region = result.get("region", {})
                area1 = region.get("area1", {}).get("name", "")
                area2 = region.get("area2", {}).get("name", "")
                area3 = region.get("area3", {}).get("name", "")
                area4 = region.get("area4", {}).get("name", "")

                parts = [part for part in (area1, area2, area3, area4) if part]
                if parts:
                    return " ".join(parts)

        return None

    def _extract_geocoding_result(self, data: Dict) -> Optional[Dict]:
        addresses = data.get("addresses", [])
        if not addresses:
            return None

        first = addresses[0]
        x = first.get("x")
        y = first.get("y")

        if x is None or y is None:
            return None

        address = (
            first.get("roadAddress")
            or first.get("jibunAddress")
            or first.get("englishAddress")
            or ""
        )

        return {
            "address": address,
            "latitude": float(y),
            "longitude": float(x),
        }

    def _fallback_reverse_nominatim(
        self,
        longitude: float,
        latitude: float,
    ) -> Optional[str]:
        logger.info("Falling back to OSM Nominatim reverse geocoding")
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            "lat": latitude,
            "lon": longitude,
            "format": "json",
            "zoom": 18,
            "addressdetails": 1,
        }
        headers = {
            "User-Agent": self.OSM_USER_AGENT,
        }

        try:
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=self.OSM_TIMEOUT_SECONDS,
            )
            if response.status_code == 200:
                data = response.json()
                address = data.get("display_name", "")
                return address if address else None
        except requests.exceptions.RequestException as exc:
            logger.error("OSM reverse geocoding failed: %s", exc)

        return None

    def _fallback_search_nominatim(self, query: str) -> Optional[Dict]:
        logger.info("Falling back to OSM Nominatim geocoding for query=%s", query)
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": query,
            "format": "json",
            "limit": 1,
        }
        headers = {
            "User-Agent": self.OSM_USER_AGENT,
        }

        try:
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=self.OSM_TIMEOUT_SECONDS,
            )
            if response.status_code == 200:
                data = response.json()
                if data:
                    first = data[0]
                    return {
                        "address": first.get("display_name"),
                        "latitude": float(first.get("lat")),
                        "longitude": float(first.get("lon")),
                    }
        except requests.exceptions.RequestException as exc:
            logger.error("OSM geocoding fallback failed: %s", exc)

        return None
