import os
import logging
import logging.config
import json
from datetime import datetime

import yaml

API_KEY = os.getenv("API_KEY")


# Logging
class MaxLevelFilter(logging.Filter):
    def __init__(self, max_level):
        super().__init__()
        self.max_level = max_level

    def filter(self, record):
        # Only allow records <= max_level 30 warning, 40, error, 50 crit
        return record.levelno <= self.max_level


class JsonFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):  # Override
        dt = datetime.fromtimestamp(record.created)
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    def format(self, record):
        log_record = {
            "time": self.formatTime(record),
            "level": record.levelname,
            "name": record.name,
            "lineno": record.lineno,
            "message": record.getMessage(),
        }
        for key in ("vendor_id", "method", "url", "params", "client_ip", "status_code"):
            if hasattr(record, key):
                log_record[key] = getattr(record, key)  # retrieve value of key in extra
        return json.dumps(log_record, indent=4)


def setup_logging():
    with open("./api/app/config/logging.yaml", "rt") as f:
        config = yaml.safe_load(f.read())
    logging.config.dictConfig(config)
