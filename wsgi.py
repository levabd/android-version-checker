# -*- coding: utf-8 -*-

import logging.handlers
import os
from android_version_checker import app

if __name__ == "__main__":
    handler = logging.handlers.RotatingFileHandler(
        os.path.dirname(os.path.abspath(__file__)) +
        '/logs/android_version_checker.log',
        maxBytes=10000,
        backupCount=1)
    formatter = logging.Formatter(
        "[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s")
    handler.setLevel(logging.INFO)
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)
    app.logger.info('Android app version checker started on port 5005')
    app.run()