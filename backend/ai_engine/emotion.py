import re
from textblob import TextBlob

# Emotion Analysis Engine
# Detects specific emotions and calculates intensity scores.

EMOTION_KEYWORDS = {
    "Anger": ["furious", "angry", "terrible", "bad", "useless", "worst", "hate", "mad", "annoyed", "frustrated", "sick", "tired", "stupid", "idiot", "nonsense", "rubbish", "pathetic", "awful"],
    "Fear": ["scary", "unsafe", "danger", "afraid", "worried", "threat", "fire", "short circuit", "spark", "loose", "broke", "accident", "gas leak", "smoke", "explosion", "collapse", "blood", "attack", "shaking"],
    "Urgency": ["immediately", "urgent", "asap", "now", "quick", "critical", "emergency", "hurry", "fast", "priority", "deadline", "overdue", "delay", "waiting"],
    "Distress": ["helpless", "please help", "struggling", "suffering", "difficult", "pain", "sorry", "cry", "unable", "cannot", "scared", "help me", "dying", "hurt", "trapped"]
}

def detect_emotions(text):
    """
    Detects intensity of specific emotions based on keywords and sentiment.
    """
    text_lower = text.lower()
    results = {}
    
    CRITICAL_KEYWORDS = {
        "fire", "smoke", "spark", "explosion", "blood", "injury", "attack", "collapsed", "flood", "gas leak"
    }

    for emotion, keywords in EMOTION_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            if re.search(r'\b' + re.escape(keyword) + r'\b', text_lower):
                score += 0.35 # Increased base weight
                if keyword in CRITICAL_KEYWORDS:
                    score = 1.0 # Immediate max score for critical terms
        results[emotion] = min(round(score, 2), 1.0) # Cap at 1.0
        
    return results

def analyze_sentiment(text):
    """
    Analyzes the sentiment and specific emotions of the complaint text.
    """
    try:
        blob = TextBlob(text)
        polarity = round(blob.sentiment.polarity, 2)
        subjectivity = round(blob.sentiment.subjectivity, 2)
        
        # Normalize polarity (-1 to 1) to score (0 to 1)
        score = (polarity + 1) / 2
        
        # Specific Emotions
        emotions = detect_emotions(text)
        
        # --- STEP 6: AI-Based Escalation Logic ---
        escalation_reasons = []
        is_escalated = False

        # Rule 4: Explicit Distress Escalation
        if emotions['Distress'] > 0.5:
             is_escalated = True
             escalation_reasons.append(f"Significant emotional distress detected ({emotions['Distress']})")

        # Rule 5: Emotion score > 0.75
        for emo, intensity in emotions.items():
            if intensity > 0.75:
                is_escalated = True
                escalation_reasons.append(f"High {emo} intensity ({intensity})")

        # Rule 2: Negative sentiment + high urgency
        if polarity < -0.4 and emotions['Urgency'] > 0.6:
            is_escalated = True
            escalation_reasons.append("Negative sentiment combined with high urgency")

        # Rule 3: Extreme Negative Sentiment
        if polarity < -0.8:
            is_escalated = True
            escalation_reasons.append("Extreme negative sentiment score")

        # Fallback for general threshold
        if not is_escalated and (emotions['Anger'] > 0.6 or emotions['Fear'] > 0.6):
             is_escalated = True
             escalation_reasons.append("Elevated Anger or Fear levels detected")
        
        if polarity > 0.3:
            sentiment = "Positive"
        elif polarity < -0.3:
            sentiment = "Negative"
        else:
            sentiment = "Neutral"
            
        return {
            'polarity': polarity,
            'subjectivity': subjectivity,
            'score': round(score, 2),
            'sentiment': sentiment,
            'emotions': emotions,
            'is_escalated': is_escalated,
            'escalation_reasons': escalation_reasons
        }
    except Exception as e:
        print(f"Sentiment Analysis Error: {e}")
        return {
            'polarity': 0.0, 
            'subjectivity': 0.0, 
            'score': 0.5, 
            'sentiment': 'Neutral',
            'emotions': {"Anger": 0, "Fear": 0, "Urgency": 0, "Distress": 0},
            'is_escalated': False
        }
