import torchvision
import torch
from PIL import Image
import numpy as np
import cv2
from ultralytics import YOLO
from inference import get_model
import gc 

class ModelManager():
    model = None

    def __init__(self):
        self.load_model()

    def load_model(self):
        pass
    
    def predict(self, image):
        pass

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
        
    def clear(self):
        del self.model
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    

class RCNNModelManager(ModelManager):
    def load_model(self):
        rcnn_model = torchvision.models.detection.fasterrcnn_resnet50_fpn_v2(num_classes=2)

        device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')

        rcnn_model.load_state_dict(torch.load('./models/resnet/weights.pth', weights_only=True, map_location=device))
        rcnn_model.eval()

        self.model = rcnn_model

    def predict(self, image):
        image = Image.fromarray(image)    
        transforms = torchvision.transforms.Compose([
            torchvision.transforms.ToTensor()
        ])
        img = transforms(image)
        img = torch.unsqueeze(img, dim=0)

        results = self.model(img)[0]

        image = np.asarray(image)
        if len(image.shape) != 3:
            image = np.stack((image,)*3, axis=-1)
        detected_img = image.copy()
        boxes_mask = np.zeros((image.shape[0],image.shape[1],1), np.uint8)
        boxes = results['boxes']
        confidence = results['scores']

        for i, box in enumerate(boxes):

            score = confidence[i]        
            if score < 0.70:
                continue

            x1 = int(box[0].item())
            y1 = int(box[3].item())
            x2 = int(box[2].item())
            y2 = int(box[1].item())

            color = self.map_color_to_prob(score * 100)
            cv2.rectangle(detected_img, (x1, y1), (x2,y2), color, 2)
            cv2.rectangle(boxes_mask, (x1, y1), (x2, y2), int(score*100), -1)

        return detected_img, boxes_mask
    

class YOLOModelManager(ModelManager):
    def load_model(self):
        model_yolo11 = YOLO("./models/yolo/weights.pt")
        self.model = model_yolo11

    def predict(self, image):
        # image = Image.fromarray(img_array)
        # image = np.asarray(image) 
        if len(image.shape) != 3:
            image = np.stack((image,)*3, axis=-1)

        results = self.model.predict(image)

        box_image = image.copy()
        boxes_mask = np.zeros((image.shape[0],image.shape[1],1), np.uint8)

        for box in results[0].boxes.data:
            x1, y1, x2, y2, score, label = box
            x1 = int(x1)
            y1 = int(y1)
            x2 = int(x2)
            y2 = int(y2)
            color = self.map_color_to_prob(score * 100)
            cv2.rectangle(box_image, (x1, y1), (x2,y2), color, 2)
            cv2.rectangle(boxes_mask, (x1, y1), (x2, y2), int(score*100), -1)
        

        return box_image, boxes_mask
    

class RoboFlowModelManager(ModelManager):
    def load_model(self):
        model_roboflow = get_model(model_id="diploma-soocr/3", api_key='UvgFv3pldbWoJV15XcOH')
        self.model = model_roboflow

    def predict(self, image):
        img = Image.fromarray(image)
        img = np.asarray(img)
        if len(img.shape) != 3:
            img = np.stack((img,)*3, axis=-1)

        results = self.model.infer(img)[0]

        box_image = img.copy()
        boxes_mask = np.zeros((img.shape[0],img.shape[1],1), np.uint8)

        for box in results.predictions:

            x1 = box.x - box.width/2
            y1 = box.y - box.height/2
            x2 = box.x + box.width/2
            y2 = box.y + box.height/2
            x1 = int(x1)
            y1 = int(y1)
            x2 = int(x2)
            y2 = int(y2)

            score = box.confidence
            label = box.class_name

            color = self.map_color_to_prob(score * 100)
            cv2.rectangle(box_image, (x1, y1), (x2,y2), color, 2)
            cv2.rectangle(boxes_mask, (x1, y1), (x2, y2), int(score*100), -1)

        return box_image, boxes_mask
