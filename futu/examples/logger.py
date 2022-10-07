import logging
import logging.handlers

file_handler = None
stream_handler = None


class Logger:
    def __init__(self, filename, rotate=False, logger=None):
        global file_handler, stream_handler

        self.logger = logging.getLogger(logger)
        self.logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('[%(asctime)s]%(message)s')

        if file_handler is not None:
            self.logger.removeHandler(file_handler)
        if rotate:
            file_handler = logging.handlers.TimedRotatingFileHandler(filename=filename, encoding='utf-8', when='H', interval=3, backupCount=16)
            file_handler.suffix = '%Y-%m-%d_%H.log'
        else:
            file_handler = logging.FileHandler(filename=filename, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        if stream_handler is not None:
            self.logger.removeHandler(stream_handler)
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.DEBUG)
        stream_handler.setFormatter(formatter)
        self.logger.addHandler(stream_handler)

    def get_logger(self):
        return self.logger
