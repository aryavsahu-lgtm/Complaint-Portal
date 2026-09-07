import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from datetime import datetime

def generate_compliance_report(data, output_path):
    """
    Generates a PDF compliance report.
    `data` expects:
    {
        'report_date': str,
        'violations': list of dicts,
        'escalations': list of dicts
    }
    """
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    # Title
    title_style = styles['Heading1']
    title_style.alignment = 1
    elements.append(Paragraph("MineGuard Compliance & Escalation Report", title_style))
    elements.append(Spacer(1, 12))

    # Date
    elements.append(Paragraph(f"<b>Report Date:</b> {data.get('report_date', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}", styles['Normal']))
    elements.append(Spacer(1, 12))

    # Escalations Section
    elements.append(Paragraph("Auto-Escalated Complaints (Last 7 Days)", styles['Heading2']))
    escalations = data.get('escalations', [])
    if escalations:
        esc_data = [["ID", "Title", "Date Escalated", "Status"]]
        for esc in escalations:
            esc_data.append([str(esc['id']), esc['title'], esc['updated_at'], esc['status']])
        
        esc_table = Table(esc_data, colWidths=[50, 250, 100, 100])
        esc_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(esc_table)
    else:
        elements.append(Paragraph("No recent escalations.", styles['Normal']))
    
    elements.append(Spacer(1, 24))

    # Active Violations Section
    elements.append(Paragraph("High Risk Active Violations", styles['Heading2']))
    violations = data.get('violations', [])
    if violations:
        vio_data = [["Colliery", "Location", "Risk Level", "Inspector"]]
        for vio in violations:
            vio_data.append([vio['mine_name'], vio['location_pit_seam'], vio['risk_level'], vio['inspector_name']])
            
        vio_table = Table(vio_data, colWidths=[120, 150, 80, 150])
        vio_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkred),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightpink),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(vio_table)
    else:
        elements.append(Paragraph("No active high-risk violations.", styles['Normal']))

    doc.build(elements)
    return output_path
