from datetime import datetime, timezone
from database import db


class UserMenuContribution(db.Model):
    """사용자 입력 메뉴 정보"""
    __tablename__ = 'user_menu_contributions'

    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    menu_name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Integer)
    contributed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    restaurant = db.relationship('Restaurant', backref=db.backref('user_contributions', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'menu_name': self.menu_name,
            'price': self.price,
            'contributed_at': self.contributed_at.isoformat() if self.contributed_at else None,
        }
