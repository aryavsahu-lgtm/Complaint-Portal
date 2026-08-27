from deep_translator import GoogleTranslator
import re
from ai_engine.emotion import analyze_sentiment
from ai_engine.allocation import allocate_task

class ComplaintAnalyzer:
    def __init__(self, text, available_workers=None):
        self.original_text = text
        self.english_text = text
        self.clean_text = ""
        self.translated = False
        self.available_workers = available_workers or []
        self.keywords = {
            "Occupational Safety": [
                "unsafe", "safety violation", "ppe", "helmet", "harness", "injury", "accident",
                "near miss", "fire", "explosion", "collapse", "trapped", "rescue", "emergency",
                "first aid", "gas", "blasting", "shot firing", "methane", "dust"
            ],
            "Mine Operations": [
                "haul road", "conveyor", "excavator", "truck", "shovel", "drilling", "blasting",
                "production", "dispatch", "machinery", "equipment", "maintenance", "breakdown"
            ],
            "Ventilation & Gas Monitoring": [
                "ventilation", "airflow", "methane", "carbon monoxide", "co", "gas detector", "oxygen",
                "dust level", "respiratory", "fume", "smoke", "underground air", "gas alarm"
            ],
            "Electrical & Mechanical": [
                "power", "electricity", "transformer", "cable", "switchgear", "short circuit", "motor",
                "pump", "generator", "earthing", "electrical", "mechanical", "lockout", "isolation"
            ],
            "Environmental Compliance": [
                "pollution", "dust", "noise", "water quality", "effluent", "discharge", "ash",
                "land reclamation", "topsoil", "forest", "wildlife", "carbon", "emission", "environment"
            ],
            "Labor Welfare": [
                "wages", "attendance", "overtime", "canteen", "housing", "drinking water", "toilet",
                "transport", "harassment", "contract worker", "medical checkup", "benefits", "grievance"
            ],
            "Regulatory Compliance": [
                "inspection", "notice", "permit", "license", "dgms", "compliance", "audit", "record",
                "register", "statutory", "violation", "approval", "reporting", "legal"
            ],
            "Community & Land Relations": [
                "land acquisition", "resettlement", "rehabilitation", "village", "community",
                "compensation", "boundary", "traffic", "public complaint", "stakeholder"
            ]
        }
        self.priority_keywords = {
            "High": ["urgent", "emergency", "fire", "danger", "immediately", "critical", 
                     "severe", "blood", "accident", "health", "spark", "short circuit",
                     "broken", "stuck", "explode", "burn", "now", "unsafe"],
                "Low": ["suggestion", "maybe", "later", "whenever", "can wait", "low priority",
                    "request", "feedback", "improvement", "routine"]
        }
        self.known_locations = [
            "mine", "pit", "seam", "bench", "slope", "shaft", "tunnel", "panel", "face",
            "workshop", "weighbridge", "crusher", "stockyard", "colony", "village", "plant"
        ]

    def translate(self):
        """Translate text to English with timeout protection"""
        try:
            # Skip translation if text is already in English or very short
            if len(self.original_text.split()) < 3:
                return
                
            # Quick check: if mostly ASCII, probably English
            ascii_ratio = sum(1 for c in self.original_text if ord(c) < 128) / len(self.original_text)
            if ascii_ratio > 0.8:
                return
            
            # Try translation with timeout handling
            translator = GoogleTranslator(source='auto', target='en')
            translated = translator.translate(self.original_text[:500])  # Limit length for speed
            
            if translated and translated.lower() != self.original_text.lower():
                self.english_text = translated
                self.translated = True
        except Exception as e:
            # Don't block on translation errors - use original text
            print(f"[Translation] Skipped due to error: {type(e).__name__}")
            self.english_text = self.original_text


    def clean(self):
        text_lower = self.english_text.lower()
        filler_words = ["um", "uh", "like", "actually", "literally", "basically", "you know", "i mean", "sort of", "maybe"]
        for filler in filler_words:
            text_lower = text_lower.replace(f" {filler} ", " ").replace(f"{filler} ", " ")
        self.clean_text = text_lower

    def extract_title(self):
        words = self.clean_text.split()
        if len(words) > 8:
            return " ".join(words[:8]) + "..."
        return self.clean_text.capitalize()

    def categorize(self):
        detected_category = "Other"
        matched_keywords = []

        for category, keywords in self.keywords.items():
            for keyword in keywords:
                if re.search(r'\b' + re.escape(keyword) + r'\b', self.clean_text):
                    detected_category = category
                    matched_keywords.append(keyword)
        
        return detected_category, list(set(matched_keywords))

    def prioritization(self, matched_keywords):
        priority = "Medium"
        
        # Check High
        for keyword in self.priority_keywords["High"]:
            if re.search(r'\b' + re.escape(keyword) + r'\b', self.clean_text):
                priority = "High"
                matched_keywords.append(keyword)
                return priority, matched_keywords
        
        # Check Low
        for keyword in self.priority_keywords["Low"]:
            if re.search(r'\b' + re.escape(keyword) + r'\b', self.clean_text):
                priority = "Low"
                matched_keywords.append(keyword)
                return priority, matched_keywords
                
        return priority, matched_keywords

    def extract_location(self):
        location = ""
        # Check known
        for loc in self.known_locations:
             if re.search(r'\b' + re.escape(loc) + r'\b', self.clean_text):
                 return loc.title()
        
        # Check regex
        match = re.search(r'\b(in|at|near|from)\s+([a-z0-9]+\s?[a-z0-9]*\s?[a-z0-9]*)', self.clean_text)
        if match:
            extracted = match.group(2).strip()
            if extracted not in ["the", "a", "an", "my", "this", "that"]:
                return extracted.title()
        return location

    def route_department(self, category, location, city=None):
        """
        Determines the accountable mine control area from category and evidence.
        This rule-based decision is transparent and remains auditable in the case record.
        Decisions are auditable via the assigned_to field in the database.
        """
        department = "General Administration" # Default
        
        department_map = {
            "Occupational Safety": "Safety Control Room",
            "Mine Operations": "Mine Operations Control",
            "Ventilation & Gas Monitoring": "Ventilation and Gas Control",
            "Electrical & Mechanical": "Electrical and Mechanical Maintenance",
            "Environmental Compliance": "Environment and Sustainability Cell",
            "Labor Welfare": "Worker Welfare and HR",
            "Regulatory Compliance": "Regulatory Affairs and Mine Survey",
            "Community & Land Relations": "Community Relations and Land Management"
        }
        department = department_map.get(category, department)
        if any(term in self.clean_text for term in ["fire", "explosion", "collapse", "trapped", "methane"]):
            department = "Emergency Response Control Room"
        
        # Location based overrides
        if location:
            if "Hostel" in location:
                if category == "Infrastructure":
                    department = "Hostel Maintenance" # Specialized dept
            elif "Library" in location:
                if category == "Infrastructure":
                    department = "Library Maintenance"

        if city:
            department = f"{city} - {department}"

        return department

    def process(self, city=None):
        self.translate()
        self.clean()
        
        title = self.extract_title()
        category, matched_keywords = self.categorize()
        priority, matched_keywords = self.prioritization(matched_keywords)
        location = self.extract_location()
        department = self.route_department(category, location, city=city)
        
        # --- MODULE 2: AI-Optimized Workforce Allocation ---
        self.worker_id = None
        if self.available_workers:
             # STEP 8: Detect sub-skill for better matching
             detected_sub_skill = None
             if "electrical" in self.clean_text or "power" in self.clean_text:
                 detected_sub_skill = "Electrical"
             elif "ventilation" in self.clean_text or "methane" in self.clean_text or "gas" in self.clean_text:
                 detected_sub_skill = "Ventilation"
                 
             self.worker_id = allocate_task(category, location, self.available_workers, detected_sub_skill, priority)
             if self.worker_id:
                  print(f"AI Allocation: Task assigned to Worker ID {self.worker_id} (Skill: {detected_sub_skill or category})")
                  # STEP 10: Notification Simulation
                  print(f">>> TECHNICIAN ALERT: New Task Assigned to Worker {self.worker_id}. Priority: {priority}")
        
        sentiment_data = analyze_sentiment(self.clean_text)
        self.sentiment_score = sentiment_data['score']
        self.sentiment_label = sentiment_data['sentiment']
        self.is_escalated = sentiment_data['is_escalated']
        self.emotions = sentiment_data['emotions']
        self.escalation_reasons = sentiment_data.get('escalation_reasons', [])

        # --- STEP 6: RULE-BASED ESCALATION LOGIC ---
        
        # Rule 4: Emergency keywords detected
        emergency_keywords_detected = [kw for kw in self.priority_keywords["High"] if re.search(r'\b' + re.escape(kw) + r'\b', self.clean_text)]
        if emergency_keywords_detected:
            self.is_escalated = True
            self.escalation_reasons.append(f"Emergency keywords detected: {', '.join(emergency_keywords_detected)}")

        # Rule 5: Repetitive complaint check
        if getattr(self, 'is_repetitive', False):
            self.is_escalated = True
            self.escalation_reasons.append("Identified as a repetitive complaint by this user")

        # MARK as High Priority if escalated
        if self.is_escalated:
            priority = "High"
            
        description_final = self.english_text.capitalize()
        
        # Log escalation reasons for transparency
        if self.is_escalated:
            reason_str = " | ".join(self.escalation_reasons)
            description_final += f"\n\n[🛡️ AI ESCALATION SYSTEM]: MARKED AS HIGH PRIORITY. \nReason: {reason_str}"
            # Simulated: Notify Senior Authority
            print(f">>> AUTOMATIC NOTIFICATION: Alerting Senior Authority for Escalated Complaint. Reasons: {reason_str}")

        if self.translated:
            description_final += f"\n\n--- Original Text ---\n{self.original_text}"

        missing_fields = []
        if not title or len(title) < 5:
             missing_fields.append("title")
        if not location:
             missing_fields.append("location")
        if category == "Other" and not matched_keywords:
             missing_fields.append("specific category")

        # --- STEP 13: ETHICAL AI & BIAS DETECTION ---
        from ai_engine.ethics import EthicalAILayer, scrub_pii
        detected_bias = EthicalAILayer.detect_bias(self.clean_text, self.escalation_reasons)
        
        # Transparent Logging (Data Privacy compliant)
        pii_safe_text = scrub_pii(self.clean_text[:50]) # Only log first 50 chars for safety
        EthicalAILayer.transparent_log(
            "NEW", 
            "ALLOCATION", 
            f"Assigned to {self.worker_id}" if self.worker_id else "Unassigned",
            {"text": pii_safe_text, "category": category, "is_escalated": self.is_escalated}
        )

        return {
            "title": title,
            "category": category,
            "priority": priority,
            "description": description_final,
            "location": location,
            "keywords": list(set(matched_keywords)),
            "original_text": self.original_text if self.translated else None,
            "department": department,
            "missing_fields": missing_fields,
            "sentiment_score": self.sentiment_score,
            "sentiment_label": self.sentiment_label,
            "is_escalated": self.is_escalated,
            "emotions": self.emotions,
            "worker_id": self.worker_id,
            "escalation_reasons": self.escalation_reasons,
            "detected_bias": detected_bias
        }

def analyze_complaint_text(text, available_workers=None, is_repetitive=False, city=None):
    if not text:
        return {"title": "", "category": "Other", "priority": "Medium", "description": ""}
    
    analyzer = ComplaintAnalyzer(text, available_workers)
    analyzer.is_repetitive = is_repetitive
    return analyzer.process(city=city)
