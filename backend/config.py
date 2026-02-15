import os
import warnings

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")

    if os.getenv("FLASK_ENV") == "production" and SECRET_KEY == "dev-secret-key":
        raise ValueError("Production environment requires a secure SECRET_KEY")

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///foodfinder.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Naver Developers API (local search)
    NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
    NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

    # Naver Cloud Platform API Gateway keys (geocoding/reverse geocoding)
    NAVER_CLOUD_ID = os.getenv("NAVER_CLOUD_ID")
    NAVER_CLOUD_SECRET = os.getenv("NAVER_CLOUD_SECRET")

    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        warnings.warn(
            "NAVER_CLIENT_ID or NAVER_CLIENT_SECRET is missing. "
            "Local search API calls may fail.",
            RuntimeWarning,
        )

    if not NAVER_CLOUD_ID or not NAVER_CLOUD_SECRET:
        warnings.warn(
            "NAVER_CLOUD_ID or NAVER_CLOUD_SECRET is missing. "
            "Geocoding API calls may fail.",
            RuntimeWarning,
        )

    DEFAULT_SEARCH_RADIUS = 1000
    MAX_SEARCH_RADIUS = 5000
