import requests
from typing import List, Dict, Optional
import re
import logging
import concurrent.futures

logger = logging.getLogger(__name__)


class NaverMapClient:
    """네이버 지도 API 클라이언트"""

    BASE_URL = 'https://openapi.naver.com/v1/search/local.json'

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        geocoding_client_id: Optional[str] = None,
        geocoding_client_secret: Optional[str] = None
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.geocoding_client_id = geocoding_client_id
        self.geocoding_client_secret = geocoding_client_secret
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
        네이버 지역 검색 API 호출 + OSM 좌표 변환을 통한 정확한 거리 필터링
        """
        # 1. 네이버 API에서 넉넉하게 가져오기
        all_items = []
        seen_keys = set()
        max_items = 15  # 15개 정도 가져와서 필터링 (속도 고려)
        
        # 3번 호출 (1, 6, 11) -> 5개씩 총 15개
        for start in [1, 6, 11]:
            params = {
                'query': query,
                'display': 5, # API 최대값
                'start': start,
                'sort': 'random'
            }
            try:
                response = requests.get(
                    self.BASE_URL,
                    headers=self.headers,
                    params=params,
                    timeout=5
                )
                if response.status_code == 200:
                    data = response.json()
                    items = data.get('items', [])
                    if not items: break
                    
                    # 수집 단계에서 중복 제거
                    for item in items:
                        # 태그 제거된 타이틀과 주소로 고유 키 생성
                        clean_title = re.sub(r'<[^>]+>', '', item.get('title', ''))
                        unique_key = f"{clean_title}_{item.get('address')}"
                        
                        if unique_key not in seen_keys:
                            seen_keys.add(unique_key)
                            all_items.append(item)
                            
                    if len(all_items) >= max_items: break
            except Exception as e:
                logger.error(f"Search API Error: {e}")
                break

        # 2. 결과 정제 및 정확한 좌표 변환 (병렬 처리)
        results = []
        
        # 순환 참조 방지를 위해 함수 내부 import
        from api.naver_geocoding import NaverGeocodingClient 
        # 환경변수 로드가 필요하지만, 인스턴스를 매번 만들면 비효율적이므로 임시 키 사용 (OSM은 키 불필요)
        geo_client = NaverGeocodingClient(
            self.geocoding_client_id or "",
            self.geocoding_client_secret or ""
        )

        def process_item(item):
            # 기본 파싱
            parsed = self._parse_item(item)
            
            # 주소로 정확한 좌표 구하기 (OSM)
            # WGS84 좌표가 없으면 거리 계산이 엉망이 되므로 필수
            addr = parsed['road_address'] or parsed['address']
            
            # 이미 캐싱된 좌표가 있다면 좋겠지만 지금은 매번 호출
            if addr:
                # '경기도 화성시 향남읍' 정도만 있어도 좌표가 나옴
                coord = geo_client.address_to_coord(addr)
                if coord:
                    parsed['latitude'] = coord['latitude']
                    parsed['longitude'] = coord['longitude']
                else:
                    parsed['latitude'] = None
                    parsed['longitude'] = None
            return parsed

        # 병렬 실행 (속도 향상) - OSM 호출 병렬화
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_item = {executor.submit(process_item, item): item for item in all_items}
            for future in concurrent.futures.as_completed(future_to_item):
                try:
                    res = future.result()
                    results.append(res)
                except Exception as e:
                    logger.error(f"Item processing failed: {e}")

        # 3. 거리 기반 필터링
        if latitude and longitude:
            filtered_results = []
            for result in results:
                if result['latitude'] is None or result['longitude'] is None:
                    continue
                    
                # 유클리드 거리 (약식)
                lat_diff = abs(result['latitude'] - latitude) * 111000
                lon_diff = abs(result['longitude'] - longitude) * 88000
                distance = (lat_diff ** 2 + lon_diff ** 2) ** 0.5

                if distance <= radius:
                    result['distance'] = int(distance)
                    filtered_results.append(result)

            # 거리순 정렬
            filtered_results.sort(key=lambda x: x.get('distance', 999999))
            
            return filtered_results

        return results

    def _parse_item(self, item: Dict) -> Dict:
        """API 응답 아이템 파싱"""
        title = re.sub(r'<[^>]+>', '', item.get('title', ''))
        category_full = item.get('category', '')
        category = category_full.split('>')[0] if category_full else ''

        return {
            'title': title,
            'category': category,
            'address': item.get('address', ''),
            'road_address': item.get('roadAddress', ''),
            'telephone': item.get('telephone', ''),
            'link': item.get('link', ''),
            'latitude': None,
            'longitude': None
        }
