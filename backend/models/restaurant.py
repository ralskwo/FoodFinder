from datetime import datetime
from backend.database import db


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

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
