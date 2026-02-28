import torch
from ultralytics import YOLO


class YOLOEngine:
    def __init__(self, model_path="yolov8s.pt"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"YOLO running on: {self.device}")

        self.model = YOLO(model_path)
        self.model.to(self.device)

        # COCO vehicle class IDs
        self.vehicle_classes = {2, 3, 5, 7}  # car, motorcycle, bus, truck

    # -------------------------------------------------------
    # Detect and return vehicle count
    # -------------------------------------------------------
    def count_vehicles(self, frame):

        results = self.model(frame)[0]

        vehicle_count = 0

        for cls in results.boxes.cls:
            class_name = self.model.names[int(cls)]

            if class_name in ["car", "truck", "bus", "motorcycle"]:
                vehicle_count += 1

        return vehicle_count