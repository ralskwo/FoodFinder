import os
from dotenv import load_dotenv
import requests
import json
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# .env 로드
load_dotenv('backend/.env')

def mask_text(text):
    if not text: return "None"
    if len(text) < 8: return "****"
    return text[:4] + "*" * (len(text)-8) + text[-4:]

def test_search_api():
    print("\n" + "="*50)
    print("🔍 1. 네이버 검색 API (Developers) 테스트")
    print("="*50)
    
    client_id = os.getenv('NAVER_CLIENT_ID')
    client_secret = os.getenv('NAVER_CLIENT_SECRET')
    
    print(f"Client ID: {mask_text(client_id)}")
    
    url = "https://openapi.naver.com/v1/search/local.json"
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret
    }
    params = {
        "query": "치킨",
        "display": 5
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=5)
        print(f"상태 코드: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 성공! 검색 결과: {len(data.get('items', []))}개")
            # print(json.dumps(data, indent=2, ensure_ascii=False)[:200] + "...")
        else:
            print(f"❌ 실패! 응답 내용:\n{response.text}")
            
    except Exception as e:
        print(f"❌ 에러 발생: {e}")

def test_geocoding_api():
    print("\n" + "="*50)
    print("🗺️  2. 네이버 지도 API (Cloud Platform) 테스트")
    print("="*50)
    
    cloud_id = os.getenv('NAVER_CLOUD_ID')
    cloud_secret = os.getenv('NAVER_CLOUD_SECRET')
    
    print(f"Cloud ID: {mask_text(cloud_id)}")
    
    url = "https://naveropenapi.apigw.ntruss.com/map-reversegeocode/v2/gc"
    headers = {
        "X-NCP-APIGW-API-KEY-ID": cloud_id,
        "X-NCP-APIGW-API-KEY": cloud_secret
    }
    # 사용자 현재 위치 (화성시)
    params = {
        "coords": "126.8313,37.1997",
        "output": "json",
        "orders": "roadaddr,addr"
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=5)
        print(f"상태 코드: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            status = data.get('status', {})
            if status.get('code') == 0:
                results = data.get('results', [])
                if results:
                    print(f"✅ 성공! 변환된 주소 데이터 있음")
                    # print(json.dumps(results[0], indent=2, ensure_ascii=False))
                else:
                    print(f"⚠️ 성공했으나 주소 결과가 없음 (바다 위거나 데이터 없음?)")
            else:
                print(f"❌ 실패 (API 내부 에러)! 응답 내용:\n{response.text}")
        else:
            print(f"❌ 실패 (HTTP 에러)! 응답 내용:\n{response.text}")
            if response.status_code == 401:
                print("-> 인증 실패: Client ID/Secret을 확인하세요.")
            elif response.status_code == 403:
                print("-> 권한 없음/호출 한도 초과/서비스 미신청")
                
    except Exception as e:
        print(f"❌ 에러 발생: {e}")

if __name__ == "__main__":
    print("환경 변수 파일 로드 중...")
    test_search_api()
    test_geocoding_api()
