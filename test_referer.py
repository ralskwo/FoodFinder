import os
from dotenv import load_dotenv
import requests
import json

load_dotenv('backend/.env')

cloud_id = os.getenv('NAVER_CLOUD_ID')
cloud_secret = os.getenv('NAVER_CLOUD_SECRET')

print("="*60)
print("📍 Referer 헤더 테스트")
print("="*60)

url = "https://naveropenapi.apigw.ntruss.com/map-geocode/v2/geocode"
headers = {
    "X-NCP-APIGW-API-KEY-ID": cloud_id,
    "X-NCP-APIGW-API-KEY": cloud_secret,
    # ⭐ 핵심: 네이버 콘솔에 등록한 주소를 Referer로 척 보냄
    "Referer": "http://localhost:3000" 
}
params = {
    "query": "분당구 불정로 6"
}

try:
    print(f"요청 보냄... (Referer: http://localhost:3000)")
    response = requests.get(url, headers=headers, params=params, timeout=5)
    print(f"상태 코드: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ 성공!!! Referer 헤더가 필요했군요.")
        print(f"좌표: {response.json()['addresses'][0]['x']}, {response.json()['addresses'][0]['y']}")
    else:
        print(f"❌ 여전히 실패...")
        print(response.text)
        
except Exception as e:
    print(f"에러: {e}")
