import requests
import os
from dotenv import load_dotenv

load_dotenv(r'c:\Users\ralskwo\Desktop\Study\Privates\FoodFinder\backend\.env')

def test_ncp_search():
    client_id = os.getenv('NAVER_CLOUD_ID')
    client_secret = os.getenv('NAVER_CLOUD_SECRET')
    
    # NCP version of Search API
    url = 'https://naveropenapi.apigw.ntruss.com/util/v1/search/local.json'
    headers = {
        'X-NCP-APIGW-API-KEY-ID': client_id,
        'X-NCP-APIGW-API-KEY': client_secret
    }
    params = {'query': '치킨', 'display': 1}
    
    print(f"Testing NCP Search API with ID: {client_id[:5]}...")
    try:
        response = requests.get(url, headers=headers, params=params)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    test_ncp_search()
