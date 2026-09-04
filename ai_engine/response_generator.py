import random
from deep_translator import GoogleTranslator

class ResponseGenerator:
    """
    AI-based response generator that ensures polite, conversational, 
    and varied responses based on intent, emotion, and chatbot state.
    """
    
    def __init__(self, lang='en'):
        self.lang = lang
        self.translator = None
        if lang and lang != 'en':
            try:
                self.translator = GoogleTranslator(source='en', target=lang)
            except Exception as e:
                print(f"[ResponseGen] Could not initialize translator for {lang}: {e}")
                self.translator = None

    def _tr(self, text):
        """Translates text if language is set to a non-English language."""
        if self.translator and text:
            try:
                return self.translator.translate(text)
            except Exception as e:
                print(f"[ResponseGen] Translation Error: {e}")
                return text
        return text

    def translate_items(self, items):
        """Translates a list of strings."""
        if not self.translator or not items:
            return items
        return [self._tr(item) for item in items]

    TEMPLATES = {
        'greeting': [
            "Welcome to the Smart Coal Mining Governance Portal. I am your AI Safety & Compliance Assistant. How may I assist you with colliery operations today?",
            "Greetings from the Coal Governance Command Center. I am the AI Assistant dedicated to monitoring mine safety and compliance. Please state your requirement.",
            "Official AI Governance Assistant at your service. I can assist you in filing safety reports, compliance issues, or tracking existing incidents. How may I help you?"
        ],
        'thanks': [
            "You are welcome. It is our duty to ensure safety and compliance across all coalfields.",
            "I am glad to have been of assistance. Please let me know if any further operational information is required.",
            "Thank you. I remain at your service for any mining governance concerns."
        ],
        'goodbye': [
            "Thank you for using the Coal Governance Portal. This session is now concluded. Stay safe.",
            "The consultation is now complete. You may return to the portal at any time for further safety assistance.",
            "Reporting session closed. We remain dedicated to zero-harm operations. Goodbye."
        ],
        'help': [
            "I can assist you with the following: 1. Filing a new safety or compliance incident. 2. Tracking the progress of an existing report. Please select an option.",
            "To assist you better, you may choose to 'File a report' or 'Check status'. Which service do you require?",
            "As an official AI Assistant, I am programmed to guide you through DGMS compliance reporting and tracking procedures. Please specify your need."
        ],
        'fallback': [
            "I apologize, but I did not fully comprehend your statement. Could you please specify if you wish to file a safety incident or track a report status?",
            "For accurate processing, please use clear terms related to mining operations such as 'file report' or 'check status'.",
            "I am unable to interpret that request. Please state your requirement concisely in relation to mine safety and governance."
        ],
        'emergency_alert': [
            "🚨 **CRITICAL ALERT DETECTED** 🚨\n\nThis matter has been classified as **High Urgency/Emergency (DGMS Level 1)**. Mine safety authorities and rescue teams are being notified immediately. Please evacuate to the designated safe assembly zone.",
            "⚠️ **OFFICIAL EMERGENCY ESCALATION** ⚠️\n\nYour report indicates an immediate threat to mine safety. This has been escalated to the Colliery Manager and Rescue Station. If you are in immediate danger, trigger the emergency siren directly."
        ],
        'hazard_alerts': {
            'animal_on_road': "🚨 **SAFETY ALERT: UNAUTHORIZED ENTRY** 🚨\n\nAn unauthorized entry hazard has been identified in a restricted mining zone. This is a critical risk to heavy machinery operations. Security units have been dispatched.",
            'road_accident': "🚨 **CRITICAL INCIDENT ALERT: HEMM COLLISION** 🚨\n\nYour report concerning a Heavy Earth Moving Machinery (HEMM) collision has been prioritized for **Immediate Response**. Emergency medical services and safety officers are deployed.",
            'fire_hazard': "🚨 **LIFE-THREATENING HAZARD: MINE FIRE / SPONTANEOUS HEATING** 🚨\n\nDetection of fire, smoke, or elevated CO levels represents an immediate threat. The **Mine Rescue Station** has been notified. **EVACUATE THE DISTRICT IMMEDIATELY** following the safety protocols.",
            'gas_leak': "🚨 **SEVERE HAZARD ALERT: METHANE / NOXIOUS GAS BUILDUP** 🚨\n\nA hazardous gas level report constitutes a critical explosion and asphyxiation risk. **DGMS Officials** and ventilation officers are notified. **DE-ENERGIZE ALL EQUIPMENT**. Evacuate the face immediately.",
            'public_safety_risk': "🚨 **MINE SAFETY EMERGENCY** 🚨\n\nYour report of a significant safety hazard (e.g., strata failure, inundation) has been escalated to senior DGMS authorities. **High-Level Coordination** is underway. Please remain vigilant and await instructions."
        },
        'emotion_escalations': {
            'anger': (
                "🛡️ **OFFICIAL ESCALATION**\n\n"
                "We acknowledge the critical nature of your concern. "
                "Your incident report has been identified as a **Critical Compliance Breach**. "
                "It has been automatically escalated to the **Safety Officer and Agent** for immediate oversight."
            ),
            'repeated': (
                "🛡️ **PRIORITY RECOGNITION NOTICE**\n\n"
                "Our telemetry and records indicate this hazard was flagged previously. "
                "This case is now marked as **Highest Priority (CAPA Tier 1)**. "
                "The Colliery Manager has been assigned to ensure immediate rectification."
            ),
            'distress': (
                "🛡️ **URGENT RESCUE NOTICE**\n\n"
                "We recognize the distress and immediate danger in your report. "
                "Please be assured that your safety is our primary concern. "
                "This report has been flagged for **Immediate Intervention** by the Mine Rescue Team."
            )
        },
        'closing_official': {
            'registration_success': [
                "✅ **OFFICIAL REGISTRATION SUCCESSFUL.** Reference Number **#{id}** has been generated for your incident report. DGMS and internal safety units have been notified.",
                "Confirmed. Your report is officially recorded in the safety ledger as **#{id}**. You may track the live compliance status via the portal.",
                "Submission complete. CAPA Ticket **#{id}** is now active. The concerned safety officer is mandated to initiate corrective action immediately."
            ],
            'issue_resolved': [
                "📢 **RESOLUTION CONFIRMATION.** We are pleased to inform you that incident **#{id}** has been marked as **RESOLVED (Compliance Met)**. Field teams have completed the necessary intervention.",
                "Case **#{id}** Closure Notice: The reported hazard has been successfully mitigated by our safety technicians. Zero-harm operations resumed."
            ],
            'feedback_request': [
                "Your experience is vital for safety compliance. Could you please provide a brief rating of the AI Assistant's performance?",
                "How satisfied are you with the incident reporting process? Your feedback helps us build a safer mining environment.",
                "We value your input. Please rate the effectiveness of this interaction to help us enhance mine governance."
            ],
            'appreciation': [
                "We appreciate your proactive role as a vigilant mining personnel. Together, we ensure zero-harm operations.",
                "Thank you for bringing this safety matter to our official attention. Your contribution is essential for DGMS compliance.",
                "Workplace safety is the cornerstone of our operations. We thank you for your commitment to the welfare of all miners."
            ]
        }
    }

    STATE_INSTRUCTIONS = {
        'collecting_category': [
            "Please specify the operational department or category relevant to your incident report.",
            "To ensure proper routing to the concerned safety officer, please select the appropriate category.",
            "Classification is required for compliance routing. Please select the mining operations area."
        ],
        'collecting_description': [
            "Please provide a detailed formal description of the hazard or compliance issue.",
            "Detailed technical information is necessary for the department to take corrective action.",
            "Kindly provide a concise summary of the operational problem, including any relevant sensor or machinery context."
        ],
        'collecting_city': [
            "Please select the Mining Zone or Coalfield where this issue occurred.",
            "For regional routing, it is necessary to identify your Coalfield: Jharia, Raniganj, Korba, Singrauli, or Talcher.",
            "Zone selection is mandatory. Please choose your operational coalfield."
        ],
        'collecting_location': [
            "To ensure rapid deployment of safety teams, may I request your permission to access your **GPS Coordinates**? Precise telemetry data allows our officers to reach the face faster.",
            "Please provide the exact pit/seam address or authorize GPS capture. Accurate geographic data is essential for emergency response.",
            "Identify the precise underground or opencast location. Authorizing location services expedites hazard mitigation."
        ],
        'collecting_media': [
            "Would you like to provide photographic evidence or CCTV captures to support your report? You may skip this step if not applicable.",
            "Providing media attachments can significantly aid the CAPA process. Would you like to upload a file?",
            "Supporting documentation (e.g. DGMS forms, photos) may be attached now. Type 'skip' to proceed without attachment."
        ],
        'confirming': [
            "Please review the summary above and confirm its accuracy before official DGMS ledger submission.",
            "Verify the provided details carefully. Confirm with 'Yes' to register this incident in our compliance records.",
            "Is the information presented correct? Please signify your confirmation or request edits."
        ],
        'tracking_id': [
            "Please provide the official Reference Number or Case ID you wish to track.",
            "Identify the report by entering its unique tracking number (e.g., #101 or INC-...).",
            "To retrieve the progress report and CAPA status, please input the complaint identification number."
        ],
        'location_services': {
            'request_permission': "To ensure rapid deployment of safety teams, may I request your permission to access your **GPS Coordinates**? This allows for automated spatial logging.",
            'capture_success': "📍 **Location Coordinates Confirmed.** Your precise geographic data has been integrated into the compliance file.",
            'benefit_explanation': "Providing exact location data enables our safety officers to deploy targeted corrective measures faster.",
            'denied_fallback': "It appears location access was restricted. You may manually specify the mine section, pit number, or landmark.",
            'manual_entry_prompt': "Please provide a detailed manual location (e.g. Seam 3, Gallery 4) to proceed with the registration."
        }
    }

    def generate(self, intent, state, emotion=None, context=None):
        """
        Generates a formal and contextually relevant government-toned response.
        """
        # 1. Handle Specialized Hazards First
        if context and context.get('hazard_type'):
            hazard = context['hazard_type']
            if hazard in self.TEMPLATES['hazard_alerts']:
                return self._tr(self.TEMPLATES['hazard_alerts'][hazard])

        # 2. Handle General Emergencies
        if intent == 'emergency' or (emotion and emotion == 'critical'):
            return self._tr(self._get_random('emergency_alert'))

        # 2. State-specific instructions (Flow-driven)
        if state and state in self.STATE_INSTRUCTIONS and state != 'idle':
            response = self._get_random_state(state)
            
            # Add supportive/formal prefix if user is distressed
            if emotion in ['high_urgency', 'anger']:
                prefix = "We acknowledge the seriousness of this matter. " if emotion == 'anger' else "This request is being treated with priority. "
                response = prefix + response
                
            return self._tr(response)

        # 3. Intent-driven responses (Idle-driven)
        if intent in self.TEMPLATES:
            return self._tr(self._get_random(intent))
            
        return self._tr(self._get_random('fallback'))

    def _get_random(self, category):
        return random.choice(self.TEMPLATES.get(category, self.TEMPLATES['fallback']))

    def _get_random_state(self, state):
        return random.choice(self.STATE_INSTRUCTIONS.get(state, ["How may I assist you with your municipal requirements?"]))

    def get_confirmation_summary(self, draft):
        """Generates the formal summary for confirmation."""
        summary = f"""📋 **OFFICIAL REPORT SUMMARY REVIEW**
        
**🏢 COALFIELD ZONE:** {draft.get('city', 'Pending Selection')}
**📍 LOCATION:** {draft.get('location', 'Auto-Capturing...')}
**📝 DESCRIPTION:** {draft.get('description', draft.get('title', 'Not specified'))}
**📂 DEPARTMENT:** {draft.get('category', 'Safety & Operations')}
**⚡ PRIORITY LEVEL:** {draft.get('priority', 'Normal')}

Does this summary accurately represent the incident you wish to file?"""
        return self._tr(summary)

    def get_success_message(self, complaint_id):
        """Formal success messages after official submission."""
        template = random.choice(self.TEMPLATES['closing_official']['registration_success'])
        return self._tr(template.format(id=complaint_id))

    def get_resolution_message(self, complaint_id):
        """Formal resolution confirmation message."""
        template = random.choice(self.TEMPLATES['closing_official']['issue_resolved'])
        return self._tr(template.format(id=complaint_id))

    def get_feedback_prompt(self):
        """Official request for citizen feedback."""
        return self._tr(random.choice(self.TEMPLATES['closing_official']['feedback_request']))

    def get_appreciation_message(self):
        """Formal citizen appreciation message."""
        return self._tr(random.choice(self.TEMPLATES['closing_official']['appreciation']))

    def get_ai_vision_feedback(self, fused_results):
        """
        Explains AI vision decisions transparently to the user.
        """
        metadata = fused_results.get('fusion_metadata', {})
        label = metadata.get('top_detection')
        is_on_road = metadata.get('is_on_road', False)
        
        if not metadata.get('has_vision'):
            return self._tr("Note: No specific technical issues were identified in the attached media. Please ensure the image is clear or provide additional details textually.")

        # 1. Animal on Road Case
        animal_classes = ['Stray Animal: Cow', 'Stray Animal: Dog', 'Stray Animal: Buffalo', 'Stray Animal: Goat']
        if label in animal_classes and is_on_road:
            return self._tr(
                f"🧠 **AI VISION ANALYSIS:** A {label} has been detected directly on a transit surface. "
                "For public safety, this has been marked as **HIGH PRIORITY**. "
                "The Municipal Animal Control and Traffic Police units have been notified for immediate response."
            )
            
        # 2. Infrastructure Case
        if label and ('Pothole' in label or 'Road Crack' in label):
            return self._tr(
                f"🧠 **AI VISION ANALYSIS:** Visual evidence confirms {label}. "
                "This grievance has been categorized under **Road & Infrastructure**. "
                "The maintenance department has been assigned to assess the structural damage."
            )
            
        # 3. Sanitation Case
        if label and 'Garbage' in label:
            return self._tr(
                f"🧠 **AI VISION ANALYSIS:** An accumulation of waste ({label}) has been identified. "
                "The Sanitation Department has been notified to schedule a prompt clearance of this area."
            )

        # 4. Fallback for detected but not specified in requirements
        if label:
            return self._tr(f"🧠 **AI VISION ANALYSIS:** Visual evidence of '{label}' has been automatically documented to support your grievance.")

        return self._tr("The provided media has been analyzed and attached to your case file for administrative review.")

    def get_escalation_message(self, reason):
        """Formal notification regarding automated escalation."""
        return self._tr(
            f"🛡️ **OFFICIAL ESCALATION NOTICE**: This case has been automatically escalated to senior authorities. \n"
            f"**Reason:** {reason}"
        )

    def get_emotion_escalation_feedback(self, analysis):
        """
        Provides empathetic and formal feedback based on emotional state or repetition.
        """
        emotions = analysis.get('emotions', {})
        is_repetitive = analysis.get('is_repetitive', False)
        
        # 1. Handle Repetitive Complaints first
        if is_repetitive:
            return self._tr(self.TEMPLATES['emotion_escalations']['repeated'])
            
        # 2. Handle High Anger
        if emotions.get('Anger', 0) > 0.7:
            return self._tr(self.TEMPLATES['emotion_escalations']['anger'])
            
        # 3. Handle High Distress/Fear
        if emotions.get('Distress', 0) > 0.7 or emotions.get('Fear', 0) > 0.7:
            return self._tr(self.TEMPLATES['emotion_escalations']['distress'])
            
        return None

    def get_voice_feedback(self):
        """Formal acknowledgement for official voice note submission."""
        return self._tr(
            "🎙️ **AI VOICE ANALYSIS INITIATED**\n\n"
            "Your voice recording has been received. Our AI is currently transcribing the audio to extract "
            "official grievance details. The transcript will be integrated into your case file for administrative review."
        )
