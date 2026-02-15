from unittest.mock import patch

import pytest

from app import create_app
from database import db
from models.menu import Menu
from models.restaurant import Restaurant
from services.menu_service import MenuService


@pytest.fixture
def app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "NAVER_CLIENT_ID": "test-id",
            "NAVER_CLIENT_SECRET": "test-secret",
            "NAVER_CLOUD_ID": "test-cloud-id",
            "NAVER_CLOUD_SECRET": "test-cloud-secret",
        }
    )

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def restaurant(app):
    with app.app_context():
        row = Restaurant(
            place_id="test-place",
            name="Test Restaurant",
            latitude=37.5665,
            longitude=126.9780,
            address="Seoul",
        )
        db.session.add(row)
        db.session.commit()
        return row.id


def test_get_menus_uses_cache_before_crawl(app, restaurant):
    with app.app_context():
        restaurant_row = db.session.get(Restaurant, restaurant)
        cached = Menu(
            restaurant_id=restaurant_row.id,
            name="Cached Menu",
            price=8000,
            source="user",
            is_representative=True,
        )
        db.session.add(cached)
        db.session.commit()

        service = MenuService()
        with patch.object(service, "_crawl_menus") as mock_crawl:
            menus = service.get_menus(restaurant_row, allow_crawl=False)

        assert len(menus) == 1
        assert menus[0].name == "Cached Menu"
        mock_crawl.assert_not_called()


def test_get_menus_skips_crawl_when_disabled(app, restaurant):
    with app.app_context():
        restaurant_row = db.session.get(Restaurant, restaurant)
        service = MenuService()
        with patch.object(service, "_crawl_menus") as mock_crawl:
            menus = service.get_menus(restaurant_row, allow_crawl=False)

        assert menus == []
        mock_crawl.assert_not_called()


def test_get_menus_crawls_and_saves_when_enabled(app, restaurant):
    with app.app_context():
        restaurant_row = db.session.get(Restaurant, restaurant)
        service = MenuService()
        fake_menu_data = [
            {"name": "Kimchi Jjigae", "price": 9000, "is_representative": True, "source": "naver"},
            {"name": "Bibimbap", "price": 10000, "is_representative": False, "source": "naver"},
        ]

        with patch.object(service, "_crawl_menus", return_value=fake_menu_data):
            menus = service.get_menus(restaurant_row, allow_crawl=True)

        assert len(menus) == 2
        saved_names = sorted([menu.name for menu in menus])
        assert saved_names == ["Bibimbap", "Kimchi Jjigae"]
        assert Menu.query.filter_by(restaurant_id=restaurant_row.id).count() == 2


def test_get_menus_resolves_place_id_when_link_missing(app, restaurant):
    with app.app_context():
        restaurant_row = db.session.get(Restaurant, restaurant)
        service = MenuService()
        fake_menu_data = [{"name": "Kimchi Jjigae", "price": 9000, "is_representative": True}]

        with patch.object(service.naver_crawler, "get_place_id_from_link", return_value=None), patch.object(
            service.naver_crawler, "find_place_id", return_value="123456"
        ) as mock_find_id, patch.object(
            service.naver_crawler, "get_menus", return_value=fake_menu_data
        ) as mock_get_menus:
            menus = service.get_menus(restaurant_row, naver_link=None, allow_crawl=True)

        assert len(menus) == 1
        mock_find_id.assert_called_once()
        mock_get_menus.assert_called_once_with("123456")


def test_get_menus_repairs_broken_cached_menu_name(app, restaurant):
    with app.app_context():
        restaurant_row = db.session.get(Restaurant, restaurant)
        broken_name = "생삼겹살".encode("utf-8").decode("latin1")
        cached = Menu(
            restaurant_id=restaurant_row.id,
            name=broken_name,
            price=17000,
            source="naver",
            is_representative=True,
        )
        db.session.add(cached)
        db.session.commit()

        service = MenuService()
        menus = service.get_menus(restaurant_row, allow_crawl=False)

        assert len(menus) == 1
        assert menus[0].name == "생삼겹살"
