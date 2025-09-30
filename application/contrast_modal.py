from PySide6.QtWidgets import QDialog
from PySide6.QtGui import QPixmap, QImage
from contrast_modal_view import Ui_Dialog
from PIL import Image
from PIL.ImageQt import ImageQt 
from osgeo import gdal
from skimage.exposure import rescale_intensity
import numpy as np
import cv2
import sys
from model_manager import RoboFlowModelManager, RCNNModelManager, YOLOModelManager
from ice_detector import IceDetector

class ContrastModal(QDialog):
    def __init__(self, parent=None):
        super(ContrastModal, self).__init__(parent)        

        self.init_ui()

    def init_ui(self):
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.setWindowTitle("Контрастность")

        self.add_listeners()

    def add_listeners(self):
        self.ui.buttonBox.accepted.connect(self.update_contrast)

    def update_contrast(self):
        parent = self.parent()
        
        value = self.ui.contrastSlider.value()

        parent.update_contrast(value)
        