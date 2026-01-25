from flask import Flask
from flask_cors import CORS
from backend.database import db, init_db
from backend.config import Config


def create_app(config_override=None):
    """Flask 애플리케이션 팩토리"""
    app = Flask(__name__)

    # 설정 로드
    app.config.from_object(Config)
    if config_override:
        app.config.update(config_override)

    # CORS 설정
    CORS(app)

    # 데이터베이스 초기화
    init_db(app)

    # 블루프린트 등록
    from backend.api.restaurant import restaurant_bp
    app.register_blueprint(restaurant_bp, url_prefix='/api')

    # 헬스 체크
    @app.route('/api/health')
    def health():
        return {'status': 'ok'}, 200

    return app


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
