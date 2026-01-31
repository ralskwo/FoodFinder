import requests
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


class NaverGeocodingClient:
    """네이버 Reverse Geocoding API 클라이언트"""

    REVERSE_GEOCODING_URL = 'https://naveropenapi.apigw.ntruss.com/map-reversegeocode/v2/gc'

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.headers = {
            'X-NCP-APIGW-API-KEY-ID': client_id,
            'X-NCP-APIGW-API-KEY': client_secret
        }

    def coord_to_address(self, longitude: float, latitude: float) -> Optional[str]:
        """
        좌표를 주소로 변환 (Reverse Geocoding)

        Args:
            longitude: 경도
            latitude: 위도

        Returns:
            주소 문자열 또는 None
        """
        params = {
            'coords': f'{longitude},{latitude}',
            'orders': 'roadaddr,addr',  # 도로명 주소 우선, 지번 주소 대체
            'output': 'json'
        }

        try:
            response = requests.get(
                self.REVERSE_GEOCODING_URL,
                headers=self.headers,
                params=params,
                timeout=10
            )

            if response.status_code != 200:
                logger.warning(f"Naver Geocoding API 에러: {response.status_code}")
                logger.warning(f"응답: {response.text}")
                return self._fallback_nominatim(longitude, latitude)

            data = response.json()
            results = data.get('results', [])

            if not results:
                return self._fallback_nominatim(longitude, latitude)

            # 첫 번째 결과 사용
            result = results[0]
            region = result.get('region', {})
            land = result.get('land', {})

            # 주소 구성
            address_parts = []

            # 시/도
            area1 = region.get('area1', {}).get('name', '')
            if area1:
                address_parts.append(area1)

            # 시/군/구
            area2 = region.get('area2', {}).get('name', '')
            if area2:
                address_parts.append(area2)

            # 읍/면/동
            area3 = region.get('area3', {}).get('name', '')
            if area3:
                address_parts.append(area3)

            # 도로명 주소가 있으면 추가
            if result.get('name') == 'roadaddr':
                addition0 = land.get('addition0', {}).get('value', '')
                if addition0:
                    address_parts.append(addition0)

            address = ' '.join(address_parts)
            return address if address else None

        except requests.exceptions.RequestException as e:
            logger.error(f"네트워크 에러: {e}")
            return self._fallback_nominatim(longitude, latitude)
        except Exception as e:
            logger.error(f"주소 변환 에러: {e}")
            return self._fallback_nominatim(longitude, latitude)

    def _fallback_nominatim(self, longitude: float, latitude: float) -> Optional[str]:
        """
        OpenStreetMap Nominatim API를 이용한 예비 주소 변환
        (네이버 API 실패 시 사용, 키 필요 없음)
        """
        logger.info("네이버 지도 API 실패로 OSM Nominatim 시도")
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            'lat': latitude,
            'lon': longitude,
            'format': 'json',
            'zoom': 18,
            'addressdetails': 1
        }
        headers = {
            'User-Agent': 'FoodFinder/1.0 (dev_test)' 
        }
        
        try:
            # 타임아웃 15초로 증가
            response = requests.get(url, params=params, headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                address = data.get('display_name', '')
                return address if address else None
        except Exception as e:
            logger.error(f"OSM 백업 실패: {e}")
            
        return None

    def address_to_coord(self, query: str) -> Optional[Dict]:
        """
        주소/장소명으로 좌표 검색 (OSM Nominatim 사용)
        """
        logger.info(f"OSM Nominatim 주소 검색: {query}")
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': query,
            'format': 'json',
            'limit': 1
        }
        headers = {
            'User-Agent': 'FoodFinder/1.0 (dev_test)'
        }
        
        try:
            # 타임아웃 15초로 증가
            response = requests.get(url, params=params, headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if data:
                    result = data[0]
                    return {
                        'address': result.get('display_name'),
                        'latitude': float(result.get('lat')),
                        'longitude': float(result.get('lon'))
                    }
        except Exception as e:
            logger.error(f"OSM 검색 실패: {e}")
            
        return None
