import requests
import json
import os
from dotenv import load_dotenv

load_dotenv(r'c:\Users\ralskwo\Desktop\Study\Privates\FoodFinder\backend\.env')

def test_search():
    client_id = os.getenv('NAVER_CLIENT_ID')
    client_secret = os.getenv('NAVER_CLIENT_SECRET')
    
    url = 'https://openapi.naver.com/v1/search/local.json'
    headers = {
        'X-Naver-Client-Id': client_id,
        'X-Naver-Client-Secret': client_secret
    }
    params = {'query': '치킨', 'display': 1}
    
    print(f"Testing Search API with ID: {client_id[:5]}...")
    try:
        response = requests.get(url, headers=headers, params=params)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

def test_geocoding():
    client_id = os.getenv('NAVER_CLOUD_ID')
    client_secret = os.getenv('NAVER_CLOUD_SECRET')
    
    url = 'https://naveropenapi.apigw.ntruss.com/map-reversegeocode/v2/gc'
    headers = {
        'X-NCP-APIGW-API-KEY-ID': client_id,
        'X-NCP-APIGW-API-KEY': client_secret
    }
    params = {
        'coords': '126.9780,37.5665',
        'orders': 'addr',
        'output': 'json'
    }
    
    print(f"\nTesting Geocoding API with ID: {client_id[:5]}...")
    try:
        response = requests.get(url, headers=headers, params=params)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    test_search()
    test_geocoding()
