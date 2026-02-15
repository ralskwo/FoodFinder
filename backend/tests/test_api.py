import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app import create_app
from database import db
from models.restaurant import Restaurant


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
def client(app):
    return app.test_client()


def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "ok"


def test_search_restaurants_requires_coordinates(client):
    response = client.post("/api/restaurants/search", json={"query": "한식"})
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_search_restaurants_budget_filter(client):
    mocked_results = [
        {
            "title": "테스트식당",
            "category": "한식",
            "address": "서울시 강남구",
            "road_address": "서울시 강남구 테헤란로",
            "latitude": 37.5665,
            "longitude": 126.9780,
            "telephone": "02-1111-2222",
            "link": "https://map.naver.com/p/entry/place/123456",
        }
    ]

    mocked_menus = [
        SimpleNamespace(name="김치찌개", price=9000, is_representative=True),
        SimpleNamespace(name="제육볶음", price=11000, is_representative=False),
    ]

    with patch("api.restaurant.NaverMapClient.search_local", return_value=mocked_results), patch(
        "api.restaurant.menu_service.get_menus", return_value=mocked_menus
    ):
        response = client.post(
            "/api/restaurants/search",
            json={
                "lat": 37.5665,
                "lng": 126.9780,
                "radius": 1200,
                "query": "한식",
                "budget": 10000,
                "budget_type": "menu",
                "categories": ["한식"],
                "location_hint": "서울 강남구",
            },
        )

    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 1
    assert data["total"] == 1
    assert data["results"][0]["name"] == "테스트식당"
    assert data["results"][0]["title"] == "테스트식당"
    assert data["filters_applied"]["budget"] == 10000


def test_search_restaurants_excludes_when_budget_and_menu_missing(client):
    mocked_results = [
        {
            "title": "메뉴없는식당",
            "category": "한식",
            "address": "서울시 강남구",
            "road_address": "서울시 강남구 테헤란로",
            "latitude": 37.5665,
            "longitude": 126.9780,
            "telephone": "",
            "link": "",
        }
    ]

    with patch("api.restaurant.NaverMapClient.search_local", return_value=mocked_results), patch(
        "api.restaurant.menu_service.get_menus", return_value=[]
    ):
        response = client.post(
            "/api/restaurants/search",
            json={
                "lat": 37.5665,
                "lng": 126.9780,
                "budget": 10000,
                "query": "한식",
            },
        )

    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 0


def test_search_restaurants_strict_radius_filter(client):
    mocked_results = [
        {
            "title": "Far Place",
            "category": "한식",
            "address": "서울시 강남구",
            "road_address": "서울시 강남구 테헤란로",
            "latitude": 35.1796,
            "longitude": 129.0756,
            "telephone": "",
            "link": "",
        }
    ]

    with patch("api.restaurant.NaverMapClient.search_local", return_value=mocked_results):
        response = client.post(
            "/api/restaurants/search",
            json={
                "lat": 37.5665,
                "lng": 126.9780,
                "radius": 1200,
                "query": "음식점",
            },
        )

    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 0
    assert data["diagnostics"]["within_radius"] == 0


def test_search_restaurants_category_alias_match(client):
    mocked_results = [
        {
            "title": "맛있는 삼겹살",
            "category": "한식>육류,고기요리",
            "address": "서울시 강남구",
            "road_address": "서울시 강남구 역삼동",
            "latitude": 37.5665,
            "longitude": 126.9780,
            "telephone": "",
            "link": "",
        }
    ]

    with patch("api.restaurant.NaverMapClient.search_local", return_value=mocked_results):
        response = client.post(
            "/api/restaurants/search",
            json={
                "lat": 37.5665,
                "lng": 126.9780,
                "radius": 1500,
                "query": "음식점",
                "categories": ["고기"],
            },
        )

    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 1


def test_nearby_restaurants_endpoint(client, app):
    with app.app_context():
        near = Restaurant(
            place_id="near-1",
            name="가까운식당",
            latitude=37.5665,
            longitude=126.9780,
            delivery_fee=2000,
            delivery_available=True,
        )
        far = Restaurant(
            place_id="far-1",
            name="먼식당",
            latitude=37.7000,
            longitude=127.1000,
            delivery_fee=5000,
            delivery_available=True,
        )
        db.session.add(near)
        db.session.add(far)
        db.session.commit()

    response = client.get("/api/restaurants/nearby?lat=37.5665&lng=126.9780&radius=3000")
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 1
    assert data["results"][0]["name"] == "가까운식당"


def test_reverse_geocode_validation(client):
    response = client.get("/api/geocode/reverse")
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_reverse_geocode_success(client):
    with patch("api.restaurant.NaverGeocodingClient.coord_to_address", return_value="서울시 중구"):
        response = client.get("/api/geocode/reverse?lat=37.5665&lng=126.9780")

    assert response.status_code == 200
    data = response.get_json()
    assert data["address"] == "서울시 중구"
    assert data["latitude"] == 37.5665
