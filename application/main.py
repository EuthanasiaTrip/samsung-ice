from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox
from PyQt6.QtGui import QPixmap, QImage
from view import Ui_Dialog
from PIL import Image, ImageQt
from inference import get_model
import numpy as np
import cv2
import sys
from ultralytics import YOLO

class MainWindow(QMainWindow):
    model = None

    def __init__(self):
        super(MainWindow, self).__init__()

        self.init_ui()
        

    def init_ui(self):
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.ui.label.setText('')

        self.add_listeners()

    def add_listeners(self):
        self.ui.pushButton.clicked.connect(self.open_file_dialog)
        self.ui.pushButton_2.clicked.connect(self.predict)

    def open_file_dialog(self):
        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle("Open File")
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setViewMode(QFileDialog.ViewMode.Detail)
        file_dialog.setNameFilter("Image files (*.png *.tif *.tiff *.jpg)")

        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            self.load_image(selected_files[0])

    def load_image(self, img_path):
        image = Image.open(img_path)
        self.pixmap = QPixmap(img_path)
        self.ui.label.setPixmap(self.pixmap)

    def predict(self):
        if not self.model:
            self.model = YOLO("D:\snap data\yolov12s\yolo11m.pt")

        self.inference_img_roboflow()

    def inference_img_roboflow(self):
        if not self.pixmap:
            raise Exception("Image not loaded")

        image = ImageQt.fromqimage(self.pixmap)
        image = np.asarray(image)

        if len(image.shape) != 3:
            image = np.stack((image,)*3, axis=-1)

        results = self.model.infer(image)[0]

        box_image = image.copy()

        msgBox = QMessageBox()
        msgBox.setText(f"Найдено айсбергов: {len(results.predictions)}")
        msgBox.exec()

        for box in results.predictions:            

            x1 = box.x - box.width/2
            y1 = box.y - box.height/2
            x2 = box.x + box.width/2
            y2 = box.y + box.height/2

            print(x1, '-', y1, ' ', x2, '-', y2)

            x1 = int(x1)
            y1 = int(y1)
            x2 = int(x2)
            y2 = int(y2)

            score = box.confidence
            label = box.class_name

            color = self.map_color_to_prob(score * 100)
            cv2.rectangle(box_image, (x1, y1), (x2,y2), color, 2)
            print(f'{score:.2f} {label}')
            # cv2.putText(box_image, f'{score:.2f}', (x1-50, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
        
        height, width, channel = box_image.shape
        bytesPerLine = 3 * width
        qImg = QImage(box_image.data, width, height, bytesPerLine, QImage.Format.Format_RGB888)

        self.pixmap = QPixmap.fromImage(qImg)
        self.ui.label.setPixmap(self.pixmap)

    def map_color_to_prob(self, prob_value):
        if(prob_value > 45):
            return (0, 255, 0)
        if(prob_value > 30 and prob_value <= 45):
            return (181, 255, 0)
        if(prob_value > 15 and prob_value <= 30):
            return (255, 189, 0)
        if(prob_value > 5 and prob_value <= 15):
            return (255, 111, 0)
        if(prob_value > 0 and prob_value <= 5):
            return (255, 0, 0)
        

if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())