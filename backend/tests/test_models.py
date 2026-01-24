import pytest
from backend.database import db, init_db
from backend.models.restaurant import Restaurant
from backend.models.user_preference import UserPreference
from flask import Flask


@pytest.fixture
def app():
    """테스트용 Flask 앱 생성"""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
    init_db(app)

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_restaurant_creation(app):
    """Restaurant 모델 생성 테스트"""
    with app.app_context():
        restaurant = Restaurant(
            place_id='12345',
            name='맛있는 식당',
            category='한식',
            address='서울시 강남구',
            latitude=37.5665,
            longitude=126.9780,
            phone='02-1234-5678',
            rating=4.5
        )
        db.session.add(restaurant)
        db.session.commit()

        found = Restaurant.query.filter_by(place_id='12345').first()
        assert found is not None
        assert found.name == '맛있는 식당'
        assert found.category == '한식'
        assert found.rating == 4.5


def test_restaurant_to_dict(app):
    """Restaurant to_dict 메서드 테스트"""
    with app.app_context():
        restaurant = Restaurant(
            place_id='12345',
            name='맛있는 식당',
            category='한식',
            address='서울시 강남구',
            latitude=37.5665,
            longitude=126.9780
        )

        result = restaurant.to_dict()
        assert result['place_id'] == '12345'
        assert result['name'] == '맛있는 식당'
        assert 'latitude' in result
        assert 'longitude' in result


def test_user_preference_creation(app):
    """UserPreference 모델 생성 테스트"""
    with app.app_context():
        pref = UserPreference(
            session_id='test-session-123',
            favorite_categories=['한식', '일식'],
            max_distance=2000,
            max_price_per_person=20000,
            max_delivery_fee=3000
        )
        db.session.add(pref)
        db.session.commit()

        found = UserPreference.query.filter_by(session_id='test-session-123').first()
        assert found is not None
        assert '한식' in found.favorite_categories
        assert found.max_distance == 2000
