import numpy as np

class IceDetector():
    def __init__(self, modelManager):
        self.ModelManager = modelManager

    def split_image(self, image, width, height):
        tiles = []
        shape_y = len(range(0,image.shape[0],width))
        shape_x = len(range(0,image.shape[1],height))
        tiles = [image[x:x+width,y:y+height] for x in range(0,image.shape[0],width) for y in range(0,image.shape[1],height)]
        return tiles, (shape_x, shape_y)
    
    def restore_image(self, img_tiles, shape):
        x_len, y_len = shape
        combined_tiles = []
        x_start = 0
        x_end = x_len
        print(shape)
        for y in range(y_len):
            combined_tiles.append(np.concatenate(img_tiles[x_start:x_end], axis=1))
            x_start += x_len
            x_end += x_len
        restored_img = np.concatenate(combined_tiles)
        return restored_img
    
    def predict_image_large(self, image, progress_bar=None):        
        images_splitted, shape = self.split_image(image, 640, 640)
        predicted_imgs = []
        boxes_imgs = []

        if progress_bar:
            progress_bar.setMaximum(len(images_splitted))

        for i, image in enumerate(images_splitted):
            detected_img, boxes = self.ModelManager.predict(image)
            predicted_imgs.append(detected_img)
            boxes_imgs.append(boxes)

            print("box", i, "of", len(images_splitted))
            if progress_bar:
                progress_bar.setValue(i+1)

        restored_img = self.restore_image(predicted_imgs, shape)
        boxes_image = self.restore_image(boxes_imgs, shape)
        return restored_img, boxes_image
    
    def predict_image_large_callback(self, image, isCancelled, progress_callback=None):
        images_splitted, shape = self.split_image(image, 640, 640)
        predicted_imgs = []
        boxes_imgs = []

        if progress_callback:
            progress_callback(0, len(images_splitted))            

        for i, image in enumerate(images_splitted):
            if isCancelled[0]:
                predicted_imgs = []
                boxes_imgs = []                
                self.ModelManager.clear()
                return ([], [])
            detected_img, boxes = self.ModelManager.predict(image)
            predicted_imgs.append(detected_img)
            boxes_imgs.append(boxes)

            print("box", i, "of", len(images_splitted))
            if progress_callback:
                progress_callback(i+1, len(images_splitted))

        restored_img = self.restore_image(predicted_imgs, shape)
        boxes_image = self.restore_image(boxes_imgs, shape)
        return restored_img, boxes_image
