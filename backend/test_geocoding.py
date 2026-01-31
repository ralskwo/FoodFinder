from api.naver_geocoding import NaverGeocodingClient
from config import Config
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)

print(f"Testing with Cloud Client ID: {Config.NAVER_CLOUD_ID}")
# 보안을 위해 Secret은 일부만 출력
secret_preview = Config.NAVER_CLOUD_SECRET[:5] + "..." if Config.NAVER_CLOUD_SECRET else "None"
print(f"Testing with Cloud Client Secret: {secret_preview}")

client = NaverGeocodingClient(Config.NAVER_CLOUD_ID, Config.NAVER_CLOUD_SECRET)
# Web 서비스 URL 검증을 통과하기 위해 헤더 추가 시도 (필요한 경우)
client.headers['Referer'] = 'http://localhost:3000'
address = client.coord_to_address(126.9780, 37.5665)

if address:
    print(f"✅ 성공! 주소: {address}")
else:
    print("❌ 실패: 주소를 가져오지 못했습니다. 위의 에러 메시지를 확인해주세요.")
    print("팁: Naver Cloud Platform Console > Services > Maps > Application에서 'Reverse Geocoding'이 선택되어 있는지 확인하세요.")
