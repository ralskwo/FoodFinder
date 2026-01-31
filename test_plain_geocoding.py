import os
from dotenv import load_dotenv
import requests
import json

# .env 로드
load_dotenv('backend/.env')

cloud_id = os.getenv('NAVER_CLOUD_ID')
cloud_secret = os.getenv('NAVER_CLOUD_SECRET')

print("="*60)
print("🗺️  Naver Maps Geocoding API 테스트 (주소 -> 좌표)")
print("="*60)
print(f"Cloud ID: {cloud_id[:5]}...")

url = "https://naveropenapi.apigw.ntruss.com/map-geocode/v2/geocode"
headers = {
    "X-NCP-APIGW-API-KEY-ID": cloud_id,
    "X-NCP-APIGW-API-KEY": cloud_secret
}
params = {
    "query": "분당구 불정로 6"
}

try:
    response = requests.get(url, headers=headers, params=params, timeout=5)
    print(f"상태 코드: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ 성공! Maps API 권한은 정상입니다.")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False)[:300])
    else:
        print(f"❌ 실패! 응답 내용:\n{response.text}")
        if response.status_code == 200:
             # 상태코드는 200인데 내용이 에러인 경우 (가끔 있음)
             pass
        elif "210" in response.text:
             print("\n-> 결론: 'Geocoding' API도 사용 권한이 없습니다.")
             print("   즉, Application 설정 문제가 아니라 'Maps' 서비스 자체가 이용 신청이 안 된 것 같습니다.")
        
except Exception as e:
    print(f"❌ 에러 발생: {e}")
