import sys
from loguru import logger as lg
from os.path import dirname

from settings import STD_OUT_LOG_LEVER, FILE_LOG_LEVER


def get_logger():
    log_config = {
        "handlers": [
            {
                "sink": sys.stdout,
                "format": "{time:YYYY-MM-DD HH:mm:ss} |  {file}:{line} |({level}){message}",
                "level": STD_OUT_LOG_LEVER,
            },
            {
                "sink": dirname(__file__) + "/log.log",
                "format": "{time:YYYY-MM-DD HH:mm:ss} | {level} | {file}:{line} | {message}",
                "enqueue": True,
                "rotation": "500 MB",
                "level": FILE_LOG_LEVER,
                "encoding": "utf-8",
            },
        ]
    }
    lg.configure(**log_config)
    return lg


logger = get_logger()
