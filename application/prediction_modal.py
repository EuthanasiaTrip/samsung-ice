from PySide6.QtWidgets import QDialog, QDialogButtonBox
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import QObject, Signal, QThread
import PySide6.QtCore as QtCore
from prediction_modal_view import Ui_Dialog
from PIL import Image
from PIL.ImageQt import ImageQt 
from osgeo import gdal
from skimage.exposure import rescale_intensity
import numpy as np
import cv2
import sys
from model_manager import RoboFlowModelManager, RCNNModelManager, YOLOModelManager
from ice_detector import IceDetector

class PredictionWorker(QObject):
    finished = Signal(tuple)
    progress = Signal(tuple)
    
    def __init__(self):
        super().__init__()
        self._is_cancelled = [False]

    def run(self):
        detector = IceDetector(self.ModelManager)
        image = self.image    

        result = detector.predict_image_large_callback(image, self._is_cancelled, progress_callback=self.handle_progress)

        detector.ModelManager = None
        self.finished.emit(result)

    def handle_progress(self, value, maxValue):        
        self.progress.emit((value, maxValue))

    def cancel(self):
        self._is_cancelled[0] = True

class PredictionModal(QDialog):
    ModelManager = None

    def __init__(self, parent=None):
        super(PredictionModal, self).__init__(parent)    

        self.is_worker_running = False    
        self.thread = None   
        self.worker = None 

        self.init_ui()    

        self.on_model_selected(0)       

    def init_ui(self):
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.setWindowTitle("Выбор модели")

        self.modelBoxValues = ["FasterRCNN", "YOLO", "RoboFlow"]
        self.modelManagers = [RCNNModelManager, YOLOModelManager, RoboFlowModelManager]
        self.ui.modelBox.addItems(self.modelBoxValues)        

        self.add_listeners()        

    def add_listeners(self):
        self.ui.buttonBox.clicked.connect(self.predict2)
        self.ui.modelBox.activated.connect(self.on_model_selected)

    def on_model_selected(self, index):
        print("model idx", index)
        self.ModelManager = self.modelManagers[index]

    def predict(self, button):
        print(button.text())
        if button.text() == "Cancel":
            self.rejected()
            return
        
        parent = self.parent()

        img = parent.image
        print(img)

        detector = IceDetector(self.ModelManager())

        self.ui.progressBar.setVisible(True)
     
        detected_img, boxes_mask = detector.predict_image_large(img, self.ui.progressBar)

        parent.set_img_fromarray(detected_img)
        parent.predicted_mask = boxes_mask        

        parent.update_save_buttons(True)

    def predict2(self, button):
        print(button.text())
        if button.text() == "Cancel":
            self.reject()
            return
        
        parent = self.parent()

        img = parent.image
        
        self.worker = PredictionWorker()
        self.thread = QThread()
        self.worker.image = img
        self.worker.ModelManager = self.ModelManager()

        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_prediction_finished)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self.on_thread_finished)

        self.worker.progress.connect(self.on_progress_change)

        self.ui.progressBar.setVisible(True)
        self.ui.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)
        self.is_worker_running = True
        self.thread.start()

    def on_prediction_finished(self, result):
        parent = self.parent()

        detected_img, boxes_mask = result
        if len(detected_img) > 0 and len(boxes_mask) > 0:
            parent.set_img_fromarray(detected_img)
            parent.predicted_mask = boxes_mask        

            parent.update_save_buttons(True)
        self.is_worker_running = False
        self.accept()

    def on_progress_change(self, values):
        value, maxValue = values
        if maxValue != self.ui.progressBar.maximum():
            self.ui.progressBar.setMaximum(maxValue)
        self.ui.progressBar.setValue(value)

    def cleanup_thread(self):
        if self.worker:
            self.worker.cancel()
        if self.thread and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait(3000)
            self.is_worker_running = False
        self.thread = None
        self.worker = None

    def on_thread_finished(self): 
        self.is_worker_running = False       
        self.thread = None
        self.worker = None

    def closeEvent(self, event):
        self.cleanup_thread()        
        super().closeEvent(event)

    def reject(self):
        self.cleanup_thread()
        super().reject()

    def accept(self):
        if not self.is_worker_running:
            return super().accept()


        
