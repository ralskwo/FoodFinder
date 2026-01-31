import requests
import json

url = "https://nominatim.openstreetmap.org/search"
params = {
    'q': '강남역',
    'format': 'json',
    'limit': 1
}
headers = {
    'User-Agent': 'FoodFinderTest/1.0'
}

try:
    print(f"요청: {url} {params}")
    response = requests.get(url, params=params, headers=headers, timeout=10)
    print(f"상태 코드: {response.status_code}")
    print(f"응답: {response.text[:200]}")
except Exception as e:
    print(f"에러: {e}")
