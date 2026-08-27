from textblob import TextBlob
import re

# Text Preprocessing Module
# Handles noise reduction, stop word removal, and spelling correction.

def preprocess_text(text):
    """
    Cleans and normalizes complaint text.
    Steps:
    1. Lowercase
    2. Remove filler words (uh, um, like)
    3. Remove special characters
    4. Auto-correct spelling (TextBlob)
    
    Args:
        text (str): Raw input text.
        
    Returns:
        clean_text (str): Preprocessed text ready for NLP.
    """
    if not text:
        return ""
        
    # 1. Lowercase & Basic Cleaning
    text = text.lower().strip()
    
    # 2. Remove filler words (common in voice input)
    fillers = ["um", "uh", "like", "actually", "literally", "basically", "you know", "i mean"]
    for word in fillers:
        text = text.replace(f" {word} ", " ").replace(f"{word} ", "")
        
    # 3. Remove specialized characters (keep alphanumeric + spaces)
    text = re.sub(r'[^a-z0-9\s]', '', text)
    
    # 4. Spelling Correction (Optional - can be slow on large text)
    # Using TextBlob for simple correction
    try:
        blob = TextBlob(text)
        corrected_text = str(blob.correct())
    except Exception as e:
        print(f"Spelling Correction Warning: {e}")
        corrected_text = text # Fallback to original
        
    return corrected_text

def extract_keywords(text):
    """
    Extracts meaningful keywords (Nouns/Adjectives) from text.
    """
    try:
        blob = TextBlob(text)
        # simplistic keyword extraction based on Nouns
        return list(blob.noun_phrases)
    except:
        return []
