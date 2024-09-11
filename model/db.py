import time
import logging
from functools import wraps
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


def retry_on_timeout(max_retries=3, delay=5):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except (OperationalError, TimeoutError) as err:
                    if retries < max_retries:
                        retries += 1
                        logging.warning(f"Operation failed: {err}. Retrying {retries}/{max_retries} in {delay} seconds...") # noqa
                        time.sleep(delay)
                    else:
                        logging.error(f"Operation failed after {max_retries} retries: {err}") # noqa
                        raise
        return wrapper
    return decorator
