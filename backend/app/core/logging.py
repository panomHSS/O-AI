import logging
import logging.config


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
