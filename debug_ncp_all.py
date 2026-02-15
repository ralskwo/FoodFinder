import requests
import os
from dotenv import load_dotenv

load_dotenv(r'c:\Users\ralskwo\Desktop\Study\Privates\FoodFinder\backend\.env')

def test_ncp_api(url, name):
    client_id = os.getenv('NAVER_CLOUD_ID')
    client_secret = os.getenv('NAVER_CLOUD_SECRET')
    
    headers = {
        'X-NCP-APIGW-API-KEY-ID': client_id,
        'X-NCP-APIGW-API-KEY': client_secret
    }
    
    # Geocoding vs Reverse Geocoding
    if 'reversegeocode' in url:
        params = {'coords': '127.105399,37.359570', 'orders': 'addr', 'output': 'json'}
    else:
        params = {'query': '분당구 불정로 6', 'output': 'json'}
    
    print(f"\n--- Testing {name} ---")
    try:
        response = requests.get(url, headers=headers, params=params)
        print(f"Status: {response.status_code}")
        print(f"Result: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    # 1. Geocoding
    test_ncp_api('https://naveropenapi.apigw.ntruss.com/map-geocoding/v2/geocode', "Geocoding (Address to Coord)")
    # 2. Reverse Geocoding
    test_ncp_api('https://naveropenapi.apigw.ntruss.com/map-reversegeocode/v2/gc', "Reverse Geocoding (Coord to Address)")
