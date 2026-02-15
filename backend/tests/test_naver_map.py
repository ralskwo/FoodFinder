from unittest.mock import Mock, patch

import requests

from api.naver_map import NaverMapClient


def _mock_response(status_code, payload):
    response = Mock()
    response.status_code = status_code
    response.json.return_value = payload
    return response


def test_search_local_success_with_geocoding():
    client = NaverMapClient(
        client_id="test-client-id",
        client_secret="test-client-secret",
        geocoding_client_id="test-cloud-id",
        geocoding_client_secret="test-cloud-secret",
    )

    api_payload = {
        "items": [
            {
                "title": "<b>맛집</b> 한식당",
                "category": "한식>백반",
                "address": "서울시 중구",
                "roadAddress": "서울시 중구 세종대로",
                "telephone": "02-1234-5678",
                "link": "https://map.naver.com/p/entry/place/123456",
            }
        ]
    }

    with patch(
        "api.naver_map.requests.get",
        side_effect=[
            _mock_response(200, api_payload),
            _mock_response(200, {"items": []}),
        ],
    ), patch(
        "api.naver_geocoding.NaverGeocodingClient.address_to_coord",
        return_value={"latitude": 37.5665, "longitude": 126.9780, "address": "서울시 중구"},
    ):
        results = client.search_local(
            "한식",
            latitude=37.5665,
            longitude=126.9780,
            radius=1500,
        )

    assert len(results) == 1
    assert results[0]["title"] == "맛집 한식당"
    assert results[0]["latitude"] == 37.5665
    assert results[0]["longitude"] == 126.9780
    assert results[0]["distance"] <= 1500


def test_search_local_network_error_returns_empty():
    client = NaverMapClient(client_id="test-client-id", client_secret="test-client-secret")

    with patch("api.naver_map.requests.get", side_effect=requests.exceptions.RequestException("boom")):
        results = client.search_local("한식")

    assert results == []


def test_search_local_returns_fallback_when_out_of_radius():
    client = NaverMapClient(
        client_id="test-client-id",
        client_secret="test-client-secret",
        geocoding_client_id="test-cloud-id",
        geocoding_client_secret="test-cloud-secret",
    )

    api_payload = {
        "items": [
            {
                "title": "거리먼 식당",
                "category": "한식",
                "address": "부산시 해운대구",
                "roadAddress": "부산시 해운대구 우동",
                "telephone": "",
                "link": "",
            }
        ]
    }

    with patch(
        "api.naver_map.requests.get",
        side_effect=[
            _mock_response(200, api_payload),
            _mock_response(200, {"items": []}),
        ],
    ), patch(
        "api.naver_geocoding.NaverGeocodingClient.address_to_coord",
        return_value={"latitude": 35.1587, "longitude": 129.1604, "address": "부산시 해운대구"},
    ):
        results = client.search_local(
            "한식",
            latitude=37.5665,
            longitude=126.9780,
            radius=100,
        )

    assert len(results) == 1
    assert results[0]["title"] == "거리먼 식당"
    assert results[0]["distance"] > 100
