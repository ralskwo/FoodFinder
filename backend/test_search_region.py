import requests
import json
import os
from dotenv import load_dotenv

load_dotenv('backend/.env')

API_URL = "http://localhost:5000/api/restaurants/search"

# 향남읍 좌표
test_location = {
    "latitude": 37.1325,  # 향남읍 대략적인 좌표
    "longitude": 126.9214
}
# 사용자 현재 위치
user_location = {
    "latitude": 37.1997,
    "longitude": 126.8313
}

print("=" * 60)
print("🔍 지역명 포함 검색 테스트")
print("=" * 60)

# 1. 그냥 검색
query1 = "삼겹살"
print(f"\n1. 검색어: '{query1}' (필터링 됨)")
payload1 = {
    "query": query1,
    "latitude": user_location["latitude"],
    "longitude": user_location["longitude"],
    "radius": 5000  # 반경 5km
}
try:
    res = requests.post(API_URL, json=payload1)
    print(f"결과: {res.json().get('count')}개")
except Exception as e:
    print(f"에러: {e}")

# 0. Geocoding 테스트
print("\n0. Geocoding 테스트")
print("-" * 60)
from api.naver_geocoding import NaverGeocodingClient
from config import Config
try:
    gc_client = NaverGeocodingClient(Config.NAVER_CLOUD_ID, Config.NAVER_CLOUD_SECRET)
    addr = gc_client.coord_to_address(126.9780, 37.5665)
    print(f"결과: {addr}")
except Exception as e:
    print(f"에러: {e}")

# 2. 지역명 포함 검색 (필터링 확인을 위해 API 직접 호출 시뮬레이션)
print("\n2. 검색어: '화성시 삼겹살' (원본 데이터 확인)")
from api.naver_map import NaverMapClient
try:
    # Config에서 클라이언트 ID/Secret 가져오기
    client = NaverMapClient(Config.NAVER_CLIENT_ID, Config.NAVER_CLIENT_SECRET)
    # raw_results는 거리 필터링 전의 데이터
    raw_results = client.search_local("화성시 삼겹살", latitude=37.1997, longitude=126.8313, radius=5000)
    print(f"원본 결과 개수: {len(raw_results)}개")
    for r in raw_results:
        print(f"- {r['title']} ({r['address']})")
except Exception as e:
    print(f"에러: {e}")
