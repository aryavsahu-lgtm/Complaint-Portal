# Chatbot Technical Specification
**Smart Complaint System - AI Chatbot Module**

---

## 📋 Module Overview

**Module Name**: AI Chatbot Engine  
**Location**: `ai_engine/chatbot.py`, `chatbot/routes.py`  
**Dependencies**: TextBlob, NLTK, Flask, SQLite  
**Status**: Foundation Complete, Enhancement Required

---

## 🏗️ Current Implementation Analysis

### Existing Components

#### 1. **SmartChatbot Class** (`ai_engine/chatbot.py`)
```python
Current Features:
✅ Intent detection (7 intents via regex)
✅ Emotion detection (3 urgency levels)
✅ Complaint info extraction
✅ Message processing pipeline
✅ Database integration
✅ Worker assignment integration

Code Stats:
- Lines: 251
- Methods: 6
- Intents: 7
- State management: Basic
```

#### 2. **Chatbot Routes** (`chatbot/routes.py`)
```python
Current Endpoints:
✅ GET  /chatbot/              - Render chat interface
✅ POST /chatbot/message       - Process user message
✅ POST /chatbot/submit-complaint - Submit complaint
✅ GET  /chatbot/complaint/<id> - Get complaint details
✅ GET  /chatbot/history       - Get chat history

Code Stats:
- Lines: 119
- Routes: 5
- Authentication: login_required decorator
```

### Current Strengths
1. ✅ **Solid foundation** - Well-structured OOP design
2. ✅ **Integration ready** - Connected to existing AI services
3. ✅ **Database schema** - Chat history table exists
4. ✅ **Authentication** - User session management
5. ✅ **Action-based responses** - Structured response format

### Current Limitations
1. ⚠️ **Simple intent detection** - Only regex, no ML
2. ⚠️ **No context persistence** - Session context not saved to DB
3. ⚠️ **Limited conversation states** - State machine not fully implemented
4. ⚠️ **No voice integration** - Text-only currently
5. ⚠️ **Basic emotion detection** - Keyword counting only
6. ⚠️ **No learning mechanism** - Static responses

---

## 🎯 Enhancement Roadmap

### Enhancement 1: Advanced NLP (STEP 3)

**Current:**
```python
def detect_intent(self, message):
    for intent, pattern in self.intents.items():
        if re.search(pattern, message.lower()):
            return intent
    return 'unknown'
```

**Enhanced:**
```python
from transformers import pipeline

class EnhancedNLU:
    def __init__(self):
        # Use pre-trained intent classifier
        self.intent_classifier = pipeline(
            "text-classification",
            model="facebook/bart-large-mnli"
        )
        
    def detect_intent(self, message):
        # Classify against multiple candidate labels
        candidates = [
            "filing a new complaint",
            "checking complaint status",
            "asking for help",
            "greeting",
            "showing frustration"
        ]
        
        result = self.intent_classifier(
            message,
            candidate_labels=candidates
        )
        
        return {
            'intent': result['labels'][0],
            'confidence': result['scores'][0]
        }
```

**Benefits:**
- 📈 95%+ accuracy (vs 70-80% regex)
- 🧠 Handles variations and typos
- 🌐 Better multi-language support

---

### Enhancement 2: Context-Aware Conversations (STEP 4)

**Implementation:**
```python
class ConversationContext:
    def __init__(self, session_id, user_id):
        self.session_id = session_id
        self.user_id = user_id
        self.state = "greeting"
        self.entities = {}
        self.history = []
        
    def update_context(self, user_msg, bot_response, intent):
        """Track conversation flow"""
        self.history.append({
            'user': user_msg,
            'bot': bot_response,
            'intent': intent,
            'timestamp': datetime.now()
        })
        
        # Extract and update entities
        if intent == 'complaint_new':
            self.entities['complaint_draft'] = self.extract_entities(user_msg)
            self.state = 'collecting_info'
        
    def get_context_for_response(self):
        """Provide context for next response"""
        return {
            'current_state': self.state,
            'pending_entities': self.missing_entities(),
            'conversation_length': len(self.history),
            'last_intent': self.history[-1]['intent'] if self.history else None
        }
```

**Database Schema:**
```sql
CREATE TABLE conversation_contexts (
    id INTEGER PRIMARY KEY,
    session_id TEXT UNIQUE NOT NULL,
    user_id INTEGER,
    state TEXT DEFAULT 'greeting',
    entities TEXT,  -- JSON
    history TEXT,   -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

---

### Enhancement 3: Emotion & Sentiment Analysis (STEP 5)

**Current Implementation:**
```python
def detect_emotion(self, message):
    urgent_keywords = ['urgent', 'emergency', ...]
    urgency_score = sum(1 for kw in urgent_keywords if kw in message.lower())
    
    if urgency_score >= 2:
        return 'high_urgency'
    # ...
```

**Enhanced Version:**
```python
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

class EmotionAnalyzer:
    def __init__(self):
        self.vader = SentimentIntensityAnalyzer()
        
    def analyze_emotion(self, message):
        # VADER for social media style text
        vader_scores = self.vader.polarity_scores(message)
        
        # TextBlob for general sentiment
        blob = TextBlob(message)
        
        # Custom urgency keywords
        urgency_keywords = {
            'emergency': 3,
            'urgent': 2,
            'asap': 2,
            'immediately': 2,
            'critical': 3,
            'fire': 4,
            'danger': 4,
            'help': 1,
            'broken': 1,
            'leak': 2
        }
        
        urgency_score = sum(
            urgency_keywords.get(word.lower(), 0)
            for word in message.split()
        )
        
        # Emotion classification
        compound = vader_scores['compound']
        
        emotion_profile = {
            'sentiment': {
                'polarity': blob.sentiment.polarity,
                'subjectivity': blob.sentiment.subjectivity,
                'compound': compound,
                'positive': vader_scores['pos'],
                'negative': vader_scores['neg'],
                'neutral': vader_scores['neu']
            },
            'urgency': {
                'score': urgency_score,
                'level': self._urgency_level(urgency_score)
            },
            'emotion': self._classify_emotion(compound),
            'requires_escalation': urgency_score >= 3 or compound < -0.6
        }
        
        return emotion_profile
    
    def _urgency_level(self, score):
        if score >= 3:
            return 'critical'
        elif score >= 2:
            return 'high'
        elif score >= 1:
            return 'medium'
        return 'low'
    
    def _classify_emotion(self, compound):
        if compound >= 0.5:
            return 'satisfied'
        elif compound >= 0.1:
            return 'calm'
        elif compound >= -0.1:
            return 'neutral'
        elif compound >= -0.5:
            return 'concerned'
        else:
            return 'frustrated'
```

**Integration:**
```python
class SmartChatbot:
    def __init__(self, user_id=None, session_id=None):
        # ...
        self.emotion_analyzer = EmotionAnalyzer()
    
    def process_message(self, user_message):
        # Analyze emotions
        emotion_data = self.emotion_analyzer.analyze_emotion(user_message)
        
        # Escalate if needed
        if emotion_data['requires_escalation']:
            self._escalate_complaint(emotion_data)
        
        # Adjust response tone based on emotion
        response = self._generate_response(intent, emotion_data)
        return response
```

---

### Enhancement 4: Voice Input Integration (STEP 6)

**Frontend Implementation:**

**HTML** (`templates/chatbot.html`):
```html
<div class="voice-input-container">
    <button id="voiceBtn" class="btn btn-voice">
        <i class="bi bi-mic-fill"></i>
        <span class="status-text">Tap to speak</span>
    </button>
    <canvas id="waveform" width="200" height="50"></canvas>
</div>
```

**JavaScript** (`static/js/voice-handler.js`):
```javascript
class VoiceInputHandler {
    constructor() {
        this.recognition = new (window.SpeechRecognition || 
                                window.webkitSpeechRecognition)();
        this.setupRecognition();
    }
    
    setupRecognition() {
        this.recognition.continuous = false;
        this.recognition.interimResults = true;
        this.recognition.lang = 'en-US';
        
        this.recognition.onstart = () => {
            console.log('Voice recognition started');
            this.updateUI('listening');
        };
        
        this.recognition.onresult = (event) => {
            const transcript = Array.from(event.results)
                .map(result => result[0].transcript)
                .join('');
            
            if (event.results[0].isFinal) {
                this.sendMessage(transcript);
            } else {
                this.showInterim(transcript);
            }
        };
        
        this.recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            this.updateUI('error');
        };
        
        this.recognition.onend = () => {
            this.updateUI('ready');
        };
    }
    
    startListening() {
        this.recognition.start();
    }
    
    stopListening() {
        this.recognition.stop();
    }
    
    sendMessage(transcript) {
        // Send to chatbot API
        fetch('/chatbot/message', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                message: transcript,
                input_type: 'voice'
            })
        })
        .then(response => response.json())
        .then(data => {
            this.displayResponse(data);
        });
    }
}

// Initialize
const voiceHandler = new VoiceInputHandler();
document.getElementById('voiceBtn').addEventListener('click', () => {
    voiceHandler.startListening();
});
```

**Audio Visualization:**
```javascript
class WaveformVisualizer {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.isAnimating = false;
    }
    
    startAnimation() {
        this.isAnimating = true;
        this.animate();
    }
    
    animate() {
        if (!this.isAnimating) return;
        
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Draw waveform bars
        const barCount = 20;
        const barWidth = this.canvas.width / barCount;
        
        for (let i = 0; i < barCount; i++) {
            const height = Math.random() * this.canvas.height;
            this.ctx.fillStyle = '#667eea';
            this.ctx.fillRect(
                i * barWidth,
                (this.canvas.height - height) / 2,
                barWidth - 2,
                height
            );
        }
        
        requestAnimationFrame(() => this.animate());
    }
    
    stopAnimation() {
        this.isAnimating = false;
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    }
}
```

---

### Enhancement 5: Learning & Feedback Loop (STEP 7)

**Feedback Collection:**
```python
class ChatbotFeedback:
    @staticmethod
    def collect_feedback(session_id, rating, comments=None):
        """
        rating: 1-5 stars
        comments: optional user feedback
        """
        db = get_db()
        db.execute("""
            INSERT INTO chatbot_feedback 
            (session_id, rating, comments, created_at)
            VALUES (?, ?, ?, datetime('now'))
        """, (session_id, rating, comments))
        db.commit()
    
    @staticmethod
    def analyze_feedback():
        """Generate insights from feedback"""
        db = get_db()
        stats = db.execute("""
            SELECT 
                AVG(rating) as avg_rating,
                COUNT(*) as total_feedback,
                SUM(CASE WHEN rating >= 4 THEN 1 ELSE 0 END) as positive,
                SUM(CASE WHEN rating <= 2 THEN 1 ELSE 0 END) as negative
            FROM chatbot_feedback
            WHERE created_at > datetime('now', '-30 days')
        """).fetchone()
        
        return dict(stats)
```

**Learning from Interactions:**
```python
class ChatbotLearning:
    @staticmethod
    def learn_from_misclassifications():
        """
        Identify frequently misunderstood intents
        and suggest pattern improvements
        """
        db = get_db()
        
        # Find messages where user had to rephrase
        misunderstood = db.execute("""
            SELECT ch1.message, ch1.intent
            FROM chat_history ch1
            JOIN chat_history ch2 ON ch1.session_id = ch2.session_id
            WHERE ch1.intent = 'unknown'
              AND ch2.created_at > ch1.created_at
              AND ch2.intent != 'unknown'
              AND JULIANDAY(ch2.created_at) - JULIANDAY(ch1.created_at) < 0.01
            ORDER BY ch1.created_at DESC
            LIMIT 50
        """).fetchall()
        
        # Analyze patterns
        return [dict(row) for row in misunderstood]
```

---

## 🗂️ File Structure (Enhanced)

```
Smart Complaint System/
│
├── ai_engine/
│   ├── __init__.py
│   ├── chatbot.py              # Core chatbot logic ✅
│   ├── emotion.py              # Emotion analysis ✅
│   ├── nlu_engine.py           # 🆕 Advanced NLP
│   ├── context_manager.py      # 🆕 Conversation context
│   ├── learning.py             # Existing learning module
│   └── response_generator.py   # 🆕 Dynamic response generation
│
├── chatbot/
│   ├── __init__.py
│   ├── routes.py               # API endpoints ✅
│   └── feedback.py             # 🆕 Feedback collection
│
├── templates/
│   ├── chatbot.html            # 🆕 Chat interface
│   └── chatbot_admin.html      # 🆕 Analytics dashboard
│
├── static/
│   ├── css/
│   │   └── chatbot.css         # 🆕 Chat styling
│   └── js/
│       ├── chatbot.js          # 🆕 Chat logic
│       ├── voice-handler.js    # 🆕 Voice input
│       └── waveform.js         # 🆕 Audio visualization
│
└── tests/
    ├── test_chatbot.py         # 🆕 Unit tests
    ├── test_nlu.py             # 🆕 NLP tests
    └── test_integration.py     # 🆕 End-to-end tests
```

---

## 📊 Database Migrations Required

### Migration 1: Conversation Context
```sql
CREATE TABLE IF NOT EXISTS conversation_contexts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT UNIQUE NOT NULL,
    user_id INTEGER,
    state TEXT DEFAULT 'greeting',
    entities TEXT,  -- JSON: extracted information
    history TEXT,   -- JSON: conversation history
    metadata TEXT,  -- JSON: additional data
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE INDEX idx_context_session ON conversation_contexts(session_id);
CREATE INDEX idx_context_user ON conversation_contexts(user_id);
```

### Migration 2: Chatbot Feedback
```sql
CREATE TABLE IF NOT EXISTS chatbot_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    user_id INTEGER,
    rating INTEGER CHECK(rating BETWEEN 1 AND 5),
    comments TEXT,
    helpful_responses TEXT,  -- JSON array of helpful message IDs
    unhelpful_responses TEXT,  -- JSON array of unhelpful message IDs
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE INDEX idx_feedback_session ON chatbot_feedback(session_id);
CREATE INDEX idx_feedback_rating ON chatbot_feedback(rating);
```

### Migration 3: Intent Logs (for learning)
```sql
CREATE TABLE IF NOT EXISTS intent_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message TEXT NOT NULL,
    detected_intent TEXT,
    confidence REAL,
    actual_intent TEXT,  -- Corrected by user or admin
    user_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE INDEX idx_intent_detected ON intent_logs(detected_intent);
CREATE INDEX idx_intent_actual ON intent_logs(actual_intent);
```

---

## 🧪 Testing Requirements

### Unit Tests
```python
# tests/test_chatbot.py

def test_intent_detection():
    chatbot = SmartChatbot()
    
    assert chatbot.detect_intent("Hello!") == "greeting"
    assert chatbot.detect_intent("I want to file a complaint") == "complaint_new"
    assert chatbot.detect_intent("Check my status") == "complaint_status"

def test_emotion_detection():
    chatbot = SmartChatbot()
    
    # High urgency
    emotion = chatbot.detect_emotion("Emergency! Fire in the building!")
    assert emotion == "high_urgency"
    
    # Normal
    emotion = chatbot.detect_emotion("The fan is not working")
    assert emotion in ["normal", "medium_urgency"]

def test_complaint_extraction():
    chatbot = SmartChatbot(user_id=1)
    
    complaint = chatbot.extract_complaint_info(
        "The electrical socket in Lab-3 is sparking"
    )
    
    assert complaint['category'] == "Electrical"
    assert "Lab-3" in complaint['location']
```

### Integration Tests
```python
# tests/test_integration.py

def test_end_to_end_complaint_filing():
    """Test complete conversation flow"""
    chatbot = SmartChatbot(user_id=1, session_id="test-session")
    
    # 1. Greeting
    response = chatbot.process_message("Hi")
    assert "Hello" in response['message']
    
    # 2. File complaint
    response = chatbot.process_message("My room AC is broken")
    assert response['action'] == 'confirm_complaint'
    assert 'AC' in response['message']
    
    # 3. Confirm
    complaint_data = response['data']
    result = chatbot.submit_complaint(complaint_data)
    assert result['success'] == True
    assert result['complaint_id'] > 0
```

---

## 🚀 Deployment Checklist

### Pre-Deployment
- [ ] All unit tests passing
- [ ] Integration tests passing
- [ ] Performance benchmarks met
- [ ] Security audit completed
- [ ] Database migrations tested
- [ ] Error handling verified
- [ ] Logging configured

### Deployment Steps
1. **Database Migration**
   ```bash
   python migrate_chatbot.py
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**
   ```bash
   export FLASK_ENV=production
   export CHATBOT_DEBUG=false
   ```

4. **Start Service**
   ```bash
   python app.py
   ```

### Post-Deployment
- [ ] Monitor error logs
- [ ] Track response times
- [ ] Collect user feedback
- [ ] Analyze conversation metrics
- [ ] Iterate based on data

---

## 📈 Performance Targets

| Metric | Target | Current | Gap |
|--------|--------|---------|-----|
| Response Time | < 2s | ~1.5s | ✅ |
| Intent Accuracy | > 85% | ~75% | 🔴 |
| Uptime | > 99% | TBD | - |
| Concurrent Users | 100+ | TBD | - |
| Messages/day | 1000+ | TBD | - |

---

## 🔧 Configuration

### Environment Variables
```bash
# .env file
CHATBOT_DEBUG=true
CHATBOT_LOG_LEVEL=INFO
CHATBOT_MAX_HISTORY=50
CHATBOT_SESSION_TIMEOUT=3600
CHATBOT_ENABLE_VOICE=true
CHATBOT_FEEDBACK_ENABLED=true
NLU_MODEL_PATH=/models/intent_classifier
EMOTION_MODEL_PATH=/models/emotion_analyzer
```

### Feature Flags
```python
# config.py
CHATBOT_CONFIG = {
    'features': {
        'voice_input': True,
        'text_to_speech': False,  # Future
        'multi_language': False,  # Future
        'advanced_nlu': False,    # To be enabled in Phase 2
        'learning_mode': True,
        'feedback_collection': True
    },
    'limits': {
        'max_message_length': 500,
        'max_messages_per_session': 100,
        'session_timeout_minutes': 60
    },
    'models': {
        'intent_confidence_threshold': 0.75,
        'emotion_threshold': 0.6
    }
}
```

---

## 📝 Next Implementation Steps

### Immediate (This Week)
1. ✅ Review and approve technical specification
2. 🔲 Create UI mockups for chat interface
3. 🔲 Design conversation flow diagrams
4. 🔲 Set up testing framework

### Short Term (Next 2 Weeks)
1. 🔲 Implement enhanced emotion detection
2. 🔲 Build chat interface UI
3. 🔲 Add voice input support
4. 🔲 Create feedback mechanism

### Medium Term (Month 1)
1. 🔲 Integrate advanced NLP
2. 🔲 Implement context management
3. 🔲 Build analytics dashboard
4. 🔲 Conduct user testing

---

**Document Version**: 1.0  
**Last Updated**: February 11, 2026  
**Status**: Ready for Implementation  
**Next Review**: After STEP 2 completion
