from datetime import datetime, timezone
from database import db
from sqlalchemy import CheckConstraint


class Restaurant(db.Model):
    """음식점 정보 모델"""
    __tablename__ = 'restaurants'

    id = db.Column(db.Integer, primary_key=True)
    place_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50))
    address = db.Column(db.String(300))
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    phone = db.Column(db.String(20))
    rating = db.Column(db.Float)

    # 배달 정보 (사용자 입력)
    delivery_available = db.Column(db.Boolean, default=False)
    delivery_fee = db.Column(db.Integer)  # 원 단위
    minimum_order = db.Column(db.Integer)  # 원 단위

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # 데이터 무결성 제약조건
    __table_args__ = (
        CheckConstraint('latitude >= -90 AND latitude <= 90', name='check_latitude_range'),
        CheckConstraint('longitude >= -180 AND longitude <= 180', name='check_longitude_range'),
        CheckConstraint('rating IS NULL OR (rating >= 0 AND rating <= 5)', name='check_rating_range'),
        CheckConstraint('delivery_fee IS NULL OR delivery_fee >= 0', name='check_delivery_fee_positive'),
        CheckConstraint('minimum_order IS NULL OR minimum_order >= 0', name='check_minimum_order_positive'),
    )

    def to_dict(self):
        """딕셔너리로 변환"""
        return {
            'id': self.id,
            'place_id': self.place_id,
            'name': self.name,
            'category': self.category,
            'address': self.address,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'phone': self.phone,
            'rating': self.rating,
            'delivery_available': self.delivery_available,
            'delivery_fee': self.delivery_fee,
            'minimum_order': self.minimum_order,
        }

    def __repr__(self):
        return f'<Restaurant {self.name}>'
