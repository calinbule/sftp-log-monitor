import os
import sqlite3
from flask import g, current_app
from app_modules.logger_config import setup_logger
from app_modules.populate_db import populate_sftp_settings


logger = setup_logger('database')


def setup_database(app):
    """Setup database configuration for the Flask app"""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    database_dir = os.path.join(project_root, 'database')
    app.instance_path = database_dir
    os.makedirs(app.instance_path, exist_ok=True)
    app.teardown_appcontext(close_db)

    with app.app_context():
        init_db()


def get_db():
    if 'db' not in g:
        try:
            logger.debug("Creating new database connection")
            g.db = sqlite3.connect(
                os.path.join(current_app.instance_path, 'settings.db'),
                detect_types=sqlite3.PARSE_DECLTYPES
            )
            g.db.row_factory = sqlite3.Row
            logger.info("Database connection established successfully")
        except Exception as e:
            logger.error(f"Failed to connect to database: {str(e)}", exc_info=True)
            raise
    return g.db


def close_db(e=None):
    try:
        db = g.pop('db', None)
        if db is not None:
            db.close()
            logger.debug("Database connection closed")
    except Exception as e:
        logger.error(f"Error closing database connection: {str(e)}", exc_info=True)


def init_db():
    try:
        logger.info("Initializing database")
        db = get_db()
        db.execute('''
            CREATE TABLE IF NOT EXISTS sftp_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hostname TEXT NOT NULL,
                port INTEGER NOT NULL,
                username TEXT NOT NULL,
                password TEXT NOT NULL,
                remote_dir TEXT NOT NULL
            )
        ''')
        db.commit()
        logger.info("Database initialized successfully")

        # Check if database should be populated
        should_populate = os.getenv('POPULATE_DB', 'False').lower() == 'true'
        if should_populate:
            logger.info("POPULATE_DB is True, populating database with initial data")
            populate_sftp_settings()

    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}", exc_info=True)
        raise