from datetime import datetime, timezone
from backend.database import db
import json
import warnings


class UserPreference(db.Model):
    """사용자 선호도 설정 모델"""
    __tablename__ = 'user_preferences'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), unique=True, nullable=False, index=True)

    # 선호 카테고리 (JSON 배열로 저장)
    _favorite_categories = db.Column('favorite_categories', db.Text)

    # 검색 필터
    max_distance = db.Column(db.Integer, default=1000)  # 미터
    max_price_per_person = db.Column(db.Integer)  # 원
    max_delivery_fee = db.Column(db.Integer)  # 원

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    @property
    def favorite_categories(self):
        """카테고리 리스트 반환"""
        if self._favorite_categories:
            try:
                return json.loads(self._favorite_categories)
            except (json.JSONDecodeError, TypeError) as e:
                warnings.warn(f"Failed to decode favorite_categories: {e}")
                return []
        return []

    @favorite_categories.setter
    def favorite_categories(self, value):
        """카테고리 리스트 저장"""
        if not isinstance(value, list):
            raise ValueError("favorite_categories must be a list")
        self._favorite_categories = json.dumps(value, ensure_ascii=False)

    def to_dict(self):
        """딕셔너리로 변환"""
        return {
            'session_id': self.session_id,
            'favorite_categories': self.favorite_categories,
            'max_distance': self.max_distance,
            'max_price_per_person': self.max_price_per_person,
            'max_delivery_fee': self.max_delivery_fee,
        }

    def __repr__(self):
        return f'<UserPreference {self.session_id}>'
