from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def init_db(app):
    """데이터베이스 초기화"""
    db.init_app(app)
    return db
