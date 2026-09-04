import os
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
try:
    import cv2
except Exception:
    cv2 = None

try:
    import numpy as np
except Exception:
    np = None

class AuthenticityEngine:
    """
    Image Authenticity & Anti-Fraud Module.
    Detects if an image is likely a stock photo, a duplicate, or lacks original metadata.
    """

    @staticmethod
    def get_exif_data(image_path):
        """Extracts EXIF data from the image."""
        try:
            with Image.open(image_path) as img:
                exif_data = img._getexif()
                if not exif_data:
                    return None
                
                decoded = {}
                for tag, value in exif_data.items():
                    decoded_tag = TAGS.get(tag, tag)
                    decoded[decoded_tag] = value
                return decoded
        except Exception:
            return None

    @staticmethod
    def check_metadata(image_path):
        """
        Checks for original camera metadata.
        Returns (is_suspicious, reasons)
        """
        exif = AuthenticityEngine.get_exif_data(image_path)
        reasons = []
        is_suspicious = False

        if not exif:
            is_suspicious = True
            reasons.append("Missing Camera Metadata (EXIF). Likely a web-downloaded or screenshot image.")
        else:
            # Check for camera model
            if 'Model' not in exif and 'Make' not in exif:
                is_suspicious = True
                reasons.append("Missing Camera Make/Model info.")
            
            # Check for GPS (Many students might have it off, but its presence is a strong authenticity signal)
            has_gps = False
            for tag in exif:
                if tag == "GPSInfo":
                    has_gps = True
                    break
            
            if not has_gps:
                reasons.append("No GPS coordinates found in metadata.")

        return is_suspicious, reasons

    @staticmethod
    def calculate_dhash(image_path, hash_size=8):
        """
        Calculates a difference hash (dHash) for the image.
        Used to detect duplicate submissions.
        """
        try:
            img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if img is None: return None
            
            # Resize to (hash_size + 1, hash_size)
            resized = cv2.resize(img, (hash_size + 1, hash_size))
            
            # Compute difference between adjacent pixels
            diff = resized[:, 1:] > resized[:, :-1]
            
            # Convert to bits
            return "".join(diff.flatten().astype(int).astype(str))
        except Exception:
            return None

    @staticmethod
    def detect_stock_patterns(image_path):
        """
        Detect markers typical of professional/stock photography:
        - Perfect focus (extremely high Laplacian variance)
        - Specific aspect ratios
        - No sensor noise
        """
        try:
            img = cv2.imread(image_path)
            if img is None: return False, []
            
            reasons = []
            is_suspicious = False
            
            # 1. Check for extreme clarity (often stock photos)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            variance = cv2.Laplacian(gray, cv2.CV_64F).var()
            if variance > 10000: # Extremely sharp
                reasons.append("Extremely high image clarity (Professional/Stock characteristic).")
            
            # 2. Aspect Ratio (Stock photos often use specific ratios)
            h, w = img.shape[:2]
            ratio = w / h
            # Standard phone photos are usually 4:3 or 16:9
            if abs(ratio - 1.5) < 0.01: # 3:2 is classic DSLR/Stock
                reasons.append("Professional aspect ratio (3:2) detected.")
                
            if len(reasons) >= 2:
                is_suspicious = True
                
            return is_suspicious, reasons
        except Exception:
            return False, []

    @classmethod
    def verify_authenticity(cls, image_path):
        """
        Runs the full verification suite.
        """
        meta_suspicious, meta_reasons = cls.check_metadata(image_path)
        pattern_suspicious, pattern_reasons = cls.detect_stock_patterns(image_path)
        
        # Calculate fingerprint for duplicate detection
        fingerprint = cls.calculate_dhash(image_path)
        
        is_suspicious = meta_suspicious or pattern_suspicious
        all_reasons = list(set(meta_reasons + pattern_reasons))
        
        return {
            "is_suspicious": is_suspicious,
            "reasons": all_reasons,
            "fingerprint": fingerprint,
            "trust_score": max(0, 100 - (len(all_reasons) * 15))
        }

def analyze_image_authenticity(image_path):
    """Wrapper for the AuthenticityEngine."""
    return AuthenticityEngine.verify_authenticity(image_path)
