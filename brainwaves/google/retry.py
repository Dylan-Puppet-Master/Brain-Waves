"""Trying again when Google is briefly unwell.

Google answers a small share of requests with 429, 500, 502, 503 or 504, and the network
drops out on its own account. None of those mean the request was wrong, so none of them
should reach a village leader as an error.

Only operations that can be repeated safely go through here: reading anything, and writing
cells, which puts the same values in the same places however many times it runs. Posting a
comment does not, because a second attempt would post it twice.
"""

import time

TRANSIENT_CODES = frozenset({429, 500, 502, 503, 504})
ATTEMPTS = 4
FIRST_PAUSE = 0.5


def retrying(call, attempts: int = ATTEMPTS, pause: float = FIRST_PAUSE):
    """Run `call`, trying again after a longer wait each time Google is briefly unwell."""
    for attempt in range(attempts):
        try:
            return call()
        except Exception as error:  # noqa: BLE001 - re-raised unless it is worth retrying
            if attempt == attempts - 1 or not is_transient(error):
                raise
            time.sleep(pause * 2**attempt)
    return None


def is_transient(error: Exception) -> bool:
    """Whether an error says to try again rather than that the request was wrong."""
    status = http_status(error)
    if status is not None:
        return status in TRANSIENT_CODES
    return isinstance(error, OSError)  # a dropped connection or a timeout


def http_status(error: Exception) -> int | None:
    """The HTTP status, however the library that raised it happens to carry one."""
    for holder, name in (("response", "status_code"), ("resp", "status")):
        code = getattr(getattr(error, holder, None), name, None)
        if code is not None:
            try:
                return int(code)
            except (TypeError, ValueError):
                return None
    return None
