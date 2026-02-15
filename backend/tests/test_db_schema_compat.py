import sqlite3
import uuid
from pathlib import Path

from app import create_app
from database import db
from sqlalchemy import text


def _create_legacy_restaurants_table(db_path):
    connection = sqlite3.connect(db_path)
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE restaurants (
                id INTEGER NOT NULL PRIMARY KEY,
                place_id VARCHAR(100) NOT NULL,
                name VARCHAR(200) NOT NULL,
                category VARCHAR(50),
                address VARCHAR(300),
                latitude FLOAT NOT NULL,
                longitude FLOAT NOT NULL,
                phone VARCHAR(20),
                rating FLOAT,
                delivery_available BOOLEAN,
                delivery_fee INTEGER,
                minimum_order INTEGER,
                created_at DATETIME,
                updated_at DATETIME
            )
            """
        )
        connection.commit()
    finally:
        connection.close()


def test_create_app_upgrades_legacy_sqlite_restaurants_table():
    temp_dir = Path(__file__).resolve().parent / ".tmp"
    temp_dir.mkdir(exist_ok=True)
    db_path = temp_dir / f"legacy_foodfinder_{uuid.uuid4().hex}.db"
    app = None

    try:
        _create_legacy_restaurants_table(db_path)

        app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path.as_posix()}",
                "NAVER_CLIENT_ID": "test-id",
                "NAVER_CLIENT_SECRET": "test-secret",
                "NAVER_CLOUD_ID": "test-cloud-id",
                "NAVER_CLOUD_SECRET": "test-cloud-secret",
            }
        )

        with app.app_context():
            # Ensure SQLAlchemy engine was initialized and schema sync has run.
            db.session.execute(text("SELECT 1"))

        connection = sqlite3.connect(db_path)
        try:
            cursor = connection.cursor()
            cursor.execute("PRAGMA table_info(restaurants)")
            columns = {row[1] for row in cursor.fetchall()}
        finally:
            connection.close()

        assert "road_address" in columns
        assert "review_count" in columns
    finally:
        if db_path.exists():
            if app is not None:
                with app.app_context():
                    db.session.remove()
                    db.engine.dispose()
            db_path.unlink()
