# -*- coding: utf-8 -*-
from PyQt6.QtCore import QObject, QRunnable, pyqtSignal
from moulinette import fetch_raw_csv, fetch_raw_igc
from logging_handler import  logger

class WorkerSignals(QObject):
    
    progress = pyqtSignal(int)      
    finished = pyqtSignal(dict)
    error = pyqtSignal(str) 
    
class MoulinetteWorker(QRunnable):

    def __init__(self, flight_dic):
        super().__init__()
        self.flight_dic = flight_dic
        self.signals = WorkerSignals()

    def run(self):
        try:
            if self.flight_dic["origin_file_path"].suffix == ".csv":
                logger.info(f"Analyzing {self.flight_dic['file_name']}")
                self.flight_dic['data'] = fetch_raw_csv(self.flight_dic, self.signals.progress)
    
            elif self.flight_dic["origin_file_path"].suffix == ".IGC":
                logger.info(f"Analyzing {self.flight_dic['file_name']}")
                self.flight_dic['data'] = fetch_raw_igc(self.flight_dic, self.signals.progress)
            
            self.signals.finished.emit(self.flight_dic)
            
    
        except Exception as e:
            self.flight_dic['is_data_processed'] = False
            self.signals.error.emit(str(e))