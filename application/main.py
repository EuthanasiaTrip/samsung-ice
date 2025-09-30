from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox, QDialogButtonBox
from PySide6.QtGui import QPixmap, QImage
from view import Ui_MainWindow
from prediction_modal import PredictionModal
from contrast_modal import ContrastModal
from PIL import Image
from PIL.ImageQt import ImageQt 
from osgeo import gdal, ogr
from skimage.exposure import rescale_intensity
import numpy as np
import sys
import time
import datetime

class MainWindow(QMainWindow):
    DEFAULT_CONTRAST_VALUE = 97e4

    def __init__(self):
        super(MainWindow, self).__init__()

        self.image = None
        self.predicted_mask = None
        self.is_tiff = False

        self.init_ui()

        self.prediction_modal = PredictionModal(self)
        self.contrast_modal = ContrastModal(self)
        self.contrast_value = self.DEFAULT_CONTRAST_VALUE
        

    def init_ui(self):
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.label.setText('')
        self.setWindowTitle("Детектор айсбергов")

        self.ui.findIcebergsButton.setEnabled(False)
        self.ui.contrastMenuButton.setEnabled(False)
        self.update_save_buttons(False)

        self.add_listeners()

    def add_listeners(self):
        self.ui.selectFileButton.clicked.connect(self.open_file_dialog)
        self.ui.findIcebergsButton.clicked.connect(self.open_modal)
        self.ui.contrastMenuButton.clicked.connect(self.open_contrast_modal)
        self.ui.saveShpButton.clicked.connect(self.save_shp_button_click)
        self.ui.saveTiffButton.clicked.connect(self.save_tiff_button_click)

    def open_file_dialog(self):
        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle("Open File")
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setViewMode(QFileDialog.ViewMode.Detail)
        file_dialog.setNameFilter("Image files (*.png *.tif *.tiff *.jpg)")

        self.ui.statusbar.showMessage("Загрузка изображения...")

        if file_dialog.exec():            
            selected_image = file_dialog.selectedFiles()[0]
            self.is_tiff = selected_image.endswith(".tiff") or selected_image.endswith(".tif")
            if self.is_tiff:
                self.load_tiff(selected_image)
            else:
                self.load_image(selected_image)                        
        
        self.ui.findIcebergsButton.setEnabled(True)
        self.ui.contrastMenuButton.setEnabled(True)
        self.update_save_buttons(False)
        self.ui.statusbar.clearMessage()

    def load_image(self, img_path):
        PIL_image = Image.open(img_path)
        self.image = np.asarray(PIL_image)
        self.pixmap = QPixmap(img_path)
        self.ui.label.setPixmap(self.pixmap)

    def load_tiff(self, img_path):
        tif_img = self.open_tif_as_png(img_path)
        self.tif_image = tif_img
        corrected_img = self.contrast_correction(tif_img, 0, self.contrast_value)
        self.contrast_modal.ui.contrastSlider.setValue(self.contrast_value)
        self.set_img_fromarray(corrected_img)

    def set_img_fromarray(self, img_array):
        self.image = img_array
        PIL_image = Image.fromarray(img_array)
        self.pixmap = QPixmap.fromImage(ImageQt(PIL_image))
        self.ui.label.setPixmap(self.pixmap)

    def update_contrast(self, value):
        self.contrast_value = value
        corrected_img = self.contrast_correction(self.tif_image, 0, value)
        self.set_img_fromarray(corrected_img)

    def open_modal(self):
        self.prediction_modal.show()
        self.prediction_modal.ui.buttonBox.button(QDialogButtonBox.Ok).setEnabled(True)
        self.prediction_modal.ui.progressBar.setVisible(False)

    def open_contrast_modal(self):
        self.contrast_modal.ui.contrastSlider.setValue(self.contrast_value)
        self.contrast_modal.show()        

    def update_save_buttons(self, value):
        if value:
            value = self.is_tiff        
        self.ui.saveShpButton.setEnabled(value)
        self.ui.saveTiffButton.setEnabled(value)        
        
    def open_tif_as_png(self, img_path):
        dataset = gdal.Open(img_path)

        self.geo_transform = dataset.GetGeoTransform()
        self.projection = dataset.GetProjection()

        band = dataset.GetRasterBand(1)    
        data = band.ReadAsArray()
        data_masked = np.ma.masked_array(data, np.isnan(data)) 

        return data_masked
        
    def contrast_correction(self, image, min, max):
        contrasted = rescale_intensity(image, in_range=(min, max), out_range=(0, 1))

        data_min = np.min(contrasted)
        data_max = np.max(contrasted)
        normalized_data = 255 * (contrasted - data_min) / (data_max - data_min)
        normalized_data = normalized_data.astype(np.uint8) 

        return normalized_data
    
    def save_shp_button_click(self):
        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle("Открыть папку")
        file_dialog.setFileMode(QFileDialog.FileMode.Directory)
        file_dialog.setViewMode(QFileDialog.ViewMode.Detail)

        if file_dialog.exec():
            path = file_dialog.selectedFiles()[0]
            self.save_to_shapefile(path)

    def save_tiff_button_click(self):
        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle("Открыть папку")
        file_dialog.setFileMode(QFileDialog.FileMode.Directory)
        file_dialog.setViewMode(QFileDialog.ViewMode.Detail)

        if file_dialog.exec():
            path = file_dialog.selectedFiles()[0]
            self.save_to_tiff(path)
    
    def save_to_tiff(self, out_path):
        width, height = self.image.shape[1], self.image.shape[0]

        ts = time.time()
        timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d_%H%M%S')
        out_path += f"/predicted_{timestamp}.tif"

        driver = gdal.GetDriverByName("GTiff")
        out_dataset = driver.Create(
            out_path,
            width,
            height,
            3,
            gdal.GDT_Byte
        )

        for i, band in enumerate(np.moveaxis(self.image, -1, 0)):
            out_dataset.GetRasterBand(i + 1).WriteArray(band)

        out_dataset.SetGeoTransform(self.geo_transform)
        out_dataset.SetProjection(self.projection)

        out_dataset = None

    def save_to_shapefile(self, out_path):
        width, height = self.predicted_mask.shape[1], self.predicted_mask.shape[0]

        ts = time.time()
        timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d_%H%M%S')
        out_path += f"/predicted_{timestamp}.shp"

        print(out_path)

        driver = gdal.GetDriverByName("MEM")
        dataset = driver.Create(
            '',
            width,
            height,
            3,
            gdal.GDT_Byte
        )

        band = np.moveaxis(self.predicted_mask, -1, 0)[0]
        dataset.GetRasterBand(1).WriteArray(band)

        dataset.SetGeoTransform(self.geo_transform)
        dataset.SetProjection(self.projection)

        srcband = dataset.GetRasterBand(1)
        dst_layername = 'icebergs'
        drv = ogr.GetDriverByName("ESRI Shapefile")
        dst_ds = drv.CreateDataSource(out_path)

        sp_ref = dataset.GetSpatialRef()

        dst_layer = dst_ds.CreateLayer(dst_layername, srs = sp_ref )    

        fld = ogr.FieldDefn("Score", ogr.OFTInteger)
        dst_layer.CreateField(fld)    

        gdal.Polygonize( srcband, None, dst_layer, 0, [], callback=None )
        
        to_remove = []
        for i in range(dst_layer.GetFeatureCount()):
            feature = dst_layer.GetFeature(i)
            if feature.GetField("Score") == 0:
                to_remove.append(feature.GetFID())
        
        for fid in sorted(to_remove, reverse=True):
            dst_layer.DeleteFeature(fid)

        del dataset
        del dst_ds
        

if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())