import requests
import re
import time
import logging

logger = logging.getLogger(__name__)


class DeliveryAppCrawler:
    """배달앱에서 메뉴 정보 크롤링 (배달의민족, 요기요)"""

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
    }

    def __init__(self, delay: float = 0.5):
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def search_baemin(self, restaurant_name: str, address: str) -> list:
        """
        배달의민족에서 음식점 메뉴 검색

        Note: 배달의민족은 공식 API가 없어 웹 스크래핑이 제한적임.
              실제 구현 시 Selenium/Playwright 필요할 수 있음.
        """
        try:
            time.sleep(self.delay)
            # 배달의민족 웹사이트 구조 변경이 잦아 실제 크롤링은 복잡함
            # 여기서는 기본 구조만 제공
            logger.info(f"Baemin search for: {restaurant_name}")
            return []
        except Exception as e:
            logger.error(f"Baemin crawl failed: {e}")
            return []

    def search_yogiyo(self, restaurant_name: str, address: str) -> list:
        """
        요기요에서 음식점 메뉴 검색

        Note: 요기요도 공식 API가 없어 웹 스크래핑이 제한적임.
        """
        try:
            time.sleep(self.delay)
            logger.info(f"Yogiyo search for: {restaurant_name}")
            return []
        except Exception as e:
            logger.error(f"Yogiyo crawl failed: {e}")
            return []

    def get_menus(self, restaurant_name: str, address: str) -> list:
        """
        배달앱에서 메뉴 정보 통합 검색

        Returns:
            list: [{'name': '메뉴명', 'price': 가격(int), 'is_representative': bool}, ...]
        """
        # 배달의민족 먼저 시도
        menus = self.search_baemin(restaurant_name, address)

        # 결과 없으면 요기요 시도
        if not menus:
            menus = self.search_yogiyo(restaurant_name, address)

        return menus
