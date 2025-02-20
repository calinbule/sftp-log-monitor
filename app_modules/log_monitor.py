import os
import time
from datetime import datetime
import paramiko
from app_modules.database import get_db
from app_modules.logger_config import setup_logger

logger = setup_logger('log_monitor')

class LogMonitor:
    def __init__(self, log_file, output_queue):
        """Initialize LogMonitor instance"""
        logger.info(f"Initializing LogMonitor for log type: {log_file}")
        self.setup_configuration(log_file, output_queue)
        self.ensure_log_directory()

    def setup_configuration(self, log_file, output_queue):
        """Setup monitor configuration from database"""
        try:
            settings = get_db().execute('SELECT * FROM sftp_settings').fetchone()
            if not settings:
                raise ValueError("No SFTP settings found in database")

            # SFTP settings
            self.sftp_config = {
                'hostname': settings['hostname'],
                'port': int(settings['port']),
                'username': settings['username'],
                'password': settings['password']
            }

            # Path settings
            self.remote_path = f"{settings['remote_dir']}/{log_file}"
            self.local_path = f'logs/{log_file}'

            # Monitoring state
            self.output_queue = output_queue
            self.last_content = None
            self.initial_load = True
            self.batch_counter = 0
            self.is_paused = False

            logger.debug(f"Configuration set - Remote: {self.remote_path}, Local: {self.local_path}")
        except Exception as e:
            logger.error(f"Configuration setup failed: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def ensure_log_directory():
        """Ensure logs directory exists"""
        if not os.path.exists('logs'):
            logger.info("Creating local logs directory")
            os.makedirs('logs')

    @staticmethod
    def get_available_logs():
        """Get available log files from SFTP server"""
        logger.debug("Fetching available logs from SFTP server")
        sftp_client = None
        transport = None

        try:
            # Read and process LOG_EXTENSIONS from .env
            env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
            if not os.path.exists(env_path):
                logger.warning("No .env file found. Using default log extensions")
                extensions = ['log']  # Default fallback
            else:
                with open(env_path, 'r') as env_file:
                    for line in env_file:
                        if line.startswith('LOG_EXTENSIONS='):
                            extensions_str = line.strip().split('=')[1]
                            extensions = [ext.strip() for ext in extensions_str.split(',')]
                            break
                    else:
                        logger.warning("LOG_EXTENSIONS not found in the .env file. Using default log extensions")
                        extensions = ['log']  # Default fallback

            settings = get_db().execute('SELECT * FROM sftp_settings').fetchone()
            if not settings:
                logger.warning("No SFTP settings found")
                return []

            transport = paramiko.Transport((settings['hostname'], settings['port']))
            transport.connect(username=settings['username'], password=settings['password'])
            sftp_client = paramiko.SFTPClient.from_transport(transport)

            # Modified file filtering to handle multiple extensions
            logger.info(f"The logs folder is: {settings['remote_dir']}")
            files = []
            for f in sftp_client.listdir(settings['remote_dir']):
                if any(f.endswith(f'.{ext}') for ext in extensions):
                    files.append(f)

            return files

        except Exception as e:
            logger.error(f"Error fetching available logs: {str(e)}", exc_info=True)
            return []
        finally:
            LogMonitor.close_connections(sftp_client, transport)


    @staticmethod
    def close_connections(sftp_client=None, transport=None):
        """Safely close SFTP connections"""
        try:
            if sftp_client:
                sftp_client.close()
            if transport:
                transport.close()
            logger.debug("SFTP connections closed")
        except Exception as e:
            logger.error(f"Error closing connections: {str(e)}", exc_info=True)

    def format_message(self, message):
        """Format message with timestamp"""
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        return f"<{timestamp}> {message}"

    def handle_file_operations(self, sftp):
        """Handle file download and content reading"""
        try:
            sftp.get(self.remote_path, self.local_path)

            if self.initial_load:
                initial_lines = self.read_file_lines(self.local_path, 100)
                self.batch_counter += 1
                self.output_queue.put(self.format_message(f"Printing batch {self.batch_counter}"))
                for line in initial_lines:
                    self.output_queue.put(line.rstrip())
                self.initial_load = False

            current_content = self.read_file_content(self.local_path)
            return current_content

        except Exception as e:
            logger.error(f"File operation error: {str(e)}", exc_info=True)
            self.output_queue.put(self.format_message(f"Error: {str(e)}"))
            return None

    def read_file_lines(self, file_path, n):
        """Read last n lines from file"""
        try:
            with open(file_path, 'r') as file:
                lines = file.readlines()
                return lines[-n:] if len(lines) > n else lines
        except Exception as e:
            logger.error(f"Error reading lines: {str(e)}", exc_info=True)
            return []

    def read_file_content(self, file_path):
        """Read entire file content"""
        try:
            with open(file_path, 'r') as file:
                return file.read()
        except Exception as e:
            logger.error(f"Error reading content: {str(e)}", exc_info=True)
            return None

    def monitor(self, should_stop):
        """Main monitoring loop"""
        logger.info("Starting monitoring process")
        sftp_client = None
        transport = None

        try:
            transport = paramiko.Transport((self.sftp_config['hostname'], self.sftp_config['port']))
            transport.connect(username=self.sftp_config['username'],
                            password=self.sftp_config['password'])
            sftp_client = paramiko.SFTPClient.from_transport(transport)

            self.output_queue.put(self.format_message(f"Connected to {self.sftp_config['hostname']}"))
            self.last_content = self.handle_file_operations(sftp_client)

            while not should_stop():
                if not self.is_paused:
                    current_content = self.handle_file_operations(sftp_client)
                    if current_content and current_content != self.last_content:
                        new_content = current_content[len(self.last_content):] if self.last_content else current_content
                        if new_content.strip():
                            self.batch_counter += 1
                            self.output_queue.put(self.format_message(f"Printing batch {self.batch_counter}"))
                            self.output_queue.put(new_content.rstrip())
                        self.last_content = current_content

                time.sleep(int(os.environ.get("SLEEP_BETWEEN_LOG_CHECKS", 5)))

        except Exception as e:
            logger.error(f"Monitoring error: {str(e)}", exc_info=True)
            self.output_queue.put(self.format_message(f"Error: {str(e)}"))
        finally:
            self.close_connections(sftp_client, transport)
            self.output_queue.put(self.format_message("Monitoring stopped"))
