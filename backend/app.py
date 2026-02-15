import os

from flask import Flask, jsonify
from flask_cors import CORS

from config import Config
from database import db, ensure_sqlite_schema_compatibility, init_db


def create_app(config_override=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)

    app.config.from_object(Config)
    if config_override:
        app.config.update(config_override)

    CORS(app, resources={r"/api/*": {"origins": app.config.get("CORS_ORIGINS", "*")}})

    init_db(app)

    from api.restaurant import restaurant_bp

    app.register_blueprint(restaurant_bp, url_prefix="/api")

    # Ensure all models are imported before create_all.
    with app.app_context():
        import models  # noqa: F401

        db.create_all()
        ensure_sqlite_schema_compatibility()
        try:
            from services.menu_service import MenuService

            repaired = MenuService().repair_recent_menu_names(limit=5000)
            if repaired:
                app.logger.warning("Repaired %s mojibake menu names on startup", repaired)
        except Exception as exc:
            app.logger.warning("Startup menu-name repair skipped: %s", exc)

    @app.route("/api/health")
    def health():
        return {"status": "ok"}, 200

    if app.config.get("DEBUG"):

        @app.route("/api/debug/config")
        def debug_config():
            naver_client_id = app.config.get("NAVER_CLIENT_ID")
            naver_cloud_id = app.config.get("NAVER_CLOUD_ID")
            naver_cloud_secret = app.config.get("NAVER_CLOUD_SECRET")
            return jsonify(
                {
                    "NAVER_CLIENT_ID": (
                        f"{naver_client_id[:5]}..." if naver_client_id else "None"
                    ),
                    "NAVER_CLOUD_ID": (
                        f"{naver_cloud_id[:5]}..." if naver_cloud_id else "None"
                    ),
                    "NAVER_CLOUD_SECRET_LEN": (
                        len(naver_cloud_secret) if naver_cloud_secret else 0
                    ),
                    "CWD": os.getcwd(),
                }
            )

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(
        debug=app.config.get("DEBUG", False),
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
    )
