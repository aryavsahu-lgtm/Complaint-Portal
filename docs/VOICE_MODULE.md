# Voice Input & Speech-to-Text Module
## Smart Complaint System

This module handles the real-time capture of user voice, transcription into text, and intelligent structuring of the data.

### 1. Overview
The Voice Input Module is designed to bridge the gap between spoken language and structured database records. It uses a hybrid approach:
- **Frontend**: Web Speech API for low-latency, high-accuracy speech-to-text.
- **Backend**: Python-based NLP service for text cleansing, categorization, and priority detection.

### 2. Architecture

```
User (Voice) 
  │
  ▼
[Frontend: VoiceInputModule (JS)]
  │ • Captures Audio
  │ • Handles Noise/Pauses
  │ • Transcribes to Text
  │
  ▼ JSON Payload
  │
[Backend: /api/analyze-complaint]
  │
  ▼
[AI Service (ai_service.py)]
  │ • Removes Filler Words ("um", "uh")
  │ • Extracts Title (First phrase)
  │ • Detects Keywords -> Category
  │ • Detects Urgency -> Priority
  │
  ▼ Structured JSON
  │
[Frontend: Form Auto-Fill]
```

### 3. Key Features

#### A. Dedicated JavaScript Module (`static/js/voice_input.js`)
- **Class-based Design**: `VoiceInputModule` is reusable across different forms.
- **State Management**: Handles 'Listening', 'Processing', and 'Error' states visually.
- **Error Handling**: Gracefully manages microphone permissions, network errors, and browser incompatibility.

#### B. Intelligent Text Processing (`ai_service.py`)
- **Filler Word Removal**: Filters out conversational noise like "actually", "like", "you know".
- **Rule-based NLP**: Uses dictionary mapping and regex for deterministic, fast analysis without heavy ML dependencies.

### 4. Implementation Details

#### Frontend Usage
```javascript
new VoiceInputModule({
    btnId: 'voice-btn',
    statusId: 'voice-status',
    fields: {
        title: 'title',
        description: 'description',
        category: 'category',
        priority: 'priority'
    }
});
```

#### Backend API
- **Endpoint**: `POST /api/analyze-complaint`
- **Input**: `{"text": "The wifi is not working in the hostel"}`
- **Output**:
```json
{
    "status": "success",
    "data": {
        "title": "The wifi is not working...",
        "category": "Infrastructure",
        "priority": "Medium",
        "description": "The wifi is not working in the hostel"
    }
}
```

### 5. Future AI Enhancements
- Integration with OpenAI Whisper for backend-side transcription (for non-Chrome browsers).
- Sentiment analysis to detect user anger/frustration.
