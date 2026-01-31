import pytest
from app import create_app
from database import db
from models.restaurant import Restaurant
from models.menu import Menu


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_search_restaurants_basic(client, app):
    """기본 검색 테스트"""
    with app.app_context():
        response = client.post("/api/restaurants/search", json={
            "lat": 37.5665,
            "lng": 126.9780,
            "radius": 1000,
            "query": "음식점"
        })

        assert response.status_code == 200
        data = response.get_json()
        assert "results" in data
        assert "total" in data


def test_search_with_budget_filter(client, app):
    """예산 필터 테스트"""
    with app.app_context():
        response = client.post("/api/restaurants/search", json={
            "lat": 37.5665,
            "lng": 126.9780,
            "radius": 1000,
            "query": "음식점",
            "budget": 10000,
            "budget_type": "menu"
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data["filters_applied"]["budget"] == 10000


def test_contribute_menu(client, app):
    """사용자 메뉴 기여 테스트"""
    with app.app_context():
        # 먼저 음식점 생성
        restaurant = Restaurant(
            place_id="test_place_123",
            name="테스트 음식점",
            latitude=37.5665,
            longitude=126.9780
        )
        db.session.add(restaurant)
        db.session.commit()

        # 메뉴 기여
        response = client.post("/api/restaurants/test_place_123/menus/contribute", json={
            "menu_name": "김치찌개",
            "price": 8000
        })

        assert response.status_code == 201
        data = response.get_json()
        assert data["name"] == "김치찌개"
        assert data["price"] == 8000
        assert data["source"] == "user"


def test_geocode_reverse(client, app):
    """역지오코딩 테스트"""
    with app.app_context():
        response = client.get("/api/geocode/reverse?lat=37.5665&lng=126.9780")
        assert response.status_code == 200
        data = response.get_json()
        assert "latitude" in data
        assert "longitude" in data


def test_search_missing_location(client, app):
    """위치 정보 없는 검색 테스트"""
    with app.app_context():
        response = client.post("/api/restaurants/search", json={
            "query": "음식점"
        })
        assert response.status_code == 400
