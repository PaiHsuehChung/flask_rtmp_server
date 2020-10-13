  
import logging
import sys


def get_logger():
    logger = logging.getLogger(__name__)

    if len(logger.handlers) == 0:
        logger.setLevel(logging.DEBUG)

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s : %(process)d - %(module)s - %(funcName)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger