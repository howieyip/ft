import logging
from logging.handlers import TimedRotatingFileHandler
import sys

class Logger:
    def __init__(self, log_file, log_level=logging.DEBUG, when="D", interval=1, backup_count=30, stream_output=True):
        self.logger = logging.getLogger(log_file)
        self.logger.setLevel(log_level)

        # 移除现有的文件处理器
        for handler in self.logger.handlers:
            if isinstance(handler, TimedRotatingFileHandler):
                self.logger.removeHandler(handler)

        # 添加新的文件处理器
        file_handler = TimedRotatingFileHandler(log_file, when=when, interval=interval, backupCount=backup_count)
        file_formatter = logging.Formatter("[%(asctime)s]%(message)s")
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

        # 移除现有的流处理器
        for handler in self.logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                self.logger.removeHandler(handler)

        # 添加新的流处理器（可选）
        if stream_output:
            stream_handler = logging.StreamHandler(sys.stdout)
            stream_formatter = logging.Formatter("[%(asctime)s]%(message)s")
            stream_handler.setFormatter(stream_formatter)
            self.logger.addHandler(stream_handler)

    def get_logger(self):
        return self.logger
