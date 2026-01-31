import os
from dotenv import load_dotenv

# .env 로드
load_dotenv('backend/.env')

cloud_id = os.getenv('NAVER_CLOUD_ID')
cloud_secret = os.getenv('NAVER_CLOUD_SECRET')

print("="*60)
print("🔑 키 값 정밀 분석")
print("="*60)

if cloud_id:
    print(f"Cloud ID 길이: {len(cloud_id)}")
    print(f"Cloud ID (Raw): '{cloud_id}'")
    if cloud_id.strip() != cloud_id:
        print("⚠️ 경고: Cloud ID 앞뒤에 공백이 있습니다!")
    
    # 헥사 값 출력 (숨겨진 문자 확인)
    hex_id = ":".join("{:02x}".format(ord(c)) for c in cloud_id)
    print(f"Cloud ID (Hex): {hex_id}")
else:
    print("Cloud ID가 로드되지 않았습니다.")

print("-" * 30)

if cloud_secret:
    print(f"Cloud Secret 길이: {len(cloud_secret)}")
    # Secret은 마스킹하지만 길이는 확인
    print(f"Cloud Secret 앞 5자리: '{cloud_secret[:5]}'")
    if cloud_secret.strip() != cloud_secret:
        print("⚠️ 경고: Cloud Secret 앞뒤에 공백이 있습니다!")
else:
    print("Cloud Secret이 로드되지 않았습니다.")

print("="*60)
