import pytest
from flask import Flask
from sqlalchemy.exc import IntegrityError

from database import db, init_db
from models.restaurant import Restaurant
from models.user_preference import UserPreference


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["TESTING"] = True
    init_db(app)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_restaurant_to_dict(app):
    with app.app_context():
        row = Restaurant(
            place_id="place-1",
            name="테스트 식당",
            category="한식",
            address="서울시 중구",
            latitude=37.5665,
            longitude=126.9780,
            rating=4.3,
        )
        data = row.to_dict()

        assert data["place_id"] == "place-1"
        assert data["name"] == "테스트 식당"
        assert data["latitude"] == 37.5665
        assert data["longitude"] == 126.9780


def test_restaurant_coordinate_constraints(app):
    with app.app_context():
        invalid = Restaurant(
            place_id="invalid-lat",
            name="Invalid",
            latitude=91.0,
            longitude=126.9780,
        )
        db.session.add(invalid)

        with pytest.raises(IntegrityError):
            db.session.commit()

        db.session.rollback()


def test_restaurant_negative_delivery_fee_constraint(app):
    with app.app_context():
        invalid = Restaurant(
            place_id="invalid-delivery",
            name="Invalid",
            latitude=37.5665,
            longitude=126.9780,
            delivery_fee=-100,
        )
        db.session.add(invalid)

        with pytest.raises(IntegrityError):
            db.session.commit()

        db.session.rollback()


def test_user_preference_categories_roundtrip(app):
    with app.app_context():
        pref = UserPreference(session_id="session-1")
        pref.favorite_categories = ["한식", "중식"]
        db.session.add(pref)
        db.session.commit()

        fetched = UserPreference.query.filter_by(session_id="session-1").first()
        assert fetched.favorite_categories == ["한식", "중식"]


def test_user_preference_invalid_categories_type(app):
    with app.app_context():
        pref = UserPreference(session_id="session-invalid")
        with pytest.raises(ValueError):
            pref.favorite_categories = "not-a-list"
