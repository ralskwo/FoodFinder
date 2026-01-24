import pytest
from unittest.mock import patch, Mock
from backend.api.naver_map import NaverMapClient


@pytest.fixture
def naver_client():
    """네이버 클라이언트 픽스처"""
    return NaverMapClient(
        client_id='test-client-id',
        client_secret='test-client-secret'
    )


def test_search_local_success(naver_client):
    """장소 검색 성공 테스트"""
    mock_response = {
        'items': [
            {
                'title': '맛있는 <b>한식</b>집',
                'category': '한식>일반한식',
                'address': '서울특별시 강남구',
                'roadAddress': '서울특별시 강남구 테헤란로 123',
                'mapx': '1269780000',
                'mapy': '375665000',
                'telephone': '02-1234-5678'
            }
        ]
    }

    with patch('backend.api.naver_map.requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_response

        results = naver_client.search_local('한식', latitude=37.5665, longitude=126.9780)

        assert len(results) == 1
        assert '한식' in results[0]['title']
        assert results[0]['latitude'] == 37.5665
        assert results[0]['longitude'] == 126.9780


def test_search_local_api_error(naver_client):
    """API 에러 처리 테스트"""
    with patch('backend.api.naver_map.requests.get') as mock_get:
        mock_get.return_value.status_code = 401

        results = naver_client.search_local('한식')
        assert results == []
