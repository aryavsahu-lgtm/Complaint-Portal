#!/usr/bin/env python3
"""
Script to download CM Vishnu Deo Sai's official image
"""
import requests
import os

# Image URL - using official source
image_url = "https://upload.wikimedia.org/wikipedia/commons/2/29/Vishnudeo_Sai.jpg"

# Save path
save_path = "static/images/cm_vishnu_deo_sai.jpg"

print(f"Downloading CM image from: {image_url}")
print(f"Saving to: {save_path}")

try:
    # Download the image with proper headers
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    response = requests.get(image_url, headers=headers, timeout=10)
    response.raise_for_status()
    
    # Save the image
    with open(save_path, 'wb') as f:
        f.write(response.content)
    
    print(f"✓ Successfully downloaded image ({len(response.content)} bytes)")
    print(f"✓ Saved to: {os.path.abspath(save_path)}")
    
except Exception as e:
    print(f"✗ Error downloading image: {e}")
    print("\nAlternatively, you can:")
    print("1. Manually download the image from the URL above")
    print(f"2. Save it as: {os.path.abspath(save_path)}")
