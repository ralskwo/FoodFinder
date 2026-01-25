import pytest
import json
from unittest.mock import patch, MagicMock
from backend.app import create_app
from backend.database import db


@pytest.fixture
def app():
    """테스트용 Flask 앱"""
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'NAVER_CLIENT_ID': 'test-id',
        'NAVER_CLIENT_SECRET': 'test-secret'
    })

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_health_check(client):
    """헬스 체크 엔드포인트 테스트"""
    response = client.get('/api/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'ok'


@patch('backend.api.restaurant.NaverMapClient')
def test_search_restaurants(mock_naver_client, client):
    """맛집 검색 엔드포인트 테스트"""
    # Mock 설정
    mock_instance = MagicMock()
    mock_instance.search_local.return_value = [
        {
            'title': '맛있는 한식당',
            'category': '한식',
            'address': '서울시 강남구',
            'latitude': 37.5665,
            'longitude': 126.9780,
            'telephone': '02-1234-5678'
        }
    ]
    mock_naver_client.return_value = mock_instance

    response = client.post('/api/restaurants/search', json={
        'query': '한식',
        'latitude': 37.5665,
        'longitude': 126.9780,
        'radius': 1000
    })

    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'results' in data
    assert isinstance(data['results'], list)
    assert len(data['results']) == 1
    assert data['results'][0]['title'] == '맛있는 한식당'


def test_search_restaurants_missing_params(client):
    """필수 파라미터 누락 테스트"""
    response = client.post('/api/restaurants/search', json={
        'query': '한식'
    })

    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data


def test_search_restaurants_missing_query(client):
    """검색어 누락 테스트"""
    response = client.post('/api/restaurants/search', json={
        'latitude': 37.5665,
        'longitude': 126.9780
    })

    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data


@patch('backend.api.restaurant.NaverMapClient')
def test_search_restaurants_with_category_filter(mock_naver_client, client):
    """카테고리 필터 테스트"""
    # Mock 설정
    mock_instance = MagicMock()
    mock_instance.search_local.return_value = [
        {'title': '한식당', 'category': '한식', 'latitude': 37.5665, 'longitude': 126.9780},
        {'title': '일식당', 'category': '일식', 'latitude': 37.5665, 'longitude': 126.9780},
    ]
    mock_naver_client.return_value = mock_instance

    response = client.post('/api/restaurants/search', json={
        'query': '맛집',
        'latitude': 37.5665,
        'longitude': 126.9780,
        'categories': ['한식']
    })

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['count'] == 1
    assert data['results'][0]['category'] == '한식'


def test_update_delivery_info_new_restaurant(client, app):
    """새 레스토랑 배달 정보 업데이트 테스트"""
    response = client.post('/api/restaurants/test-place-id/delivery', json={
        'name': '테스트 레스토랑',
        'latitude': 37.5665,
        'longitude': 126.9780,
        'delivery_fee': 3000,
        'minimum_order': 15000
    })

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['place_id'] == 'test-place-id'
    assert data['delivery_fee'] == 3000
    assert data['minimum_order'] == 15000
    assert data['delivery_available'] is True


def test_update_delivery_info_existing_restaurant(client, app):
    """기존 레스토랑 배달 정보 업데이트 테스트"""
    # 먼저 레스토랑 생성
    client.post('/api/restaurants/existing-place/delivery', json={
        'name': '기존 레스토랑',
        'latitude': 37.5665,
        'longitude': 126.9780,
        'delivery_fee': 2000
    })

    # 배달 정보 업데이트
    response = client.post('/api/restaurants/existing-place/delivery', json={
        'delivery_fee': 2500,
        'minimum_order': 20000
    })

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['delivery_fee'] == 2500
    assert data['minimum_order'] == 20000


def test_get_nearby_restaurants(client, app):
    """주변 맛집 조회 테스트"""
    # 테스트 데이터 생성
    client.post('/api/restaurants/nearby-place-1/delivery', json={
        'name': '가까운 레스토랑',
        'latitude': 37.5665,
        'longitude': 126.9780,
        'delivery_fee': 2000
    })
    client.post('/api/restaurants/nearby-place-2/delivery', json={
        'name': '먼 레스토랑',
        'latitude': 37.6000,  # 약 3.7km 떨어짐
        'longitude': 126.9780,
        'delivery_fee': 3000
    })

    response = client.get('/api/restaurants/nearby?lat=37.5665&lon=126.9780')

    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'results' in data
    # 3km 이내만 반환되어야 함
    assert data['count'] == 1
    assert data['results'][0]['name'] == '가까운 레스토랑'


def test_get_nearby_restaurants_with_delivery_fee_filter(client, app):
    """배달비 필터 테스트"""
    # 테스트 데이터 생성
    client.post('/api/restaurants/cheap-place/delivery', json={
        'name': '저렴한 배달',
        'latitude': 37.5665,
        'longitude': 126.9780,
        'delivery_fee': 2000
    })
    client.post('/api/restaurants/expensive-place/delivery', json={
        'name': '비싼 배달',
        'latitude': 37.5666,
        'longitude': 126.9781,
        'delivery_fee': 5000
    })

    response = client.get('/api/restaurants/nearby?lat=37.5665&lon=126.9780&max_delivery_fee=3000')

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['count'] == 1
    assert data['results'][0]['name'] == '저렴한 배달'


def test_get_nearby_restaurants_missing_location(client):
    """위치 정보 누락 테스트"""
    response = client.get('/api/restaurants/nearby')

    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data
