import PIL.Image
import PIL.ExifTags
from math import floor

class LocationEngine:
    """
    Handles extraction of GPS metadata (EXIF) from images and fallback logic.
    """
    
    @staticmethod
    def get_gps_metadata(image_path):
        """
        Extracts latitude and longitude from image's EXIF data.
        Returns (lat, lon) as floats or (None, None) if not found.
        """
        try:
            img = PIL.Image.open(image_path)
            exif_data = img._getexif()
            
            if not exif_data:
                return None, None
            
            gps_info = {}
            for tag, value in exif_data.items():
                decoded = PIL.ExifTags.TAGS.get(tag, tag)
                if decoded == "GPSInfo":
                    for t in value:
                        sub_decoded = PIL.ExifTags.GPSTAGS.get(t, t)
                        gps_info[sub_decoded] = value[t]
            
            if not gps_info:
                return None, None
            
            def convert_to_degrees(value):
                """Helper function to convert the GPS coordinates stored in the EXIF to float degrees"""
                d = float(value[0])
                m = float(value[1])
                s = float(value[2])
                return d + (m / 60.0) + (s / 3600.0)

            lat = None
            lon = None

            gps_latitude = gps_info.get("GPSLatitude")
            gps_latitude_ref = gps_info.get("GPSLatitudeRef")
            gps_longitude = gps_info.get("GPSLongitude")
            gps_longitude_ref = gps_info.get("GPSLongitudeRef")

            if gps_latitude and gps_latitude_ref and gps_longitude and gps_longitude_ref:
                lat = convert_to_degrees(gps_latitude)
                if gps_latitude_ref != "N":
                    lat = 0 - lat

                lon = convert_to_degrees(gps_longitude)
                if gps_longitude_ref != "E":
                    lon = 0 - lon
                    
            return lat, lon

        except Exception as e:
            print(f"[LocationEngine] Error extracting EXIF: {e}")
            return None, None

    @staticmethod
    def validate_gps(lat, lon):
        """
        Validates if GPS coordinates are within realistic bounds.
        """
        if lat is None or lon is None:
            return False
        
        # Basic world bounds
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return False
            
        # Optional: Add specific bounds for the project (e.g., city/country)
        # For now, just general world bounds
        return True
