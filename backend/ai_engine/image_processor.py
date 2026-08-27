import cv2
import numpy as np
import os
from PIL import Image

class ImagePreprocessor:
    """
    Image Preprocessing Module for the Smart Complaint System.
    Handles resizing, noise reduction, normalization, and integrity validation.
    """
    
    def __init__(self, target_size=(224, 224), normalize=True):
        self.target_size = target_size
        self.normalize = normalize

    def validate_integrity(self, file_path):
        """
        Validates if the image is corrupted and checks its basic properties.
        
        Args:
            file_path (str): Path to the image file.
            
        Returns:
            bool: True if valid, False otherwise.
        """
        if not os.path.exists(file_path):
            return False
            
        try:
            with Image.open(file_path) as img:
                img.verify() # Verify it's an image
            
            # Re-open to check if it can be loaded by OpenCV
            img_test = cv2.imread(file_path)
            if img_test is None:
                return False
                
            return True
        except Exception as e:
            print(f"[ImagePreprocessor] Integrity Check Failed: {e}")
            return False

    def preprocess(self, file_path, output_path=None):
        """
        Runs the full preprocessing pipeline on an image.
        
        Pipeline:
        1. Validate Integrity
        2. Resize to target size
        3. Remove Noise (Gaussian Blur/Denoise)
        4. Normalize Pixel Values
        
        Args:
            file_path (str): Input image path.
            output_path (str): Optional path to save the preprocessed image.
            
        Returns:
            numpy.ndarray: Preprocessed image array.
        """
        if not self.validate_integrity(file_path):
            raise ValueError("Corrupted or unsupported image file.")
            
        # 1. Load image
        img = cv2.imread(file_path)
        
        # 2. Resize
        img_resized = cv2.resize(img, self.target_size, interpolation=cv2.INTER_AREA)
        
        # 3. Noise Removal (Denoising)
        # Using fastNlMeansDenoisingColored for colored images
        img_denoised = cv2.fastNlMeansDenoisingColored(img_resized, None, 10, 10, 7, 21)
        
        # 4. Normalize (Scale pixels 0-255 to 0-1)
        if self.normalize:
            img_normalized = img_denoised.astype(np.float32) / 255.0
        else:
            img_normalized = img_denoised
            
        # 5. Save if output_path provided
        if output_path:
            # If normalized, we need to convert back to 0-255 for saving
            save_img = (img_normalized * 255).astype(np.uint8) if self.normalize else img_normalized
            cv2.imwrite(output_path, save_img)
            
        return img_normalized

def preprocess_complaint_image(file_path):
    """
    Helper function to preprocess a complaint image in place or for analysis.
    """
    preprocessor = ImagePreprocessor()
    try:
        # We'll save a preprocessed version with a prefix
        dir_name = os.path.dirname(file_path)
        base_name = os.path.basename(file_path)
        preprocessed_path = os.path.join(dir_name, f"proc_{base_name}")
        
        processed_data = preprocessor.preprocess(file_path, output_path=preprocessed_path)
        return preprocessed_path
    except Exception as e:
        print(f"[ImagePreprocessor] Error: {e}")
        return None
