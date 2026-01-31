from api.naver_geocoding import NaverGeocodingClient
from config import Config
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)

print("="*60)
print("🌍 Reverse Geocoding 테스트 (Naver -> OSM Fallback)")
print("="*60)

# 일부러 잘못된 키를 넣어서 Naver 실패 유도 (이미 실패하지만..)
client = NaverGeocodingClient("invalid_id", "invalid_secret")

# 서울 시청 좌표
address = client.coord_to_address(126.9780, 37.5665)

print("-" * 60)
if address:
    print(f"✅ 최종 주소: {address}")
else:
    print("❌ 실패: 모든 시도 실패")
