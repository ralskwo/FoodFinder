import logging

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text

db = SQLAlchemy()
logger = logging.getLogger(__name__)

# Legacy local SQLite databases can miss columns that were added later.
_LEGACY_SQLITE_COLUMNS = {
    "restaurants": {
        "road_address": "VARCHAR(300)",
        "review_count": "INTEGER",
    }
}


def init_db(app):
    """Initialize SQLAlchemy for the Flask app."""
    db.init_app(app)
    return db


def ensure_sqlite_schema_compatibility():
    """
    Add missing nullable columns for legacy SQLite databases.

    `db.create_all()` creates missing tables but does not alter existing ones.
    """
    engine = db.engine
    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    with engine.begin() as connection:
        for table_name, column_defs in _LEGACY_SQLITE_COLUMNS.items():
            if table_name not in table_names:
                continue

            existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, column_type in column_defs.items():
                if column_name in existing_columns:
                    continue

                statement = text(
                    f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
                )
                connection.execute(statement)
                logger.info(
                    "Added missing SQLite column: %s.%s (%s)",
                    table_name,
                    column_name,
                    column_type,
                )
