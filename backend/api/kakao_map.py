import requests
import logging

logger = logging.getLogger(__name__)


class KakaoMapClient:
    """카카오맵 API 클라이언트"""

    SEARCH_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            'Authorization': f'KakaoAK {api_key}'
        }

    def search_restaurant(self, query: str, x: float = None, y: float = None, radius: int = 2000) -> dict:
        """
        카카오 로컬 검색 API로 음식점 검색

        Args:
            query: 검색어 (음식점명)
            x: 경도 (longitude)
            y: 위도 (latitude)
            radius: 검색 반경 (미터)
        """
        try:
            params = {
                'query': query,
                'category_group_code': 'FD6',  # 음식점
                'size': 5
            }

            if x and y:
                params['x'] = x
                params['y'] = y
                params['radius'] = radius
                params['sort'] = 'distance'

            response = requests.get(
                self.SEARCH_URL,
                headers=self.headers,
                params=params,
                timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                documents = data.get('documents', [])
                if documents:
                    return documents[0]  # 가장 관련성 높은 결과

            return None

        except Exception as e:
            logger.error(f"Kakao API error: {e}")
            return None

    def get_menu_info(self, restaurant_name: str, address: str) -> list:
        """
        카카오맵에서 메뉴 정보 조회

        Note: 카카오 로컬 API는 기본 정보만 제공하며,
              상세 메뉴 정보는 제한적임.
        """
        # 카카오 로컬 API는 메뉴 정보를 직접 제공하지 않음
        # place_url을 통해 웹페이지 크롤링이 필요할 수 있음
        logger.info(f"Kakao menu search for: {restaurant_name}")
        return []
