import logging
import logging.config
from collections.abc import Mapping


GOOGLE_CALENDAR_OAUTH_CALLBACK_PATH = (
    "/api/v1/oauth/google-calendar/callback"
)


class OAuthCallbackAccessLogFilter(logging.Filter):
    """Remove OAuth callback query data from Uvicorn access records."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            args = record.args
            if (
                isinstance(args, tuple)
                and len(args) == 5
                and isinstance(args[2], str)
            ):
                request_target = args[2]
                if request_target == GOOGLE_CALENDAR_OAUTH_CALLBACK_PATH:
                    return True
                if request_target.startswith(
                    GOOGLE_CALENDAR_OAUTH_CALLBACK_PATH + "?"
                ):
                    sanitized = list(args)
                    sanitized[2] = GOOGLE_CALENDAR_OAUTH_CALLBACK_PATH
                    record.args = tuple(sanitized)
                    return True

            if self._contains_callback_target(record.msg):
                return False
            if self._contains_callback_target(args):
                return False
        except Exception:
            return False
        return True

    @classmethod
    def _contains_callback_target(cls, value: object) -> bool:
        if isinstance(value, str):
            return (
                GOOGLE_CALENDAR_OAUTH_CALLBACK_PATH + "?" in value
                or value == GOOGLE_CALENDAR_OAUTH_CALLBACK_PATH
            )
        if isinstance(value, tuple):
            return any(cls._contains_callback_target(item) for item in value)
        if isinstance(value, Mapping):
            return any(
                cls._contains_callback_target(item)
                for item in value.values()
            )
        return False


def _install_oauth_callback_access_log_filter() -> None:
    logger = logging.getLogger("uvicorn.access")
    if any(
        isinstance(item, OAuthCallbackAccessLogFilter)
        for item in logger.filters
    ):
        return
    logger.addFilter(OAuthCallbackAccessLogFilter())


def configure_logging(log_level: str) -> None:
    """Configure consistent, process-wide logging for API and server events."""
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                },
            },
            "root": {"handlers": ["console"], "level": log_level.upper()},
        }
    )
    _install_oauth_callback_access_log_filter()
