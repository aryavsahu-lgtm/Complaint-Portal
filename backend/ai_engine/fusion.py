import json

class AiFusionModule:
    """
    Multi-Modal AI Fusion Module.
    Combines insights from NLP (Text) and Computer Vision (Images) to 
    provide accurate categorization, prioritization, and conflict detection.
    """

    @staticmethod
    def fuse_analysis(text_results, vision_results, authenticity_results=None):
        """
        Main fusion logic.
        
        Args:
            text_results (dict): Output from analyze_complaint_text.
            vision_results (list): Output from analyze_vision_evidence.
            authenticity_results (dict): Output from analyze_image_authenticity.
            
        Returns:
            dict: Fused results containing final_priority, final_category, 
                  has_conflict, and fusion_notes.
        """
        final_priority = text_results.get('priority', 'Medium')
        final_category = text_results.get('category', 'Other')
        final_assigned_to = text_results.get('department', 'General Administration')
        is_escalated = text_results.get('is_escalated', False)
        escalation_reasons = text_results.get('escalation_reasons', [])
        
        has_conflict = False
        fusion_notes = []
        is_urgent_hazard = False

        # 0. AUTHENTICITY CHECK (Step 7)
        if authenticity_results and authenticity_results.get('is_suspicious'):
            is_escalated = True
            final_priority = 'High' # Flag as high priority for manual review if fake
            fusion_notes.append("🚩 AUTHENTICITY ALERT: Image appears suspicious (Stock or missing metadata).")
            for reason in authenticity_results.get('reasons', []):
                fusion_notes.append(f"- {reason}")

        # 1. RISK MAXIMIZATION (Highest Risk Detection Takes Precedence)
        hazard_detected = False
        top_vision_detection = None
        
        if vision_results:
            # Sort by severity (Emergency > High > Medium > Low) and confidence
            severity_rank = {"Emergency": 3, "High": 2, "Medium": 1, "Low": 0}
            top_vision_detection = max(vision_results, key=lambda x: (severity_rank.get(x.get('severity', 'Low'), 0), x['confidence']))
            
            urgent_in_text = any(kw in text_results.get('keywords', []) for kw in ["urgent", "emergency", "fire", "danger"])
            
            # Map vision label to risk-based category if it's more severe than text prediction
            vision_label = top_vision_detection['label']
            # 1.1 SITUATION CLASSIFICATION ENGINE
            # Map top vision detection to specific categories and departments
            situation_map = {
                'Pothole': {'category': 'Road & Infrastructure', 'dept': 'Public Works Department (PWD)'},
                'Road Crack': {'category': 'Road & Infrastructure', 'dept': 'Public Works Department (PWD)'},
                'Garbage Cluster': {'category': 'Sanitation', 'dept': 'Municipal Solid Waste Management'},
                'Waterlogged Area': {'category': 'Drainage', 'dept': 'Drainage Maintenance Division'},
                'Fire/Smoke': {'category': 'Emergency', 'dept': 'Fire & Emergency Services'},
                'Accident: Vehicle': {'category': 'Emergency', 'dept': 'Home Department / Police'},
                'Stray Animal: Cow': {'category': 'Public Safety', 'dept': 'Animal Control / Police'},
                'Stray Animal: Dog': {'category': 'Public Safety', 'dept': 'Animal Control / Police'},
                'Stray Animal: Buffalo': {'category': 'Public Safety', 'dept': 'Animal Control / Police'},
                'Stray Animal: Goat': {'category': 'Public Safety', 'dept': 'Animal Control / Police'}
            }

            if vision_label in situation_map and top_vision_detection['confidence'] > 0.75:
                # Vision-based override for category and department if confidence is high
                final_category = situation_map[vision_label]['category']
                final_assigned_to = situation_map[vision_label]['dept']
                fusion_notes.append(f"🤖 SITUATION IDENTIFIED: Classifying as '{final_category}' based on visual evidence of {vision_label}.")

            # 2. SEVERITY ESTIMATION ENGINE (Multi-Modal Fusion)
            # Calculate a numeric severity score based on multiple signals
            
            # Signal A: Vision Confidence and Severity
            v_score = severity_rank.get(top_vision_detection.get('severity', 'Low'), 0) * 20
            v_confidence = top_vision_detection.get('confidence', 0) * 20
            
            # Signal B: Object Size and Count
            v_size = top_vision_detection.get('object_size', 0)
            if isinstance(v_size, str): v_size = 50 # Handle string labels like 'Large'
            v_count = top_vision_detection.get('object_count', 1) * 5
            
            # Signal C: Text-based Emergency Keywords
            emergency_keywords_score = 0
            if urgent_in_text: emergency_keywords_score = 40
            
            # Signal D: Emotion-based Sentiment (Fear/Anger/Urgency)
            emotions = text_results.get('emotions', {})
            emotion_score = (emotions.get('Fear', 0) + emotions.get('Anger', 0)) * 20
            if emotions.get('Fear', 0) > 0.6: 
                is_escalated = True
                fusion_notes.append("🧠 EMOTION FUSION: High distress detected. Escalating for immediate attention.")

            total_severity_score = v_score + v_confidence + min(v_size, 30) + min(v_count, 15) + emergency_keywords_score + min(emotion_score, 20)
            
            # Additional Context: Cow/Animal + "Dangerous" text
            if ('Animal' in vision_label or 'pothole' in vision_label.lower()) and any(w in text_results.get('clean_text', '') for w in ['danger', 'threat', 'scared', 'accident', 'hit']):
                total_severity_score += 25
                fusion_notes.append("🐕 HAZARD CROSS-VALIDATION: Confirmed high-risk incident via text/image fusion.")

            # STEP 5: False Alert Prevention (Refined Animal on Road Rule)
            animal_classes = ['Stray Animal: Cow', 'Stray Animal: Dog', 'Stray Animal: Buffalo', 'Stray Animal: Goat']
            
            # 1. Size & Count Verification
            is_valid_size = top_vision_detection.get('object_size', 0) > 10.0 # Ignore tiny objects (>10% frame)
            has_multiple = top_vision_detection.get('object_count', 1) > 1
            
            # 2. Text Semantic Cross-Validation
            raw_text = text_results.get('clean_text', '').lower()
            text_corroborated = any(kw in raw_text for kw in ['animal', 'stray', 'cow', 'dog', 'cattle', 'traffic', 'road', 'highway', 'street', 'danger'])
            
            # 3. Final Decision Logic
            is_valid_hazard = (
                vision_label in animal_classes and 
                top_vision_detection.get('confidence', 0) > 0.75 and 
                top_vision_detection.get('is_on_road') and
                is_valid_size and
                (text_corroborated or has_multiple) # Need either text proof or multiple sightings to confirm
            )

            if is_valid_hazard:
                final_priority = 'Emergency'
                is_escalated = True
                
                # Multi-Agency Routing
                final_assigned_to = "Municipal Animal Control & Traffic Police" if "Road" in top_vision_detection.get('context', '') else "Municipal Animal Control"
                
                fusion_notes.append(f"🚨 VERIFIED URGENT HAZARD: {vision_label} confirmed on transit surface via multi-modal verification.")
                if has_multiple: fusion_notes.append(f"🔍 CORROBORATION: Multiple ({top_vision_detection['object_count']}) detections boost confidence.")
                is_urgent_hazard = True
            else:
                is_urgent_hazard = False
                if vision_label in animal_classes and not is_valid_size:
                    fusion_notes.append("ℹ️ ALERT FILTERED: Detected animal is too far/small to represent an immediate road hazard.")
            
            # Map score to fused priority
            if total_severity_score >= 100:
                final_priority = 'Emergency'
                is_escalated = True
                fusion_notes.append(f"🚨 CRITICAL SEVERITY: Score {total_severity_score}/100. Emergency response required.")
            elif total_severity_score >= 70:
                final_priority = 'High'
                fusion_notes.append(f"⚠️ HIGH SEVERITY: Score {total_severity_score}/100. Prioritizing for urgent action.")
            elif total_severity_score >= 40:
                final_priority = 'Medium'
            else:
                final_priority = 'Low'

        # 3. CONFLICT DETECTION (Image vs Text)
        if vision_results and top_vision_detection:
            vision_keyword_map = {
                'Road Damage: Pothole': ['road', 'hole', 'pothole', 'street', 'highway', 'pavement'],
                'Road Damage: Crack': ['crack', 'damaged', 'pavement', 'concrete', 'road'],
                'Garbage Cluster': ['garbage', 'trash', 'waste', 'smell', 'dustbin', 'litter', 'sanitation'],
                'Fire/Smoke': ['fire', 'smoke', 'burn', 'spark', 'flame', 'safety'],
                'Waterlogged Area': ['water', 'flood', 'logged', 'rain', 'puddle', 'drainage', 'monsoon'],
                'Accident: Vehicle': ['accident', 'crash', 'collision', 'hit', 'vehicle', 'ambulance', 'help'],
                'Stray Animal: Cow': ['cow', 'animal', 'stray', 'cattle', 'livestock', 'road'],
                'Stray Animal: Dog': ['dog', 'animal', 'stray', 'bite', 'bark', 'road'],
                'Stray Animal: Buffalo': ['buffalo', 'animal', 'stray', 'cattle', 'road'],
                'Stray Animal: Goat': ['goat', 'animal', 'stray', 'road'],
                'Broken Street Light': ['light', 'dark', 'bulb', 'electricity', 'pole', 'signal']
            }
            
            v_label = top_vision_detection['label']
            clean_text = text_results.get('clean_text', '').lower()
            
            # If vision is high confidence but text doesn't mention related keywords
            if top_vision_detection['confidence'] > 0.8:
                related_keywords = vision_keyword_map.get(v_label, [])
                if not any(kw in clean_text for kw in related_keywords):
                    has_conflict = True
                    fusion_notes.append(f"⚠️ EVIDENCE CONFLICT: The image suggests a '{v_label}' but the description doesn't match. Admin clarification required.")
                    is_escalated = True # Escalate conflicts to admin review

        #Combine results
        is_animal_hazard = False
        animal_classes = ['Stray Animal: Cow', 'Stray Animal: Dog', 'Stray Animal: Buffalo', 'Stray Animal: Goat']
        if vision_results and top_vision_detection:
            if top_vision_detection['label'] in animal_classes and top_vision_detection.get('confidence', 0) > 0.75 and top_vision_detection.get('is_on_road'):
                is_animal_hazard = True

        return {
            "final_priority": final_priority,
            "final_category": final_category,
            "assigned_to": final_assigned_to,
            "is_escalated": is_escalated,
            "escalation_reasons": escalation_reasons + fusion_notes,
            "has_conflict": has_conflict,
            "is_animal_hazard": is_animal_hazard,
            "is_urgent_hazard": is_urgent_hazard,
            "fusion_metadata": {
                "top_detection": top_vision_detection['label'] if top_vision_detection else None,
                "vision_confidence": top_vision_detection['confidence'] if top_vision_detection else 0,
                "has_vision": bool(vision_results),
                "is_on_road": top_vision_detection.get('is_on_road') if top_vision_detection else False
            }
        }
