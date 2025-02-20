import sqlite3
import os
from datetime import datetime
from dotenv import load_dotenv
from app_modules.logger_config import setup_logger

logger = setup_logger('populate_db')

def setup_database_connection():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    database_dir = os.path.join(project_root, 'database')
    db_path = os.path.join(database_dir, 'settings.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def populate_sftp_settings():
    conn = None
    try:
        # Load environment variables from .env file
        load_dotenv()

        # Get settings from environment variables
        settings = {
            'hostname': os.getenv('SFTP_HOSTNAME'),
            'port': int(os.getenv('SFTP_PORT', 22)),
            'username': os.getenv('SFTP_USERNAME'),
            'password': os.getenv('SFTP_PASSWORD'),
            'remote_dir': os.getenv('SFTP_REMOTE_DIR')
        }

        # Validate that all required settings are present
        missing_vars = [k for k, v in settings.items() if v is None]
        if missing_vars:
            error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
            logger.error(error_msg)
            return False

        conn = setup_database_connection()
        cursor = conn.cursor()

        # Clear existing settings and insert new ones
        cursor.execute('DELETE FROM sftp_settings')
        cursor.execute('''
            INSERT INTO sftp_settings (hostname, port, username, password, remote_dir)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            settings['hostname'],
            settings['port'],
            settings['username'],
            settings['password'],
            settings['remote_dir']
        ))

        conn.commit()
        logger.info("Database populated successfully")
        return True

    except Exception as e:
        logger.error(f"Error populating database: {str(e)}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    populate_sftp_settings()
