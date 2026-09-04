"""
AI Chatbot Engine for Smart Complaint System
Handles natural language conversations, complaint registration, and status checking
"""

import json
import re
from datetime import datetime
from database import get_db
from ai_service import analyze_complaint_text
from .intent_detector import detect_intent as engine_detect_intent
from .response_generator import ResponseGenerator
from .vision_engine import analyze_vision_evidence
from .image_processor import preprocess_complaint_image
from .audio_processor import AudioAIProcessor
from .fusion import AiFusionModule
import os

class SmartChatbot:
    # Interaction States
    STATE_IDLE = 'idle'
    STATE_COLLECTING_CATEGORY = 'collecting_category'
    STATE_COLLECTING_DESCRIPTION = 'collecting_description'
    STATE_COLLECTING_CITY = 'collecting_city'
    STATE_COLLECTING_LOCATION = 'collecting_location'
    STATE_COLLECTING_MEDIA = 'collecting_media'
    STATE_CONFIRMING = 'confirming'
    STATE_TRACKING_ID = 'tracking_id'

    def get_complaint_status_by_ref(self, ref_no, response):
        """Fetch and format complaint status by Reference Number"""
        db = get_db()
        row = db.execute("""
            SELECT c.id, c.ref_no, c.title, c.status, c.created_at, c.assigned_to, w.name as worker_name, w.avg_resolution_time
            FROM complaints c
            LEFT JOIN workers w ON c.worker_id = w.id
            WHERE c.ref_no = ?
        """, (ref_no,)).fetchone()

        if row:
            if row['status'] == 'Resolved':
                status_header = self.response_gen.get_resolution_message(row['ref_no'])
            else:
                status_header = f"📋 **OFFICIAL STATUS REPORT: {row['ref_no']}**"

            worker = row['worker_name'] or "Searching for available Field Officer..."
            dept = row['assigned_to'] or "General Administration"
            est_time = f"{row['avg_resolution_time'] or 60} mins"
            
            appreciation = self.response_gen.get_appreciation_message()
            feedback = self.response_gen.get_feedback_prompt()
            
            response['message'] = (
                f"{status_header}\n\n"
                f"**Current Status:** {row['status']}\n"
                f"**Assigned Department:** {dept}\n"
                f"**Field Officer:** {worker}\n"
                f"**Estimated Resolution:** {est_time}\n"
                f"**Case Subject:** {row['title']}\n\n"
                f"{appreciation}\n\n"
                f"{feedback}"
            )
            response['suggestions'] = ["Excellent", "Good", "Satisfactory", "Needs Improvement"]
            self.state = self.STATE_IDLE
        else:
            response['message'] = f"Reference Number **{ref_no}** not found. Please check and try again."
            self.state = self.STATE_TRACKING_ID
        return response

    def __init__(self, user_id=None, session_id=None, lang='en'):
        self.user_id = user_id
        self.session_id = session_id
        self.lang = lang
        self.context = {}  # Stores complaint draft
        self.state = self.STATE_IDLE
        self.response_gen = ResponseGenerator(lang=lang)
        
        # Load state and context from DB if session_id provided
        if self.session_id:
            try:
                self.load_context()
            except Exception as e:
                print(f"Error loading context: {e}")

    def load_context(self):
        """Load conversation state and context from database"""
        db = get_db()
        row = db.execute(
            "SELECT current_state, context_data FROM chat_sessions WHERE session_id = ?", 
            (self.session_id,)
        ).fetchone()
        
        if row:
            self.state = row['current_state'] or self.STATE_IDLE
            if row['context_data']:
                self.context = json.loads(row['context_data'])
            else:
                self.context = {}

    def save_context(self):
        """Persist conversation state and context to database"""
        if not self.session_id:
            return
            
        db = get_db()
        try:
            db.execute("""
                INSERT INTO chat_sessions (session_id, user_id, current_state, context_data, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(session_id) DO UPDATE SET
                    current_state = excluded.current_state,
                    context_data = excluded.context_data,
                    updated_at = excluded.updated_at
            """, (self.session_id, self.user_id, self.state, json.dumps(self.context)))
            db.commit()
        except Exception as e:
            print(f"Error saving context: {e}")

    def get_user_context(self):
        """Fetch user details from DB to build context for LLM"""
        context_data = {'language': self.lang}
        if self.user_id:
            try:
                db = get_db()
                row = db.execute("SELECT first_name, last_name, role FROM users WHERE id = ?", (self.user_id,)).fetchone()
                if row:
                    context_data['user_name'] = f"{row['first_name']} {row['last_name']}"
                    context_data['user_role'] = row['role']
            except Exception as e:
                print(f"[Chatbot Context] Error: {e}")
        return context_data
        
    def detect_intent(self, message):
        """Detect user intent using AI engine with bilingual support"""
        processed_message = message
        
        # If in Hindi, translate to English for better intent detection
        if self.lang == 'hi' and message:
            try:
                from deep_translator import GoogleTranslator
                # Basic check to avoid re-translating if already English
                ascii_ratio = sum(1 for c in message if ord(c) < 128) / len(message) if len(message) > 0 else 1
                if ascii_ratio < 0.8:
                    processed_message = GoogleTranslator(source='hi', target='en').translate(message)
                    print(f"[Chatbot] Intent Translation: {message} -> {processed_message}")
            except Exception as e:
                print(f"[Chatbot] Intent Translation Error: {e}")

        result = engine_detect_intent(processed_message)
        return result['intent']
    
    def detect_emotion(self, message):
        """Detect emotional urgency in message with bilingual support"""
        processed_message = message
        if self.lang == 'hi' and message:
             try:
                from deep_translator import GoogleTranslator
                ascii_ratio = sum(1 for c in message if ord(c) < 128) / len(message) if len(message) > 0 else 1
                if ascii_ratio < 0.8:
                    processed_message = GoogleTranslator(source='hi', target='en').translate(message)
             except:
                 pass

        urgent_keywords = ['urgent', 'emergency', 'asap', 'immediately', 'critical', 'serious', 
                          'fire', 'accident', 'danger', 'help', 'broken', 'leak']
        
        message_lower = processed_message.lower()
        urgency_score = sum(1 for keyword in urgent_keywords if keyword in message_lower)
        
        if urgency_score >= 2:
            return 'high_urgency'
        elif urgency_score == 1:
            return 'medium_urgency'
        return 'normal'
    
    def extract_complaint_info(self, message, city=None, existing_draft=None):
        """Extract complaint details from natural language"""
        # Use existing AI service for analysis
        db = get_db()
        
        # Cache workers to avoid repeated queries
        if not hasattr(self, '_workers_cache'):
            workers = db.execute(
                "SELECT id, name, skill, location_zone as location, current_load as load FROM workers WHERE is_active = 1"
            ).fetchall()
            self._workers_cache = [dict(w) for w in workers]
        
        # Check for repeated complaints (Step 8)
        is_repetitive = False
        if self.user_id:
            # Simple check: same user, similar message in the last 24 hours
            recent_similar = db.execute("""
                SELECT id FROM complaints 
                WHERE user_id = ? 
                AND (title LIKE ? OR description LIKE ?)
                AND created_at > datetime('now', '-1 day')
                LIMIT 1
            """, (self.user_id, f"%{message[:20]}%", f"%{message[:20]}%")).fetchone()
            if recent_similar:
                is_repetitive = True

        analysis = analyze_complaint_text(message, available_workers=self._workers_cache, is_repetitive=is_repetitive, city=city)
        
        result = {
            'title': analysis.get('title', 'Complaint via Chatbot'),
            'description': message,
            'category': analysis.get('category', 'Other'),
            'priority': analysis.get('priority', 'Medium'),
            'location': analysis.get('location') or 'Not specified',
            'city': city,
            'assigned_to': analysis.get('department', 'General Administration'),
            'sentiment_score': analysis.get('sentiment_score', 0.5),
            'is_escalated': analysis.get('is_escalated', False),
            'escalation_reason': " | ".join(analysis.get('escalation_reasons', [])),
            'worker_id': analysis.get('worker_id'),
            'emotion_data': json.dumps(analysis.get('emotions', {})),
            'emotions_raw': analysis.get('emotions', {}), # Keep for feedback logic
            'is_repetitive': is_repetitive
        }

        # If it's an edit, preserve explicitly set fields
        if existing_draft:
            for key in ['location', 'category', 'priority', 'city']:
                if existing_draft.get(key) and existing_draft[key] != 'Not specified':
                    result[key] = existing_draft[key]
        
        return result
    
    def process_message(self, user_message, attachment=None):
        """
        Process user message through state machine
        Args:
            user_message (str): User's text input
            attachment (str): Optional filename of uploaded file
        """
        response = {
            'message': '',
            'action': None,
            'data': {},
            'suggestions': []
        }

        # 1. State Machine Handling
        # 1. State Machine Handling
        if self.state == self.STATE_COLLECTING_DESCRIPTION:
            response = self.handle_description_input(user_message, response)

        elif self.state == self.STATE_COLLECTING_MEDIA:
            response = self.handle_media_input(user_message, attachment, response)

        elif self.state == self.STATE_COLLECTING_LOCATION:
            response = self.handle_location_input(user_message, response)

        elif self.state == self.STATE_COLLECTING_CITY:
            # City is now handled as part of the location or routing later if needed, 
            # but keeping the handler for state consistency
            response = self.handle_city_input(user_message, response)
            
        elif self.state == self.STATE_CONFIRMING:
            response = self.handle_confirmation_input(user_message, response)
            
        elif self.state == self.STATE_TRACKING_ID:
            response = self.handle_tracking_id_input(user_message, response)

        else:
            # 2. Intent Detection (IDLE State)
            intent = self.detect_intent(user_message)
            emotion = self.detect_emotion(user_message)
            response['emotion'] = emotion

            # 3. Intent Dispatch
            if intent == 'greeting':
                response['message'] = self.response_gen.generate('greeting', self.state)
                response['suggestions'] = ["Report Incident", "Upload Evidence", "Track Case Status", "Report Emergency", "Contact Support"]
                
            elif intent == 'register_complaint':
                self.start_complaint_flow(user_message, response)
                
            elif intent == 'track_complaint':
                self.handle_track_complaint(response, user_message)

            elif intent == 'cancel_complaint':
                response['message'] = "To terminate an incident reporting session, please provide the official Case ID or Reference Number."
                response['suggestions'] = ["Track Case Status"]

            elif intent == 'emergency':
                # Identify specific hazard context if possible
                hazard_type = 'public_safety_risk' # Default
                msg_lower = user_message.lower()
                
                if any(k in msg_lower for k in ['fire', 'smoke', 'burning']):
                    hazard_type = 'fire_hazard'
                elif any(k in msg_lower for k in ['accident', 'crash', 'collision']):
                    hazard_type = 'road_accident'
                elif any(k in msg_lower for k in ['gas', 'leak', 'smell', 'cylinder']):
                    hazard_type = 'gas_leak'
                elif any(k in msg_lower for k in ['cow', 'dog', 'animal', 'traffic']):
                    hazard_type = 'animal_on_road'

                response['message'] = self.response_gen.generate('emergency', self.state, context={'hazard_type': hazard_type})
                response['emotion'] = 'high_urgency'
                response['suggestions'] = ["Report Emergency Location", "Contact Support"]
                # Don't require login here, let them explain the situation first

            elif intent == 'general_inquiry' or intent == 'help':
                user_context = self.get_user_context()
                response['message'] = self.response_gen.generate_dynamic_response(user_message, user_context)
                response['suggestions'] = ["Report Incident", "Upload Evidence", "Track Case Status", "Report Emergency", "Contact Support"]
                
            elif intent == 'thanks':
                response['message'] = self.response_gen.generate('thanks', self.state)
                
            elif intent == 'goodbye':
                response['message'] = self.response_gen.generate('goodbye', self.state)
                response['action'] = 'end_session'
                
            else:
                # Fallback: Assume complaint if long enough
                if len(user_message.split()) > 5:
                    self.start_complaint_flow(user_message, response)
                else:
                    user_context = self.get_user_context()
                    response['message'] = self.response_gen.generate_dynamic_response(user_message, user_context)
                    response['suggestions'] = ["File a complaint", "Check status"]
                
        self.save_context()

        # --- FINAL BILINGUAL SUPPORT ---
        if response.get('suggestions'):
            response['suggestions'] = self.response_gen.translate_items(response['suggestions'])

        return response

    # --- State Handlers ---

    def start_complaint_flow(self, message, response):
        """Initialize formal guided registration flow"""
        self.context['draft'] = {
            'title': 'New Safety Incident',
            'description': '',
            'category': 'Safety & Operations',
            'priority': 'Normal',
            'location': 'Not specified',
            'city': 'Korba Coalfield' # Default
        }
        
        self.state = self.STATE_COLLECTING_DESCRIPTION
        response['message'] = "Official registration initiated. " + self.response_gen.generate(None, self.state)
        return response

    def handle_description_input(self, message, response):
        """Step 1: Process Issue Description and move to Media"""
        existing_draft = self.context.get('draft')
        info = self.extract_complaint_info(message, city=existing_draft.get('city'), existing_draft=existing_draft)
        self.context['draft'] = info
        
        # --- EMOTION-AWARE ESCALATION FEEDBACK (STEP 8) ---
        analysis_data = {
            'emotions': info.get('emotions_raw', {}),
            'is_repetitive': info.get('is_repetitive', False)
        }
        emotion_feedback = self.response_gen.get_emotion_escalation_feedback(analysis_data)
        
        prefix = f"Incident detail recorded: **{info['title']}**.\n\n"
        if emotion_feedback:
            prefix += f"{emotion_feedback}\n\n"
            
        self.state = self.STATE_COLLECTING_MEDIA
        response['message'] = prefix + self.response_gen.generate(None, self.state)
        response['suggestions'] = ["Skip Documentation", "Attach Official Media"]
        return response

    def handle_media_input(self, message, attachment, response):
        """Step 2: Process Media (Multi-Modal), perform AI Analysis, and move to Location"""
        draft = self.context.get('draft', {})
        
        if attachment:
            self.context['draft']['attachment'] = attachment
            ext = attachment.split('.')[-1].lower()
            
            # 1. Handle Voice Note / Audio
            if ext in ['webm', 'wav', 'mp3', 'm4a', 'ogg']:
                try:
                    response['message'] = self.response_gen.get_voice_feedback() + "\n\n"
                    # Transcribe and analyze will be finalized during submit_complaint 
                    # OR we can log it here. For now, we provide the mode-specific feedback.
                except Exception as e:
                    print(f"[Chatbot Audio] Error: {e}")
                    response['message'] = "Voice documentation has been attached to the case file.\n\n"
            
            # 2. Handle Photographic Evidence (Image)
            else:
                # --- AI VISION ANALYSIS (CORE FEATURE) ---
                try:
                    # 1. Image Preprocessing
                    upload_dir = os.path.join('static', 'uploads')
                    file_path = os.path.join(upload_dir, attachment)
                    
                    if os.path.exists(file_path):
                        # Preprocess
                        proc_path = preprocess_complaint_image(file_path)
                        
                        # 2. Vision Inference
                        vision_results = analyze_vision_evidence(proc_path or file_path)
                        
                        # 3. Multi-Modal Fusion
                        # We 'fuse' the previous text analysis with current visual evidence
                        fused = AiFusionModule.fuse_analysis(draft, vision_results)
                        
                        # 4. Update Draft with AI-driven decisions
                        self.context['draft']['priority'] = fused['final_priority']
                        self.context['draft']['category'] = fused['final_category']
                        self.context['draft']['is_escalated'] = fused['is_escalated']
                        self.context['draft']['escalation_reason'] = " | ".join(fused.get('escalation_reasons', []))
                        
                        # 5. Generate transparent AI feedback
                        ai_feedback = self.response_gen.get_ai_vision_feedback(fused)
                        response['message'] = f"Media documentation has been successfully analyzed.\n\n{ai_feedback}\n\n"
                except Exception as e:
                    print(f"[Chatbot Vision Fusion] Error: {e}")
                    response['message'] = "Media documentation has been attached to the case file.\n\n"
        
        self.state = self.STATE_COLLECTING_LOCATION
        response['message'] += self.response_gen.generate(None, self.state)
        response['suggestions'] = ["Current Geo-Location", "Manual Address Entry"]
        return response

    def handle_location_input(self, message, response):
        """Step 3: Process Location and move to Confirmation"""
        msg_lower = message.lower()
        loc_msg = message.replace("My current location is:", "").replace("📍 Location Captured:", "").strip()
        
        # 1. Handle Denied/Manual Request
        if "manual" in msg_lower or "deny" in msg_lower or "refuse" in msg_lower:
            response['message'] = self.response_gen.TEMPLATES['location_services']['denied_fallback'] + "\n\n" + self.response_gen.TEMPLATES['location_services']['manual_entry_prompt']
            return response

        # 2. Handle Failed GPS
        if loc_msg.lower() == "current location" or loc_msg.lower() == "current geo-location":
            response['message'] = "Automated coordinate retrieval was unsuccessful. " + self.response_gen.TEMPLATES['location_services']['manual_entry_prompt']
            return response

        # 3. Successful Capture (GPS or Manual Text)
        self.context['draft']['location'] = loc_msg
        
        # Determine if it was automated or manual for tailored feedback
        is_automated = "My current location is:" in message or "📍 Location Captured:" in message
        
        if is_automated:
            feedback = self.response_gen.TEMPLATES['location_services']['capture_success']
        else:
            feedback = f"Manual address recorded: **{loc_msg}**. " + self.response_gen.TEMPLATES['location_services']['benefit_explanation']

        self.state = self.STATE_CONFIRMING
        response['message'] = f"{feedback}\n\n" + self.response_gen.get_confirmation_summary(self.context['draft'])
        response['suggestions'] = ["Confirm & Submit", "Adjust Priority", "Modify Description", "Cancel Session"]
        return response

    def handle_city_input(self, message, response):
        """Handle city selection input"""
        city_lower = message.lower().strip()
        
        # Simple mapping for city names
        cities = {
            'jharia': 'Jharia Coalfield',
            'raniganj': 'Raniganj Coalfield',
            'korba': 'Korba Coalfield',
            'singrauli': 'Singrauli Coalfield',
            'talcher': 'Talcher Coalfield'
        }
        
        selected_city = None
        for key, val in cities.items():
            # Check for exact match or boundary match to avoid partials
            if key in city_lower:
                selected_city = val
                break
        
        if not selected_city:
            # Try to match the full name if user typed it
            if "coalfield" in city_lower or "mine" in city_lower:
                for key, val in cities.items():
                    if key in city_lower:
                        selected_city = val
                        break

        if selected_city:
            self.context['draft']['city'] = selected_city
            self.state = self.STATE_COLLECTING_LOCATION
            response['message'] = f"Jurisdiction recorded for **{selected_city}**. " + self.response_gen.generate(None, self.STATE_COLLECTING_LOCATION)
            response['suggestions'] = ["Current Geo-Location", "Manual Address Entry"]
        else:
            response['message'] = "Invalid selection. Please specify one of the following Coalfields: Jharia, Raniganj, Korba, Singrauli, or Talcher."
            response['suggestions'] = ["Jharia", "Raniganj", "Korba", "Singrauli", "Talcher"]
            
        return response



    def handle_confirmation_input(self, message, response):
        """Handle the confirmation or editing options"""
        msg = message.lower()
        
        if 'yes' in msg or 'submit' in msg:
            return self.submit_complaint(response)
            
        elif 'priority' in msg or 'change priority' in msg or 'adjust' in msg:
            response['message'] = "Select the appropriate priority level for this incident:"
            response['suggestions'] = ["High Priority", "Normal Priority", "Low Priority"]
            return response

        elif 'coalfield' in msg or 'change zone' in msg or 'change coalfield' in msg or 'mine' in msg:
            response['message'] = "Select the Coalfield with jurisdiction over this matter:"
            response['suggestions'] = ["Jharia", "Raniganj", "Korba", "Singrauli", "Talcher"]
            return response
            
        elif 'high' in msg or 'normal' in msg or 'medium' in msg or 'low' in msg:
            # Handle priority selection
            p = 'High' if 'high' in msg else ('Normal' if ('normal' in msg or 'medium' in msg) else 'Low')
            self.context['draft']['priority'] = p
            response['message'] = f"Incident priority level updated to **{p}**.\n\n" + self.response_gen.get_confirmation_summary(self.context['draft'])
            response['suggestions'] = ["Confirm & Submit", "Adjust Priority", "Change Jurisdiction", "Modify Description", "Cancel Session"]
            return response

        elif 'description' in msg or 'modify' in msg or 'edit' in msg:
            self.state = self.STATE_COLLECTING_DESCRIPTION
            response['message'] = "Please provide the revised formal description for your incident:"
            return response
            
        elif 'cancel' in msg:
            self.state = self.STATE_IDLE
            self.context = {}
            response['message'] = "Incident session terminated. How may I further assist you with colliery operations?"
            response['suggestions'] = ["Register a new incident", "Track existing case"]
            return response
            
        else:
            # Check if it's a zone name from a 'Change Zone' request
            city_names = ['jharia', 'raniganj', 'korba', 'singrauli', 'talcher']
            selected_city = None
            for cn in city_names:
                if cn in msg:
                    selected_city = cn.capitalize() + " Coalfield"
                    break
            
            if selected_city:
                self.context['draft']['city'] = selected_city
                response['message'] = f"Jurisdiction updated to **{selected_city}**.\n\n" + self.response_gen.get_confirmation_summary(self.context['draft'])
                response['suggestions'] = ["Confirm & Submit", "Adjust Priority", "Change Jurisdiction", "Modify Description", "Cancel Session"]
                return response

            response['message'] = "Please confirm the summary details. You may also adjust the priority level, change jurisdiction, or modify the description."
            response['suggestions'] = ["Confirm & Submit", "Adjust Priority", "Change Jurisdiction", "Modify Description", "Cancel Session"]
            return response

    def submit_complaint(self, response):
        """Finalize submission to database"""
        if not self.user_id:
            response['message'] = "The incident draft is officially complete. Please **Authenticate (Login/Register)** to proceed with formal submission and enable case tracking."
            response['action'] = 'require_login'
            return response

        draft = self.context.get('draft')
        if not draft:
            response['message'] = "Error: No complaint data found."
            self.state = self.STATE_IDLE
            return response
            
        try:
            db = get_db()
            cursor = db.execute("""
                INSERT INTO complaints 
                (user_id, title, description, category, priority, location, 
                 assigned_to, sentiment_score, is_escalated, worker_id, 
                 emotion_data, escalation_reason, attachment, city)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.user_id,
                draft['title'],
                draft['description'],
                draft['category'],
                draft['priority'],
                draft['location'],
                draft.get('assigned_to', 'General Administration'),
                draft['sentiment_score'],
                1 if draft['is_escalated'] else 0,
                draft.get('worker_id'),
                draft['emotion_data'],
                draft['escalation_reason'],
                draft.get('attachment'),
                draft.get('city', 'Raipur Municipal Corporation')
            ))
            
            complaint_id = cursor.lastrowid
            
             # Update worker load if assigned
            if draft.get('worker_id'):
                db.execute("UPDATE workers SET current_load = current_load + 1 WHERE id = ?", 
                          (draft['worker_id'],))
            
            # --- NOTIFY ADMINS IF ESCALATED ---
            if draft['is_escalated']:
                admins = db.execute("SELECT id FROM users WHERE is_admin = 1").fetchall()
                notification_msg = f"⚠️ HIGH PRIORITY: New complaint specific to {draft['category']} at {draft['location']}. Reason: {draft.get('escalation_reason')}"
                
                for admin in admins:
                    db.execute("INSERT INTO notifications (user_id, complaint_id, message) VALUES (?, ?, ?)",
                              (admin['id'], complaint_id, notification_msg))
            
            db.commit()
            
            success_msg = self.response_gen.get_success_message(complaint_id)
            appreciation = self.response_gen.get_appreciation_message()
            feedback = self.response_gen.get_feedback_prompt()
            
            response['message'] = f"{success_msg}\n\n{appreciation}\n\n{feedback}"
            response['suggestions'] = ["Excellent", "Good", "Satisfactory", "Needs Improvement"]
            
            # --- START BACKGROUND AUDIO PROCESSING (IF APPLICABLE) ---
            if draft.get('attachment'):
                ext = draft['attachment'].split('.')[-1].lower()
                if ext in ['webm', 'wav', 'mp3', 'm4a', 'ogg']:
                    from flask import current_app
                    upload_dir = os.path.join('static', 'uploads')
                    audio_path = os.path.join(upload_dir, draft['attachment'])
                    AudioAIProcessor.process_background(complaint_id, audio_path, current_app.app_context())

            self.state = self.STATE_IDLE
            self.context = {}
            
            success_msg = self.response_gen.get_success_message(complaint_id)
            if draft.get('is_escalated'):
                success_msg += "\n\n" + self.response_gen.get_escalation_message(draft.get('escalation_reason'))
                
            response['message'] = success_msg
            response['action'] = 'complaint_submitted'
            response['data'] = {'complaint_id': complaint_id}
            
        except Exception as e:
            print(f"Submission Error: {e}")
            response['message'] = "An administrative error occurred during the submission process. Please attempt the registration again."
            self.state = self.STATE_IDLE
            
        return response

    def handle_track_complaint(self, response, message=None):
        """Handle complaint complaint request"""
        # Allow checking status without login if ref_no/ID provided

        # Check for ID in message if provided
        import re
        if message:
            # Check for Reference Number pattern (GRV-YYYYMMDD-ABCD)
            ref_match = re.search(r'(GRV-\d{8}-[A-Z0-9]{4})', message.upper())
            if ref_match:
                return self.get_complaint_status_by_ref(ref_match.group(1), response)
            
            # Legacy ID check
            match = re.search(r'#?(\d+)', message)
            if match and len(match.group(1)) < 6: # Avoid picking up timestamps or phone numbers
                 complaint_id = int(match.group(1))
                 return self.get_complaint_status(complaint_id, response)
        
        # If no ID, show recent complaints only if logged in
        if self.user_id:
            db = get_db()
            complaints = db.execute("SELECT id, title, ref_no, status FROM complaints WHERE user_id = ? ORDER BY created_at DESC LIMIT 3", (self.user_id,)).fetchall()
            
            if complaints:
                status_list = ""
                for c in complaints:
                    display_id = c['ref_no'] if c['ref_no'] else f"#{c['id']}"
                    status_list += f"**{display_id}**: {c['title']} ({c['status']})\n"
                response['message'] = f"Here are your recent complaints:\n\n{status_list}\n\n" + self.response_gen.generate(None, self.STATE_TRACKING_ID)
                self.state = self.STATE_TRACKING_ID
            else:
                response['message'] = "You have no active complaints. Would you like to file one?"
                response['suggestions'] = ["File a new complaint"]
        else:
            response['message'] = "Please provide your **Reference Number** (e.g., GRV-2026...) or **Complaint ID** to check the status."
            self.state = self.STATE_TRACKING_ID

    def handle_tracking_id_input(self, message, response):
        """Handle input when waiting for complaint ID"""
        import re
        # Check Reference Number
        ref_match = re.search(r'(GRV-\d{8}-[A-Z0-9]{4})', message.upper())
        if ref_match:
            return self.get_complaint_status_by_ref(ref_match.group(1), response)
            
        match = re.search(r'#?(\d+)', message)
        if match:
            complaint_id = int(match.group(1))
            return self.get_complaint_status(complaint_id, response)
        else:
            if 'cancel' in message.lower() or 'stop' in message.lower():
                self.state = self.STATE_IDLE
                response['message'] = "Complaint tracking cancelled."
            else:
                response['message'] = self.response_gen.generate(None, self.STATE_TRACKING_ID)
            return response

    def get_complaint_status(self, complaint_id, response):
        """Fetch and format complaint status"""
        db = get_db()
        # Fetch complaint + worker details
        row = db.execute("""
            SELECT c.id, c.title, c.status, c.created_at, c.assigned_to, w.name as worker_name, w.avg_resolution_time
            FROM complaints c
            LEFT JOIN workers w ON c.worker_id = w.id
            WHERE c.id = ? AND c.user_id = ?
        """, (complaint_id, self.user_id)).fetchone()

        if row:
            if row['status'] == 'Resolved':
                status_header = self.response_gen.get_resolution_message(f"#{row['id']}")
            else:
                status_header = f"📋 **OFFICIAL CASE REPORT: #{row['id']}**"

            worker = row['worker_name'] or "Pending Officer Assignment"
            dept = row['assigned_to'] or "General Administration"
            # Simple estimation logic
            est_mins = row['avg_resolution_time'] or 60
            est_time = f"{est_mins} mins"
            
            appreciation = self.response_gen.get_appreciation_message()
            feedback = self.response_gen.get_feedback_prompt()
            
            response['message'] = (
                f"{status_header}\n\n"
                f"**Current Status:** {row['status']}\n"
                f"**Assigned Department:** {dept}\n"
                f"**Field Officer:** {worker}\n"
                f"**Estimated Resolution:** {est_time}\n"
                f"**Case Subject:** {row['title']}\n\n"
                f"{appreciation}\n\n"
                f"{feedback}"
            )
            response['suggestions'] = ["Excellent", "Good", "Satisfactory", "Needs Improvement"]
            self.state = self.STATE_IDLE # Done
        else:
            response['message'] = f"Complaint #{complaint_id} not found. Please try again or type 'cancel'."
            # Stay in tracking state to allow retry
            self.state = self.STATE_TRACKING_ID
            
        return response

    def get_complaint_details(self, complaint_id):
        db = get_db()
        row = db.execute("SELECT * FROM complaints WHERE id = ?", (complaint_id,)).fetchone()
        if row:
            return dict(row)
        return None
