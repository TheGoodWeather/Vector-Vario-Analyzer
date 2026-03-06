# -*- coding: utf-8 -*-
from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtCore import Qt

class MoulinetteWorker(QObject):
    
    progress = pyqtSignal(int)      # % progression
    finished = pyqtSignal()         # fin du traitement
  
    def __init__(self, data, rows_to_analyze):
        super().__init__()
        self.data = data
        self.rows = rows_to_analyze
        self._is_running = True

    def run(self):
        total = len(self.rows)

        for i, row in enumerate(self.rows):
            if not self._is_running:
                break

            flight = self.data[row]

            if flight["origin_file_path"].suffix == ".csv":
                fetch_raw_csv(flight)   # ⚠️ ton traitement lourd

            progress = int((i + 1) / total * 100)
            self.progress.emit(progress)

        self.finished.emit()

    def stop(self):
        self._is_running = False