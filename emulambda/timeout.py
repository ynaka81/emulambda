from functools import wraps
import errno
import os
import sys

import signal
#Signal module doesn't work
if sys.platform=='win32':
    import wtimeout

class TimeoutError(Exception):
    pass


def timeout(seconds=2147483647, error_message='Timer Expired'):
    def decorator(func):
        if sys.platform=='win32':
            def wrapper(*args, **kwargs):
                timer=wtimeout.Ticker(seconds)
                timer.start()
                was_set=False
                try:
                    result=func(*args, **kwargs)
                except Exception as e:
                    timer.stop()
                    timer.join()
                    raise e
                was_set=timer.consume()
                timer.stop()
                timer.join()
                if (was_set):
                   raise TimeoutError(error_message)
                return result

        else:
            def wrapper(*args, **kwargs):
                signal.signal(signal.SIGALRM, _handle_timeout)
                signal.alarm(seconds)
                try:
                    result = func(*args, **kwargs)
                finally:
                    signal.alarm(0)
                return result

            def _handle_timeout(signum, frame):
                raise TimeoutError(error_message)

        return wraps(func)(wrapper)

    return decorator
