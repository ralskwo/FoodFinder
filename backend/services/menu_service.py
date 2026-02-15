import logging
from datetime import datetime, timedelta, timezone

from crawlers.delivery_apps import DeliveryAppCrawler
from crawlers.naver_place import NaverPlaceCrawler
from database import db
from models.menu import Menu
from models.restaurant import Restaurant
from utils.text_normalizer import normalize_menu_name

logger = logging.getLogger(__name__)


class MenuService:
    """Menu retrieval and caching service."""

    CACHE_DURATION_HOURS = 24

    def __init__(self):
        self.naver_crawler = NaverPlaceCrawler()
        self.delivery_crawler = DeliveryAppCrawler()

    def get_menus(
        self,
        restaurant: Restaurant,
        naver_link: str = None,
        allow_crawl: bool = True,
    ) -> list:
        """
        Return menus from cache first, then crawl when allowed.
        """
        cached_menus = self._get_cached_menus(restaurant.id)
        if cached_menus:
            logger.info("Cache hit for restaurant %s", restaurant.id)
            return cached_menus

        if not allow_crawl:
            logger.info("Cache miss and crawling disabled for restaurant %s", restaurant.id)
            return []

        logger.info("Cache miss, crawling menus for %s", restaurant.name)
        menu_data = self._crawl_menus(restaurant, naver_link)

        if menu_data:
            self._save_menus(restaurant.id, menu_data)
            return self._get_cached_menus(restaurant.id) or []

        return []

    def _get_cached_menus(self, restaurant_id: int) -> list:
        """Get fresh menus from cache."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.CACHE_DURATION_HOURS)

        menus = Menu.query.filter(
            Menu.restaurant_id == restaurant_id,
            Menu.updated_at >= cutoff_time,
        ).all()

        self._normalize_cached_menu_names(menus)
        return menus if menus else None

    def _normalize_cached_menu_names(self, menus: list):
        if not menus:
            return

        changed = 0
        for menu in menus:
            normalized_name = normalize_menu_name(menu.name, fallback=menu.name or "메뉴명 확인 필요")
            if normalized_name != menu.name:
                menu.name = normalized_name
                changed += 1

        if changed:
            try:
                db.session.commit()
                logger.warning("Normalized %s cached menu names", changed)
            except Exception as exc:
                db.session.rollback()
                logger.error("Failed to normalize cached menu names: %s", exc)

    def _crawl_menus(self, restaurant: Restaurant, naver_link: str = None) -> list:
        """
        Crawl menus with source priority:
        1) Naver Place page
        2) Delivery app placeholders
        """
        menu_data = []
        source = None
        address_hint = restaurant.road_address or restaurant.address or ""

        place_id = self.naver_crawler.get_place_id_from_link(naver_link)
        if not place_id:
            place_id = self.naver_crawler.find_place_id(restaurant.name, address_hint)

        if place_id:
            menu_data = self.naver_crawler.get_menus(place_id)
            if menu_data:
                source = "naver"

        if not menu_data:
            menu_data = self.delivery_crawler.get_menus(restaurant.name, address_hint)
            if menu_data:
                source = "delivery"

        for item in menu_data:
            item["source"] = source or "unknown"

        return menu_data

    def _save_menus(self, restaurant_id: int, menu_data: list):
        """Persist crawled menus."""
        try:
            Menu.query.filter(
                Menu.restaurant_id == restaurant_id,
                Menu.source != "user",
            ).delete()

            for item in menu_data:
                normalized_name = normalize_menu_name(item.get("name"))
                menu = Menu(
                    restaurant_id=restaurant_id,
                    name=normalized_name,
                    price=item.get("price"),
                    is_representative=item.get("is_representative", False),
                    source=item.get("source", "unknown"),
                )
                db.session.add(menu)

            db.session.commit()
            logger.info("Saved %s menus for restaurant %s", len(menu_data), restaurant_id)

        except Exception as exc:
            db.session.rollback()
            logger.error("Failed to save menus: %s", exc)

    def add_user_contribution(self, restaurant_id: int, menu_name: str, price: int) -> Menu:
        """Store user-contributed menu data."""
        try:
            normalized_name = normalize_menu_name(menu_name, fallback="메뉴명 확인 필요")
            menu = Menu(
                restaurant_id=restaurant_id,
                name=normalized_name,
                price=price,
                is_representative=False,
                source="user",
            )
            db.session.add(menu)
            db.session.commit()
            return menu
        except Exception as exc:
            db.session.rollback()
            logger.error("Failed to add user contribution: %s", exc)
            return None

    def repair_recent_menu_names(self, limit: int = 5000) -> int:
        """
        Repair mojibake menu names in DB and return the number of updated rows.
        """
        rows = (
            Menu.query.order_by(Menu.updated_at.desc())
            .limit(max(1, int(limit)))
            .all()
        )
        if not rows:
            return 0

        changed = 0
        for menu in rows:
            normalized_name = normalize_menu_name(menu.name, fallback=menu.name or "메뉴명 확인 필요")
            if normalized_name != menu.name:
                menu.name = normalized_name
                changed += 1

        if changed:
            try:
                db.session.commit()
                logger.warning("Repaired %s stored menu names", changed)
            except Exception as exc:
                db.session.rollback()
                logger.error("Failed to repair stored menu names: %s", exc)
                return 0

        return changed
