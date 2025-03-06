import logging
import os
import queue
from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtCore import QObject, pyqtSignal

LOADING = 24
SUCCESS = 25
logging.addLevelName(LOADING, "LOADING")
logging.addLevelName(SUCCESS, "SUCCESS")


if not os.path.exists("logs"):
    os.mkdir("logs")

def loading(self, message, *args, **kwargs):
    if self.isEnabledFor(LOADING):
        self._log(LOADING, message, args, **kwargs)

def success(self, message, *args, **kwargs):
    if self.isEnabledFor(SUCCESS):
        self._log(SUCCESS, message, args, **kwargs)


logging.Logger.loading = loading
logging.Logger.success = success

logging.basicConfig(level=logging.INFO)


class CustomFormatter(logging.Formatter):
    green = "\033[1;92m"
    yellow = "\033[1;93m"
    red = "\033[1;31m"
    purple = "\033[1;35m"
    blue = "\033[1;94m"
    reset = "\033[0m"
    format = "%(asctime)s - %(levelname)s - %(name)s - %(message)s "

    FORMATS = {
        logging.DEBUG: blue + format + reset,
        logging.INFO: blue + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: red + format + reset,
        LOADING: purple + format + reset,
        SUCCESS: green + format + reset,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


class QtSignalHandler(QObject):
    log_signal = pyqtSignal(str)

class GuiLogHandler(logging.Handler):
    def __init__(self, text_widget: QTextEdit):
        super().__init__()
        self.text_widget = text_widget
        self.queue = queue.Queue()
        self.signal_handler = QtSignalHandler()
        self.signal_handler.log_signal.connect(self.update_text_widget)
        
        # Formatierung für verschiedene Log-Level
        self.level_formats = {
            logging.DEBUG: ('<span style="color: #808080;">', '</span>'),  # Grau
            logging.INFO: ('<span style="color: #FFFFFF;">', '</span>'),   # Weiß
            logging.WARNING: ('<span style="color: #FFA500;">', '</span>'), # Orange
            logging.ERROR: ('<span style="color: #FF0000;">', '</span>'),   # Rot
            logging.CRITICAL: ('<span style="color: #FF0000; font-weight: bold;">', '</span>'), # Fett Rot
        }

    def emit(self, record):
        try:
            msg = self.format(record)
            level_format = self.level_formats.get(record.levelno, ('', ''))
            formatted_msg = f"{level_format[0]}{msg}{level_format[1]}"
            self.signal_handler.log_signal.emit(formatted_msg)
        except Exception:
            self.handleError(record)

    def update_text_widget(self, message):
        self.text_widget.append(message)
        # Scrolle automatisch nach unten
        self.text_widget.verticalScrollBar().setValue(
            self.text_widget.verticalScrollBar().maximum()
        )

def setup_logger(name=None):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    return logger
