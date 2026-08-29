import logging
from logging.config import dictConfig


def setup_logging():
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": "ext://sys.stdout",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "detailed",
                "filename": "app.log",  # The name of your log file
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,  # Keep 5 old log files
                "encoding": "utf8",
            },
        },
        "loggers": {
            "watchfiles.main": {
                "handlers": ["console"],  # Only log to console if something breaks
                "level": "WARNING",  # Ignore INFO 'change detected' logs
                "propagate": False,
            },
            # This captures all logs from your 'app' package
            "app": {
                "handlers": ["console", "file"],
                "level": "INFO",  # Changed to DEBUG to see all errors
                "propagate": False,
            },
            "uvicorn": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False,
            },
            "sqlalchemy.engine": {"handlers": ["file"], "level": "WARNING"},
        },
        # "root": {
        #     "handlers": ["console", "file"],
        #     "level": "DEBUG",  # Changed to DEBUG to see all errors
        # },
    }
    dictConfig(logging_config)
