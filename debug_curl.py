import os
from dotenv import load_dotenv
import subprocess

# .env 로드
load_dotenv('backend/.env')

cloud_id = os.getenv('NAVER_CLOUD_ID')
cloud_secret = os.getenv('NAVER_CLOUD_SECRET')

url = "https://naveropenapi.apigw.ntruss.com/map-reversegeocode/v2/gc?coords=126.9780,37.5665&orders=roadaddr,addr&output=json"

# cURL 명령어 구성 (Windows cmd용)
# 1. Referer 없음
cmd_no_referer = [
    "curl", "-v",
    "-H", f"X-NCP-APIGW-API-KEY-ID: {cloud_id}",
    "-H", f"X-NCP-APIGW-API-KEY: {cloud_secret}",
    url
]

# 2. Referer 있음 (localhost:3000)
cmd_referer = [
    "curl", "-v",
    "-H", f"X-NCP-APIGW-API-KEY-ID: {cloud_id}",
    "-H", f"X-NCP-APIGW-API-KEY: {cloud_secret}",
    "-H", "Referer: http://localhost:3000",
    url
]

print("\n" + "="*50)
print("📡 1. Referer 없이 호출")
print("="*50)
try:
    result = subprocess.run(cmd_no_referer, capture_output=True, text=True)
    print("STDOUT:", result.stdout)
    if "error" in result.stdout or result.returncode != 0:
        print("STDERR:", result.stderr)
except Exception as e:
    print(f"Error: {e}")

print("\n" + "="*50)
print("📡 2. Referer 포함 호출 (http://localhost:3000)")
print("="*50)
try:
    result = subprocess.run(cmd_referer, capture_output=True, text=True)
    print("STDOUT:", result.stdout)
    if "error" in result.stdout or result.returncode != 0:
         print("STDERR:", result.stderr)
except Exception as e:
    print(f"Error: {e}")
