import requests
import json

URL = "http://localhost:5000/api/geocode"
QUERY = "강남역"

try:
    print(f"요청: {URL}?query={QUERY}")
    response = requests.get(URL, params={'query': QUERY}, timeout=10)
    print(f"상태 코드: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ 성공!")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    else:
        print(f"❌ 실패! 응답 내용:\n{response.text}")
        
except Exception as e:
    print(f"❌ 에러 발생 (서버가 죽어있을 수 있음): {e}")
