from datetime import datetime, timezone, timedelta
from database import db
from models.menu import Menu
from models.restaurant import Restaurant
from crawlers.naver_place import NaverPlaceCrawler
from crawlers.delivery_apps import DeliveryAppCrawler
import logging

logger = logging.getLogger(__name__)


class MenuService:
    """메뉴 정보 조회 서비스 (하이브리드 캐싱)"""

    CACHE_DURATION_HOURS = 24

    def __init__(self):
        self.naver_crawler = NaverPlaceCrawler()
        self.delivery_crawler = DeliveryAppCrawler()

    def get_menus(self, restaurant: Restaurant, naver_link: str = None) -> list:
        """
        메뉴 정보 조회 (캐시 우선, 없으면 크롤링)

        Args:
            restaurant: Restaurant 모델 인스턴스
            naver_link: 네이버 검색 결과의 link (place_id 추출용)

        Returns:
            list: Menu 객체 리스트
        """
        # 1. 캐시 확인
        cached_menus = self._get_cached_menus(restaurant.id)
        if cached_menus:
            logger.info(f"Cache hit for restaurant {restaurant.id}")
            return cached_menus

        # 2. 캐시 없으면 크롤링
        logger.info(f"Cache miss, crawling menus for {restaurant.name}")
        menu_data = self._crawl_menus(restaurant, naver_link)

        # 3. 결과 저장
        if menu_data:
            self._save_menus(restaurant.id, menu_data)
            return self._get_cached_menus(restaurant.id)

        return []

    def _get_cached_menus(self, restaurant_id: int) -> list:
        """캐시된 메뉴 조회 (24시간 이내)"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.CACHE_DURATION_HOURS)

        menus = Menu.query.filter(
            Menu.restaurant_id == restaurant_id,
            Menu.updated_at >= cutoff_time
        ).all()

        return menus if menus else None

    def _crawl_menus(self, restaurant: Restaurant, naver_link: str = None) -> list:
        """
        크롤링 우선순위에 따라 메뉴 정보 수집
        1순위: 네이버 플레이스
        2순위: 배달앱
        """
        menu_data = []
        source = None

        # 1순위: 네이버 플레이스
        if naver_link:
            place_id = self.naver_crawler.get_place_id_from_link(naver_link)
            if place_id:
                menu_data = self.naver_crawler.get_menus(place_id)
                if menu_data:
                    source = 'naver'

        # 2순위: 배달앱
        if not menu_data:
            menu_data = self.delivery_crawler.get_menus(
                restaurant.name,
                restaurant.address or restaurant.road_address
            )
            if menu_data:
                source = 'delivery'

        # source 추가
        for item in menu_data:
            item['source'] = source

        return menu_data

    def _save_menus(self, restaurant_id: int, menu_data: list):
        """메뉴 정보 DB 저장"""
        try:
            # 기존 메뉴 삭제 (user 소스 제외)
            Menu.query.filter(
                Menu.restaurant_id == restaurant_id,
                Menu.source != 'user'
            ).delete()

            # 새 메뉴 저장
            for item in menu_data:
                menu = Menu(
                    restaurant_id=restaurant_id,
                    name=item['name'],
                    price=item.get('price'),
                    is_representative=item.get('is_representative', False),
                    source=item.get('source', 'unknown')
                )
                db.session.add(menu)

            db.session.commit()
            logger.info(f"Saved {len(menu_data)} menus for restaurant {restaurant_id}")

        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to save menus: {e}")

    def add_user_contribution(self, restaurant_id: int, menu_name: str, price: int) -> Menu:
        """사용자 입력 메뉴 추가"""
        try:
            menu = Menu(
                restaurant_id=restaurant_id,
                name=menu_name,
                price=price,
                is_representative=False,
                source='user'
            )
            db.session.add(menu)
            db.session.commit()
            return menu
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to add user contribution: {e}")
            return None
