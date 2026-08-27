"""
Chatbot Routes for Smart Complaint System
API endpoints for chatbot interactions
"""

from flask import Blueprint, request, jsonify, session, render_template, current_app
from werkzeug.utils import secure_filename
import os
from ai_engine.chatbot import SmartChatbot
from database import get_db
from utils import login_required
import uuid

chatbot_bp = Blueprint('chatbot', __name__, url_prefix='/chatbot')

@chatbot_bp.route('/')
def chatbot_page():
    """Render chatbot interface"""
    return render_template('chatbot.html')

@chatbot_bp.route('/message', methods=['POST'])
def send_message():
    """Process user message and return chatbot response"""
    user_message = ""
    attachment_filename = None

    # Handle JSON vs FormData
    if request.is_json:
        data = request.get_json()
        user_message = data.get('message', '').strip()
    else:
        user_message = request.form.get('message', '').strip()
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename:
                filename = secure_filename(file.filename)
                # Create upload folder if not exists
                upload_folder = os.path.join(current_app.root_path, 'uploads')
                os.makedirs(upload_folder, exist_ok=True)
                file_path = os.path.join(upload_folder, filename)
                file.save(file_path)
                attachment_filename = filename
    
    if not user_message and not attachment_filename:
        return jsonify({'error': 'Message cannot be empty'}), 400
    
    # Get or create session ID
    chat_session_id = session.get('chat_session_id')
    if not chat_session_id:
        chat_session_id = str(uuid.uuid4())
        session['chat_session_id'] = chat_session_id
    
    # Initialize chatbot with session language
    chatbot = SmartChatbot(
        user_id=session.get('user_id'),
        session_id=chat_session_id,
        lang=session.get('lang', 'en')
    )
    
    # Process message
    response = chatbot.process_message(user_message, attachment=attachment_filename)
    
    # Save chat history
    save_chat_message(
        session_id=chat_session_id,
        user_id=session.get('user_id'),
        message=user_message + (f" [Attached: {attachment_filename}]" if attachment_filename else ""),
        response=response['message'],
        intent=response.get('action'),
        emotion=response.get('emotion')
    )
    
    return jsonify(response)

@chatbot_bp.route('/submit-complaint', methods=['POST'])
@login_required
def submit_complaint_from_chat():
    """Submit complaint that was drafted in chat"""
    data = request.get_json()
    complaint_data = data.get('complaint_data')
    
    if not complaint_data:
        return jsonify({'error': 'Complaint data is required'}), 400
    
    chatbot = SmartChatbot(user_id=session.get('user_id'), lang=session.get('lang', 'en'))
    result = chatbot.submit_complaint(complaint_data)
    
    return jsonify(result)

@chatbot_bp.route('/complaint/<int:complaint_id>', methods=['GET'])
@login_required
def get_complaint_details(complaint_id):
    """Get details of a specific complaint"""
    chatbot = SmartChatbot(user_id=session.get('user_id'), lang=session.get('lang', 'en'))
    complaint = chatbot.get_complaint_details(complaint_id)
    
    if complaint:
        return jsonify({'success': True, 'complaint': complaint})
    else:
        return jsonify({'success': False, 'error': 'Complaint not found'}), 404

@chatbot_bp.route('/history', methods=['GET'])
def get_chat_history():
    """Get chat history for current session"""
    chat_session_id = session.get('chat_session_id')
    
    if not chat_session_id:
        return jsonify({'messages': []})
    
    db = get_db()
    messages = db.execute("""
        SELECT message, response, created_at, emotion
        FROM chat_history
        WHERE session_id = ?
        ORDER BY created_at ASC
        LIMIT 50
    """, (chat_session_id,)).fetchall()
    
    return jsonify({
        'messages': [dict(m) for m in messages]
    })

@chatbot_bp.route('/voice-status', methods=['POST'])
@login_required
def voice_status():
    """Handle voice-based status requests and return AI summary"""
    data = request.get_json()
    transcript = data.get('transcript', '').strip().lower()
    user_id = session.get('user_id')

    if not transcript:
        return jsonify({'error': 'Transcript is required'}), 400

    db = get_db()
    
    # Try to find specific complaint by ID if mentioned
    import re
    match = re.search(r'#?(\d+)', transcript)
    complaint = None
    
    if match:
        complaint_id = int(match.group(1))
        complaint = db.execute("""
            SELECT id, title, status, category, admin_response, updated_at 
            FROM complaints WHERE id = ? AND user_id = ?
        """, (complaint_id, user_id)).fetchone()
    
    # If no ID or not found, search by latest or keyword
    if not complaint:
        # Search by keywords (category or title)
        query = "%" + transcript + "%"
        complaint = db.execute("""
            SELECT id, title, status, category, admin_response, updated_at 
            FROM complaints 
            WHERE user_id = ? AND (title LIKE ? OR category LIKE ?)
            ORDER BY created_at DESC LIMIT 1
        """, (user_id, query, query)).fetchone()
        
    # If still no complaint, just get the latest one
    if not complaint:
        complaint = db.execute("""
            SELECT id, title, status, category, admin_response, updated_at 
            FROM complaints 
            WHERE user_id = ? 
            ORDER BY created_at DESC LIMIT 1
        """, (user_id,)).fetchone()

    if not complaint:
        return jsonify({'message': "I couldn't find any complaints in your account. You can file a new one using the button on your dashboard."})

    # Generate AI-like natural response
    status = complaint['status']
    title = complaint['title']
    cid = complaint['id']
    admin_note = complaint['admin_response']
    
    response_text = f"Regarding your complaint number {cid}, titled {title}. The current status is {status}. "
    
    if status == 'Pending':
        response_text += "It is currently being reviewed by our team. We will assign a technician soon."
    elif status == 'In Progress':
        response_text += "Our field officers are currently working on resolving this issue. You will receive an update shortly."
    elif status == 'Resolved':
        response_text += "This issue has been marked as resolved. Please check the portal for final details. Thank you for your patience."
    
    if admin_note:
        response_text += f" Our administrator noted: {admin_note}."

    # --- MULTI-LANGUAGE SUPPORT FOR STATUS & VOICE ---
    curr_lang = session.get('lang', 'en')
    if curr_lang and curr_lang != 'en':
        try:
            from deep_translator import GoogleTranslator
            response_text = GoogleTranslator(source='auto', target=curr_lang).translate(response_text)
        except Exception as e:
            print(f"[VoiceStatus] Translation Error for {curr_lang}: {e}")

    return jsonify({
        'success': True,
        'complaint_id': cid,
        'message': response_text,
        'status': status
    })

def save_chat_message(session_id, user_id, message, response, intent=None, emotion=None):
    """Save chat message to database"""
    db = get_db()
    
    try:
        db.execute("""
            INSERT INTO chat_history 
            (session_id, user_id, message, response, intent, emotion)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (session_id, user_id, message, response, intent, emotion))
        db.commit()
    except Exception as e:
        print(f"[Chatbot] Error saving chat history: {e}")
