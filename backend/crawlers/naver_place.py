import requests
from bs4 import BeautifulSoup
import re
import time
import logging

logger = logging.getLogger(__name__)


class NaverPlaceCrawler:
    """네이버 플레이스에서 메뉴 정보 크롤링"""

    BASE_URL = "https://pcmap.place.naver.com/restaurant/{place_id}/menu"

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
    }

    def __init__(self, delay: float = 0.5):
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def get_menus(self, place_id: str) -> list:
        """
        네이버 플레이스에서 메뉴 정보 크롤링

        Args:
            place_id: 네이버 플레이스 ID

        Returns:
            list: [{'name': '메뉴명', 'price': 가격(int), 'is_representative': bool}, ...]
        """
        try:
            url = self.BASE_URL.format(place_id=place_id)
            time.sleep(self.delay)

            response = self.session.get(url, timeout=10)

            if response.status_code != 200:
                logger.warning(f"Naver Place returned {response.status_code} for {place_id}")
                return []

            soup = BeautifulSoup(response.text, 'html.parser')
            menus = []

            # 메뉴 아이템 파싱 (네이버 플레이스 구조에 따라 조정 필요)
            menu_items = soup.select('.menu_item, .item_menu, [class*="menu"]')

            for item in menu_items:
                try:
                    name_elem = item.select_one('.name, .menu_name, [class*="name"]')
                    price_elem = item.select_one('.price, .menu_price, [class*="price"]')

                    if not name_elem:
                        continue

                    name = name_elem.get_text(strip=True)
                    price = None

                    if price_elem:
                        price_text = price_elem.get_text(strip=True)
                        # 숫자만 추출 (예: "8,000원" -> 8000)
                        price_numbers = re.findall(r'[\d,]+', price_text)
                        if price_numbers:
                            price = int(price_numbers[0].replace(',', ''))

                    if name:
                        menus.append({
                            'name': name,
                            'price': price,
                            'is_representative': len(menus) < 2  # 처음 2개를 대표메뉴로
                        })
                except Exception as e:
                    logger.debug(f"Failed to parse menu item: {e}")
                    continue

            logger.info(f"Crawled {len(menus)} menus from Naver Place {place_id}")
            return menus

        except requests.RequestException as e:
            logger.error(f"Naver Place crawl failed for {place_id}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error crawling {place_id}: {e}")
            return []

    def get_place_id_from_link(self, naver_link: str) -> str:
        """
        네이버 링크에서 place_id 추출

        Args:
            naver_link: 네이버 검색 결과의 link 필드

        Returns:
            place_id 또는 None
        """
        if not naver_link:
            return None

        patterns = [
            r'place/(\d+)',
            r'place_id=(\d+)',
            r'/(\d{8,})',  # 8자리 이상 숫자
        ]

        for pattern in patterns:
            match = re.search(pattern, naver_link)
            if match:
                return match.group(1)

        return None
