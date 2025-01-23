import logging


def configure_logger(logfile_full: str) -> None:
    """Simple logger configuration."""
    logging.basicConfig(
        format='%(name)s - %(levelname)s - %(message)s',
        level=logging.INFO,
        handlers=[
            logging.FileHandler(logfile_full, mode="w"),
            # Excluding the stderr stream for logging messages for now
            # logging.StreamHandler()
        ]
    )

    return None
