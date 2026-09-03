import re
import datetime

class EthicalAILayer:
    """
    Step 13: Ethical AI & Bias Detection
    Ensures AI decisions are fair, transparent, and auditable.
    """
    
    # List of sensitive terms that should NOT influence escalation negatively (Bias Detection)
    # The system should flag if these words are the ONLY reason for escalation.
    PROTECTED_ATTRIBUTES = [
        "religion", "caste", "gender", "race", "nationality", "minority"
    ]

    @staticmethod
    def detect_bias(text, escalation_reasons):
        """
        Checks if the escalation was potentially triggered by sensitive attributes rather than behavior.
        """
        detected_bias = []
        for attr in EthicalAILayer.PROTECTED_ATTRIBUTES:
            if re.search(r'\b' + re.escape(attr) + r'\b', text.lower()):
                # If these are in the text, we log that extra auditing is needed
                detected_bias.append(attr)
        
        return detected_bias

    @staticmethod
    def transparent_log(complaint_id, decision_type, reason, inputs):
        """
        Logs every AI decision for auditability.
        """
        log_entry = f"[{datetime.datetime.now()}] ID: {complaint_id} | TYPE: {decision_type} | REASON: {reason} | INPUTS: {inputs}\n"
        try:
            with open("ai_decisions.log", "a") as f:
                f.write(log_entry)
        except Exception as e:
            print(f"Logging Error: {e}")

def scrub_pii(text):
    """
    Data Privacy: Scrubber for PII (Personally Identifiable Information).
    Masks Phone Numbers and Emails in logs.
    """
    # Simple regex for email and phone
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    phone_pattern = r'\b(\+?\d{1,3}[- ]?)?\d{10}\b'
    
    scrubbed = re.sub(email_pattern, "[EMAIL MASKED]", text)
    scrubbed = re.sub(phone_pattern, "[PHONE MASKED]", scrubbed)
    return scrubbed
