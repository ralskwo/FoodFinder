import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """기본 설정"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')

    # 프로덕션 환경 검증
    if os.getenv('FLASK_ENV') == 'production' and SECRET_KEY == 'dev-secret-key':
        raise ValueError("Production environment requires a secure SECRET_KEY")

    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///foodfinder.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 네이버 Developers API 설정 (검색)
    NAVER_CLIENT_ID = os.getenv('NAVER_CLIENT_ID')
    NAVER_CLIENT_SECRET = os.getenv('NAVER_CLIENT_SECRET')

    # 네이버 Cloud Platform API 설정 (지도/Geocoding) - 없으면 기존 키 사용 시도
    NAVER_CLOUD_ID = os.getenv('NAVER_CLOUD_ID', NAVER_CLIENT_ID)
    NAVER_CLOUD_SECRET = os.getenv('NAVER_CLOUD_SECRET', NAVER_CLIENT_SECRET)

    # 카카오맵 API 설정
    KAKAO_API_KEY = os.getenv('KAKAO_API_KEY', '')

    # 환경 변수가 설정되지 않았을 때 경고 또는 에러
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        import warnings
        warnings.warn(
            "NAVER_CLIENT_ID and NAVER_CLIENT_SECRET are not set. "
            "API calls will fail. Please set them in .env file.",
            RuntimeWarning
        )

    # 검색 기본값
    DEFAULT_SEARCH_RADIUS = 1000  # 미터
    MAX_SEARCH_RADIUS = 5000
