import requests
from typing import List, Dict, Optional
import re


class NaverMapClient:
    """네이버 지도 API 클라이언트"""

    BASE_URL = 'https://openapi.naver.com/v1/search/local.json'

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.headers = {
            'X-Naver-Client-Id': client_id,
            'X-Naver-Client-Secret': client_secret
        }

    def search_local(
        self,
        query: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius: int = 1000,
        display: int = 20
    ) -> List[Dict]:
        """
        네이버 지역 검색 API 호출

        Args:
            query: 검색어 (예: '한식', '카페')
            latitude: 중심 위도
            longitude: 중심 경도
            radius: 검색 반경 (미터)
            display: 결과 개수 (최대 20)

        Returns:
            검색 결과 리스트
        """
        params = {
            'query': query,
            'display': min(display, 20),
            'sort': 'random'
        }

        try:
            response = requests.get(
                self.BASE_URL,
                headers=self.headers,
                params=params,
                timeout=10
            )

            if response.status_code != 200:
                print(f"API 에러: {response.status_code}")
                return []

            data = response.json()
            items = data.get('items', [])

            # 결과 정제
            results = []
            for item in items:
                results.append(self._parse_item(item))

            # 위치 기반 필터링 (선택사항)
            if latitude and longitude:
                results = self._filter_by_distance(
                    results, latitude, longitude, radius
                )

            return results

        except requests.exceptions.RequestException as e:
            print(f"네트워크 에러: {e}")
            return []

    def _parse_item(self, item: Dict) -> Dict:
        """API 응답 아이템 파싱"""
        # HTML 태그 제거
        title = re.sub(r'<[^>]+>', '', item.get('title', ''))

        # 좌표 변환 (네이버는 KATEC 좌표계 사용)
        mapx = item.get('mapx', '0')
        mapy = item.get('mapy', '0')

        # KATEC to WGS84 간단 변환 (정확도 낮음, 실제론 라이브러리 사용 권장)
        longitude = float(mapx) / 10000000
        latitude = float(mapy) / 10000000

        # 카테고리 추출 (첫 번째 항목만)
        category_full = item.get('category', '')
        category = category_full.split('>')[0] if category_full else ''

        return {
            'title': title,
            'category': category,
            'address': item.get('address', ''),
            'road_address': item.get('roadAddress', ''),
            'latitude': latitude,
            'longitude': longitude,
            'telephone': item.get('telephone', ''),
            'link': item.get('link', '')
        }

    def _filter_by_distance(
        self,
        results: List[Dict],
        lat: float,
        lon: float,
        radius: int
    ) -> List[Dict]:
        """거리 기반 필터링 (간단한 유클리드 거리 사용)"""
        # 실제로는 Haversine 공식 사용 권장
        filtered = []
        for result in results:
            # 간단한 거리 계산 (1도 ≈ 111km)
            lat_diff = abs(result['latitude'] - lat) * 111000
            lon_diff = abs(result['longitude'] - lon) * 88000  # 한국 위도 기준
            distance = (lat_diff ** 2 + lon_diff ** 2) ** 0.5

            if distance <= radius:
                result['distance'] = int(distance)
                filtered.append(result)

        return sorted(filtered, key=lambda x: x.get('distance', 0))
