import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """기본 설정"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///foodfinder.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 네이버 API 설정
    NAVER_CLIENT_ID = os.getenv('NAVER_CLIENT_ID')
    NAVER_CLIENT_SECRET = os.getenv('NAVER_CLIENT_SECRET')

    # 검색 기본값
    DEFAULT_SEARCH_RADIUS = 1000  # 미터
    MAX_SEARCH_RADIUS = 5000
