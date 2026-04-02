from PyQt6 import QtWidgets, QtCore


class DropZone(QtWidgets.QLabel):
    fileDropped = QtCore.pyqtSignal(str)  # signal avec le chemin du fichier

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setText("Drop CSV or IGC file here")
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed gray;
                font-size: 14px;
                padding: 20px;
            }
        """)

        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()

        if urls:
            file_path = urls[0].toLocalFile()

            if file_path.endswith(".csv"):
                self.fileDropped.emit(file_path)
            elif file_path.endswith(".igc"):
                self.fileDropped.emit(file_path)
            elif file_path.endswith(".IGC"):
                self.fileDropped.emit(file_path)
            else:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Invalid file",
                    "File supported : .IGC or .CSV"
                )