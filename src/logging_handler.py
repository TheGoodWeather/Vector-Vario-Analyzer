# -*- coding: utf-8 -*-
"""
Created on Sat Jun 14 18:15:25 2025

@author: Utilisateur
"""
import logging
import sys
from pathlib import Path
from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtCore import QObject, pyqtSignal


DETAIL_LEVEL = 15


logging.addLevelName(DETAIL_LEVEL, "DETAIL")
def detail(self, message, *args, **kwargs):
    if self.isEnabledFor(DETAIL_LEVEL):
        self._log(DETAIL_LEVEL, message, args, **kwargs)

logging.Logger.detail = detail  # Add to Logger class


# --- Determine base path where .exe lives or script runs ---
if getattr(sys, 'frozen', False):
    base_path = Path(sys.executable).parent
else:
    base_path = Path(__file__).parent

log_file = base_path / "log.log"




# --- Configure base logger ---
logger = logging.getLogger("__name__")
logger.setLevel(logging.DEBUG)  # Capture everything

if not logger.handlers: #Used to prevent multiple instance of logger
    # --- File Handler ---
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    #logger.addHandler(file_handler)
    
    


#Create a specific handlfer for streaming logs into the Qtextedit widget
class QTextEditLogger(logging.Handler, QObject):
    log_signal = pyqtSignal(str)

    def __init__(self, text_edit: QTextEdit):
        logging.Handler.__init__(self)
        QObject.__init__(self)
        self.text_edit = text_edit
        self.setLevel(logging.INFO)  # Only show DETAIL and above in UI
        self.log_signal.connect(self.append_to_widget)
        self.setFormatter(logging.Formatter('[%(asctime)s]: %(message)s', "%H:%M:%S"))

    def emit(self, record):
        msg = self.format(record)
        html_msg = self.format_with_color(record, msg)
        self.log_signal.emit(html_msg)

    def append_to_widget(self, msg: str):
        if self.text_edit:  # Only write if still alive
            self.text_edit.append(msg)
        
    def format_with_color(self, record, msg: str) -> str:
        """Return an HTML-formatted string with color based on log level"""
        level = record.levelno
        color = {
            logging.DEBUG: "#808080",     # gray
            DETAIL_LEVEL: "#000000",
            logging.INFO: "#000000",      # black
            logging.WARNING: "#e68a00",   # orange
            logging.ERROR: "#cc0000",     # red
            logging.CRITICAL: "#800000",  # dark red
        }.get(level, "#000000")
        
        return f'<span style="color:{color};">[{record.levelname}] {msg}</span>'