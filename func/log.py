"""
Console logging through the standard `logging` module.

The generator logs to the "data_generator" logger, which has no output of its own (a NullHandler), so the web app,
tests and scripts stay quiet. The command line calls configure() once to print timestamped, coloured lines.
"""
import logging
import sys

from colorama import Fore, Style, just_fix_windows_console

logger = logging.getLogger("data_generator")
logger.addHandler(logging.NullHandler())

LEVEL_WIDTH = 7
SUCCESS = 25  # between INFO and WARNING
logging.addLevelName(SUCCESS, "SUCCESS")
LEVEL_COLORS = {logging.INFO: Fore.WHITE, SUCCESS: Fore.GREEN, logging.WARNING: Fore.YELLOW,
                logging.ERROR: Fore.LIGHTRED_EX}
METRIC_LABEL_WIDTH = 42


class ConsoleFormatter(logging.Formatter):
    """`  12:34:56  INFO     message`, with the level (and section titles) in colour when the stream is a terminal."""

    def __init__(self, color: bool) -> None:
        super().__init__(datefmt="%H:%M:%S")
        self.color = color

    def paint(self, text: str, color: str) -> str:
        return f"{color}{text}{Style.RESET_ALL}" if self.color else text

    def format(self, record: logging.LogRecord) -> str:
        time = self.paint(self.formatTime(record, self.datefmt), Fore.LIGHTBLACK_EX)
        level = self.paint(f"{record.levelname:<{LEVEL_WIDTH}}", LEVEL_COLORS.get(record.levelno, Fore.WHITE))
        message = record.getMessage()
        if getattr(record, "section", False):
            message = self.paint(message, Fore.CYAN)
        return f"  {time}  {level}  {message}"


def configure(level: int = logging.INFO, stream=None) -> logging.Handler:
    """
    Print the generator's log to a stream (stdout by default). Calling it again replaces the handler, so every line
    is printed once.

    Returns:
    logging.Handler: The handler that was added.
    """
    stream = stream or sys.stdout
    just_fix_windows_console()
    for handler in [h for h in logger.handlers if not isinstance(h, logging.NullHandler)]:
        logger.removeHandler(handler)
    handler = logging.StreamHandler(stream)
    handler.setFormatter(ConsoleFormatter(color=hasattr(stream, "isatty") and stream.isatty()))
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return handler


def log_info(message: str) -> None:
    logger.info(message)


def log_success(message: str) -> None:
    logger.log(SUCCESS, message)


def log_section(title: str) -> None:
    """A section title, shown in colour."""
    logger.info(title, extra={"section": True})


def log_metric(label: str, value: object) -> None:
    """One aligned `label: value` line under a section."""
    logger.info(f"  {label + ':':<{METRIC_LABEL_WIDTH}} {value}")
