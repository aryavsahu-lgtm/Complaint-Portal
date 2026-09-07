"""
OCR & Document Digitizer Module:
- /ocr-scanner (renders ocr_scanner.html)
"""

from flask import render_template, request
from werkzeug.utils import secure_filename
from ai_engine.ocr_digitizer import DocumentDigitizerEngine
from . import governance_bp

@governance_bp.route('/ocr-scanner', methods=['GET', 'POST'])
def ocr_scanner():
    result = None
    if request.method == 'POST':
        raw_text = request.form.get('raw_text', '')
        doc_file = request.files.get('document_file')
        doc_name = "Manual Input Text"

        if doc_file and doc_file.filename:
            doc_name = secure_filename(doc_file.filename)
            try:
                content_bytes = doc_file.read()
                raw_text = content_bytes.decode('utf-8', errors='ignore')
            except Exception:
                raw_text = f"Sample DGMS notice extracted from {doc_name}. Contravention of Regulation 168 of CMR 2017 regarding inflammable gas monitoring. Action required within 15 days."

        if not raw_text.strip():
            raw_text = """DIRECTORATE GENERAL OF MINES SAFETY (DGMS)
            Eastern Circle, Inspection Notice No. DGMS/EC/2026/088
            Under Section 22 of Mines Act 1952 and Regulation 142 of Coal Mines Regulations (CMR 2017).
            Subject: Immediate rectification of Spontaneous Heating in Panel 4 and Dust suppression.
            Environmental Clearance Capacity: 70.0 MTPA. Action required immediately within 7 days.
            Periodic Medical Examination Form O screening report due by 2026-09-30."""

        result = DocumentDigitizerEngine.digitize_text_content(raw_text, doc_name)

    return render_template('ocr_scanner.html', result=result)
