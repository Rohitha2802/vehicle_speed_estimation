import cv2
import easyocr
import base64
import numpy as np

class NumberPlateRecognizer:
    def __init__(self):
        """
        Initialize the EasyOCR reader. 
        Downloads model files into ~/.EasyOCR on first run.
        """
        import os
        model_dir = os.path.join(os.path.dirname(__file__), 'models')
        os.makedirs(model_dir, exist_ok=True)
        self.reader = easyocr.Reader(['en'], gpu=True, model_storage_directory=model_dir, user_network_directory=model_dir) # Will seamlessly fallback to CPU if no GPU
        
    def extract_plate(self, frame, vehicle_bbox):
        """
        Extracts license plate text from the given vehicle bounding box in a frame.
        
        Args:
            frame: Origin numpy image
            vehicle_bbox: [x1, y1, x2, y2] of the vehicle
            
        Returns:
            (plate_text, _crop_b64) or (None, None)
        """
        try:
            x1, y1, x2, y2 = vehicle_bbox
            h, w = frame.shape[:2]
            
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(w, x2)
            y2 = min(h, y2)
            
            # Crop to the vehicle
            vehicle_crop = frame[y1:y2, x1:x2]
            if vehicle_crop.size == 0:
                return None, None
                
            # Attempt OCR on the vehicle itself directly
            # Often it's faster to run OCR directly rather than running a secondary YOLO model 
            # for plate detection, since EasyOCR intrinsically hunts for text blocks.
            results = self.reader.readtext(vehicle_crop, detail=1, paragraph=False)
            
            # We want the highest confidence result that looks somewhat like a plate string
            best_plate = None
            best_conf = 0.0
            best_bbox = None
            
            for (bbox, text, conf) in results:
                # Clean up extracted text
                clean_text = ''.join(e for e in text if e.isalnum()).upper()
                
                # Assume strings > 4 chars and < 15 chars are plates
                if 4 < len(clean_text) < 15:
                    if conf > best_conf:
                        best_conf = conf
                        best_plate = clean_text
                        best_bbox = bbox
                        
            if best_plate and best_bbox:
                # Crop the plate string out for the UI image
                try: # Easyocr bounds are [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
                    px1 = max(0, int(best_bbox[0][0]))
                    py1 = max(0, int(best_bbox[0][1]))
                    px2 = min(vehicle_crop.shape[1], int(best_bbox[2][0]))
                    py2 = min(vehicle_crop.shape[0], int(best_bbox[2][1]))
                    
                    plate_crop = vehicle_crop[py1:py2, px1:px2]
                    _, buffer = cv2.imencode('.jpg', plate_crop)
                    plate_b64 = base64.b64encode(buffer).decode('utf-8')
                    return best_plate, plate_b64
                except Exception:
                    # Ignore failure to crop, just return the text
                    return best_plate, None
            
            return None, None
            
        except Exception as e:
            print(f"[ANPR Error] {e}")
            return None, None
