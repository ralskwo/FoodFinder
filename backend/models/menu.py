from datetime import datetime, timezone
from database import db


class Menu(db.Model):
    """메뉴 정보 모델"""
    __tablename__ = 'menus'

    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Integer)  # 원 단위
    is_representative = db.Column(db.Boolean, default=False)
    source = db.Column(db.String(20))  # 'naver', 'baemin', 'yogiyo', 'kakao', 'user'
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                          onupdate=lambda: datetime.now(timezone.utc))

    restaurant = db.relationship('Restaurant', backref=db.backref('menus', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'price': self.price,
            'is_representative': self.is_representative,
            'source': self.source,
        }

    def __repr__(self):
        return f'<Menu {self.name} - {self.price}원>'
