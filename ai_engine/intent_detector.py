"""
Intent Detection Engine for Smart Complaint Chatbot
Uses NLP and Machine Learning for accurate intent classification

Supported Intents:
- register_complaint: User wants to file a new complaint
- track_complaint: User wants to check complaint status
- cancel_complaint: User wants to cancel a complaint
- emergency: Urgent/emergency situation
- general_inquiry: Questions about the system
"""

import re
import json
from collections import Counter
from datetime import datetime

# NLP libraries
try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False

try:
    import nltk
    from nltk.tokenize import word_tokenize
    from nltk.corpus import stopwords
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    NLTK_AVAILABLE = True
except (ImportError, LookupError):
    NLTK_AVAILABLE = False


class IntentDetectionEngine:
    """
    Advanced Intent Detection using NLP and Pattern Matching
    Hybrid approach: ML-style features + Rule-based confidence scoring
    """
    
    def __init__(self):
        """Initialize the intent detection engine"""
        self.intents = {
            'register_complaint': {
                'keywords': [
                    'file', 'submit', 'register', 'new', 'complaint', 'report', 
                    'issue', 'problem', 'broken', 'damaged', 'not working', 
                    'malfunctioning', 'defective', 'fault', 'fix', 'repair',
                    'maintenance', 'road', 'pothole', 'sanitation', 'garbage', 'sewage',
                    'sewer', 'streetlight', 'electricity', 'water supply', 'pollution', 'safety',
                    'public park', 'highway', 'bridge', 'pavement', 'drainage'
                ],
                'patterns': [
                    r'\b(file|submit|register|log|create|raise)\s+(a\s+)?(complaint|issue|problem|ticket)\b',
                    r'\b(report|complaint)\s+about\b',
                    r'\b(my|our|the)\s+\w+\s+(is|are)\s+(broken|damaged|not working|faulty)\b',
                    r'\b(need|want)\s+to\s+(file|submit|report|register)\b',
                    r'\b(having|facing|experiencing)\s+(an?\s+)?(issue|problem)\b',
                ],
                'weight': 1.0
            },
            'track_complaint': {
                'keywords': [
                    'status', 'check', 'track', 'where', 'progress', 'update',
                    'follow up', 'follow-up', 'inquiry', 'my complaint',
                    'complaint id', 'ticket', 'number', 'resolved', 'pending'
                ],
                'patterns': [
                    r'\b(check|track|status|where|what|how)\s+(is|are|about|of)?\s*(my|the)?\s*(complaint|issue|ticket)\b',
                    r'\bstatus\s+of\b',
                    r'\b(my|the)\s+complaint\s+(is|about|regarding)\b',
                    r'\bcomplaint\s+(number|id|#)\s*\d+\b',
                    r'\b(status|check)\s+(of\s+)?(complaint\s+)?#?\d+\b',
                    r'\b(when|will)\s+(it|this|my complaint)\s+be\s+(resolved|fixed|completed)\b',
                ],
                'weight': 1.0
            },
            'cancel_complaint': {
                'keywords': [
                    'cancel', 'delete', 'remove', 'withdraw', 'retract',
                    'close', 'dismiss', 'discard', 'do not need', 'no longer',
                    'resolved itself', 'fixed itself', 'nevermind', 'never mind'
                ],
                'patterns': [
                    r'\b(cancel|delete|remove|withdraw|close)\s+(my|the)?\s*(complaint|issue|ticket)\b',
                    r'\b(want|need|would like)\s+to\s+(cancel|delete|remove|withdraw)\b',
                    r'\b(no longer|not anymore)\s+(need|required|necessary)\b',
                    r'\b(resolved|fixed)\s+itself\b',
                    r'\bnever\s*mind\b',
                ],
                'weight': 1.0
            },
            'emergency': {
                'keywords': [
                    'emergency', 'urgent', 'asap', 'immediately', 'critical',
                    'serious', 'dangerous', 'danger', 'fire', 'accident',
                    'injury', 'injured', 'hurt', 'bleeding', 'help', 'sos',
                    'life threatening', 'electrical shock', 'gas leak', 
                    'water leak', 'flood', 'security', 'theft', 'robbery'
                ],
                'patterns': [
                    r'\b(emergency|urgent|critical|serious|asap|immediately)\b',
                    r'\b(fire|flood|leak|accident|injury)\b',
                    r'\b(help|sos|911|999|112)\b',
                    r'\b(life\s+threatening|very\s+urgent)\b',
                    r'\b(danger|dangerous|hazard|unsafe)\b',
                ],
                'weight': 2.0  # Higher weight for emergency
            },
            'general_inquiry': {
                'keywords': [
                    'how', 'what', 'when', 'where', 'why', 'who', 'which',
                    'help', 'assist', 'support', 'information', 'info',
                    'explain', 'tell me', 'question', 'query', 'ask',
                    'guide', 'tutorial', 'process', 'procedure', 'works'
                ],
                'patterns': [
                    r'\b(how|what|when|where|why|who|which)\s+(do|does|is|are|can|could|would|should)\b',
                    r'\b(help|assist|support)\s+me\b',
                    r'\b(tell|show|explain)\s+me\b',
                    r'\b(can|could|would)\s+you\s+(help|assist|tell|explain)\b',
                    r'\b(what|how)\s+(is|are|do|does)\b',
                ],
                'weight': 0.8  # Lower weight as it's often combined with other intents
            },
            'greeting': {
                'keywords': [
                    'hi', 'hello', 'hey', 'greetings', 'morning', 'afternoon', 'evening',
                    'yo', 'sup', 'howdy', 'hola', 'namaste'
                ],
                'patterns': [
                    r'\b(hi|hello|hey|greetings)\b',
                    r'\bgood\s+(morning|afternoon|evening)\b',
                    r'\bhow\s+are\s+you\b',
                ],
                'weight': 1.2
            },
            'thanks': {
                'keywords': [
                    'thanks', 'thank', 'appreciate', 'grateful', 'good', 'great',
                    'cool', 'awesome', 'perfect', 'ok', 'okay'
                ],
                'patterns': [
                    r'\b(thank|thanks)\s*(you|u)?\b',
                    r'\b(appreciate)\s+(it|that)\b',
                    r'\b(sounds|looks)\s+(good|great|perfect)\b',
                ],
                'weight': 1.1
            },
            'goodbye': {
                'keywords': [
                    'bye', 'goodbye', 'see you', 'later', 'exit', 'quit', 'stop',
                    'end', 'done', 'finish'
                ],
                'patterns': [
                    r'\b(bye|goodbye)\b',
                    r'\bsee\s+you\s*(later)?\b',
                    r'\bhave\s+a\s+good\s+(day|night)\b',
                ],
                'weight': 1.1
            }
        }
        
        # Training data for ML-style feature extraction
        self.training_examples = {
            'register_complaint': [
                "I want to file a complaint about the broken AC in my room",
                "The wifi is not working in hostel",
                "Report issue with classroom projector",
                "My room fan is making loud noise",
                "Submit complaint about dirty canteen",
                "The toilet in block A is clogged",
                "Broken window in lab 101",
                "Need to report damaged furniture"
            ],
            'track_complaint': [
                "What is the status of my complaint",
                "Check my complaint number 123",
                "Where is my issue",
                "Has my complaint been resolved",
                "Track complaint about AC",
                "Status of ticket #45",
                "When will my complaint be fixed",
                "Follow up on my wifi complaint"
            ],
            'cancel_complaint': [
                "Cancel my complaint",
                "I want to withdraw my complaint",
                "Delete complaint number 10",
                "The issue is resolved, cancel it",
                "No longer need this complaint",
                "Remove my complaint",
                "Discard my ticket",
                "Never mind, cancel the complaint"
            ],
            'emergency': [
                "Emergency! Fire in hostel block B",
                "Urgent: Water leak in library",
                "Help! Someone is injured",
                "Critical: Gas leak in canteen",
                "ASAP: Electrical shock hazard",
                "Immediate help needed",
                "Dangerous situation in lab",
                "SOS: Accident in parking"
            ],
            'general_inquiry': [
                "How do I file a complaint",
                "What is the process for registration",
                "Can you help me",
                "Tell me about complaint categories",
                "How does the system work",
                "What can you do",
                "Explain the process",
                "Who handles my complaint"
            ],
            'greeting': [
                "Hi there",
                "Hello robot",
                "Good morning",
                "Hey, how are you",
                "Greetings"
            ],
            'thanks': [
                "Thanks a lot",
                "Thank you so much",
                "I appreciate it",
                "That sounds great",
                "Okay, thanks"
            ],
            'goodbye': [
                "Bye for now",
                "Goodbye",
                "See you later",
                "Have a good day",
                "Exit chat"
            ]
        }
        
    def preprocess_text(self, text):
        """
        Preprocess text for better intent detection
        - Lowercase
        - Remove extra spaces
        - Basic normalization
        """
        if not text:
            return ""
        
        # Lowercase
        text = text.lower().strip()
        
        # Remove extra spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Normalize common variations
        replacements = {
            "can't": "cannot",
            "won't": "will not",
            "don't": "do not",
            "doesn't": "does not",
            "didn't": "did not",
            "hasn't": "has not",
            "haven't": "have not",
            "isn't": "is not",
            "aren't": "are not",
            "wasn't": "was not",
            "weren't": "were not",
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        return text
    
    def extract_features(self, text):
        """
        Extract NLP features from text
        Returns a feature dictionary
        """
        features = {}
        
        # Preprocess
        text = self.preprocess_text(text)
        
        # Basic features
        features['length'] = len(text)
        features['word_count'] = len(text.split())
        features['has_question'] = '?' in text
        features['has_exclamation'] = '!' in text
        features['is_uppercase'] = text.isupper()
        
        # Question word detection
        question_words = ['how', 'what', 'when', 'where', 'why', 'who', 'which']
        features['question_word'] = any(text.startswith(qw) for qw in question_words)
        
        # Sentiment (if TextBlob available)
        if TEXTBLOB_AVAILABLE:
            try:
                blob = TextBlob(text)
                features['sentiment_polarity'] = blob.sentiment.polarity
                features['sentiment_subjectivity'] = blob.sentiment.subjectivity
            except:
                features['sentiment_polarity'] = 0.0
                features['sentiment_subjectivity'] = 0.5
        else:
            features['sentiment_polarity'] = 0.0
            features['sentiment_subjectivity'] = 0.5
        
        # Tokenization (if NLTK available)
        if NLTK_AVAILABLE:
            try:
                tokens = word_tokenize(text)
                features['token_count'] = len(tokens)
                
                # Stopwords
                stop_words = set(stopwords.words('english'))
                features['stopword_ratio'] = sum(1 for t in tokens if t.lower() in stop_words) / max(len(tokens), 1)
            except:
                features['token_count'] = len(text.split())
                features['stopword_ratio'] = 0.3
        else:
            features['token_count'] = len(text.split())
            features['stopword_ratio'] = 0.3
        
        return features
    
    def calculate_intent_score(self, text, intent_name):
        """
        Calculate confidence score for a specific intent
        Uses keyword matching, pattern matching, and feature analysis
        """
        intent_config = self.intents[intent_name]
        text_lower = text.lower()
        
        # Keyword matching score (0-1)
        # Handle single words with boundary check, multi-words with substring check
        keyword_matches = 0
        text_words = set(re.findall(r'\w+', text_lower))
        
        for kw in intent_config['keywords']:
            if ' ' in kw:
                # Multi-word phrase: use substring check
                if kw in text_lower:
                    keyword_matches += 1
            else:
                # Single word: use exact word match
                if kw in text_words:
                    keyword_matches += 1
                    
        keyword_score = min(keyword_matches / 3.0, 1.0)  # Normalize to 0-1
        
        # Pattern matching score (0-1)
        pattern_matches = sum(1 for pattern in intent_config['patterns'] if re.search(pattern, text_lower, re.IGNORECASE))
        pattern_score = min(pattern_matches / 2.0, 1.0)  # Normalize to 0-1
        
        # Combined score with weights
        base_score = (keyword_score * 0.4 + pattern_score * 0.6)
        
        # Apply intent weight but keep it normalized to 0-1
        # For emergency, boost the score but cap at 1.0
        if intent_name == 'emergency' and base_score > 0:
            # Emergency gets a boost but still normalized
            weighted_score = min(base_score * 1.5, 1.0)
        else:
            weighted_score = base_score * intent_config['weight']
        
        return weighted_score
    
    def detect_intent(self, message, return_all_scores=False):
        """
        Detect intent from user message with confidence score
        
        Args:
            message (str): User's message
            return_all_scores (bool): If True, return all intent scores
            
        Returns:
            dict: {
                'intent': str,
                'confidence': float (0-1),
                'all_scores': dict (optional)
            }
        """
        if not message or not message.strip():
            return {
                'intent': 'unknown',
                'confidence': 0.0,
                'all_scores': {}
            }
        
        # Preprocess
        processed_text = self.preprocess_text(message)
        
        # Extract features
        features = self.extract_features(processed_text)
        
        # Calculate scores for all intents
        scores = {}
        for intent_name in self.intents.keys():
            scores[intent_name] = self.calculate_intent_score(processed_text, intent_name)
        
        # Special case: If emergency keywords found, prioritize emergency
        emergency_score = scores.get('emergency', 0)
        if emergency_score > 0.5:
            # Check if it's truly an emergency (not just "help me understand")
            non_emergency_words = ['how', 'what', 'understand', 'process', 'tell me', 'explain']
            has_non_emergency = any(word in processed_text for word in non_emergency_words)
            
            if has_non_emergency and scores.get('general_inquiry', 0) > 0.3:
                # It's actually a general inquiry, reduce emergency score
                scores['emergency'] = max(emergency_score * 0.3, 0)
        
        # Get top intent
        if scores:
            top_intent = max(scores.items(), key=lambda x: x[1])
            intent_name, confidence = top_intent
            
            # Threshold: minimum confidence required
            min_confidence = 0.25
            
            if confidence < min_confidence:
                intent_name = 'unknown'
                confidence = 0.0
        else:
            intent_name = 'unknown'
            confidence = 0.0
        
        result = {
            'intent': intent_name,
            'confidence': round(min(confidence, 1.0), 3),  # Cap at 1.0
            'features': features
        }
        
        if return_all_scores:
            result['all_scores'] = {k: round(min(v, 1.0), 3) for k, v in scores.items()}
        
        return result
    
    def classify_batch(self, messages):
        """
        Classify multiple messages at once
        Useful for testing and evaluation
        """
        results = []
        for message in messages:
            result = self.detect_intent(message, return_all_scores=True)
            results.append({
                'message': message,
                **result
            })
        return results
    
    def get_intent_description(self, intent):
        """Get human-readable description of intent"""
        descriptions = {
            'register_complaint': 'User wants to file a new complaint',
            'track_complaint': 'User wants to check complaint status',
            'cancel_complaint': 'User wants to cancel a complaint',
            'emergency': 'Emergency or urgent situation',
            'general_inquiry': 'General question or help request',
            'unknown': 'Intent could not be determined'
        }
        return descriptions.get(intent, 'Unknown intent')
    
    def evaluate_accuracy(self):
        """
        Evaluate the model on training examples
        Returns accuracy metrics
        """
        correct = 0
        total = 0
        
        results = []
        
        for expected_intent, examples in self.training_examples.items():
            for example in examples:
                result = self.detect_intent(example)
                predicted_intent = result['intent']
                is_correct = predicted_intent == expected_intent
                
                if is_correct:
                    correct += 1
                total += 1
                
                results.append({
                    'example': example,
                    'expected': expected_intent,
                    'predicted': predicted_intent,
                    'confidence': result['confidence'],
                    'correct': is_correct
                })
        
        accuracy = (correct / total) * 100 if total > 0 else 0
        
        return {
            'accuracy': round(accuracy, 2),
            'correct': correct,
            'total': total,
            'details': results
        }


# Singleton instance
_intent_engine = None

def get_intent_engine():
    """Get or create singleton instance of Intent Detection Engine"""
    global _intent_engine
    if _intent_engine is None:
        _intent_engine = IntentDetectionEngine()
    return _intent_engine


# Convenience functions
def detect_intent(message):
    """Convenience function to detect intent"""
    engine = get_intent_engine()
    return engine.detect_intent(message)


def classify_intent(message, return_all_scores=False):
    """Convenience function to classify intent with all scores"""
    engine = get_intent_engine()
    return engine.detect_intent(message, return_all_scores=return_all_scores)


if __name__ == "__main__":
    # Test the intent detection
    engine = IntentDetectionEngine()
    
    print("=" * 60)
    print("Intent Detection Engine - Test Suite")
    print("=" * 60)
    
    # Test messages
    test_messages = [
        "I want to file a complaint about broken AC",
        "What is the status of my complaint",
        "Cancel my complaint please",
        "EMERGENCY! Fire in hostel",
        "How do I submit a complaint",
        "My room wifi is not working",
        "Check complaint #123",
        "I don't need this complaint anymore",
        "Urgent: Water leak in library",
        "Can you help me understand the process"
    ]
    
    print("\n🧪 Testing Intent Detection:\n")
    
    for msg in test_messages:
        result = engine.detect_intent(msg, return_all_scores=True)
        print(f"Message: \"{msg}\"")
        print(f"  ➜ Intent: {result['intent']}")
        print(f"  ➜ Confidence: {result['confidence']:.1%}")
        print(f"  ➜ Description: {engine.get_intent_description(result['intent'])}")
        print()
    
    # Evaluate on training data
    print("\n📊 Model Evaluation:")
    print("-" * 60)
    evaluation = engine.evaluate_accuracy()
    print(f"Accuracy: {evaluation['accuracy']:.1f}%")
    print(f"Correct: {evaluation['correct']}/{evaluation['total']}")
    print()
