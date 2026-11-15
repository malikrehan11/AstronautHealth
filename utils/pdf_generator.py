import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def generate_astronaut_pdf(profile, records):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter,
        rightMargin=0.5*inch, leftMargin=0.5*inch,
        topMargin=0.5*inch, bottomMargin=0.5*inch
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle(
        'CustomTitle', parent=styles['Heading1'], fontSize=22,
        textColor=colors.HexColor("#1e1e2f"), spaceAfter=5, alignment=1
    )
    subtitle_style = ParagraphStyle(
        'CustomSubtitle', parent=styles['Normal'], fontSize=10,
        textColor=colors.HexColor("#666666"), spaceAfter=20, alignment=1
    )
    section_header = ParagraphStyle(
        'SectionHeader', parent=styles['Heading2'], fontSize=14,
        textColor=colors.HexColor("#6c5ce7"), spaceBefore=15, spaceAfter=10
    )

    # HEADER
    elements.append(Paragraph("ASTROHEALTH", title_style))
    elements.append(Paragraph("CONFIDENTIAL MEDICAL DOSSIER - MISSION CONTROL", subtitle_style))
    
    # ASTRONAUT PROFILE
    elements.append(Paragraph("1. Astronaut Profile", section_header))
    
    # Safely extract profile data with defaults if missing
    name = profile.get('name', 'Unknown')
    mission = profile.get('mission', 'Unknown')
    age = profile.get('age', 'N/A')
    blood = profile.get('blood_group', 'N/A')
    weight = profile.get('weight_kg', 'N/A')
    height = profile.get('height_cm', 'N/A')
    
    profile_data = [
        ["Name:", name, "Mission:", mission],
        ["Age:", str(age), "Blood Group:", blood],
        ["Weight:", f"{weight} kg", "Height:", f"{height} cm"]
    ]
    
    profile_table = Table(profile_data, colWidths=[1*inch, 2.5*inch, 1*inch, 2.5*inch])
    profile_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#f0f2f5")),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor("#f0f2f5")),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor("#333333")),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#dddddd")),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(profile_table)
    elements.append(Spacer(1, 20))
    
    # HEALTH RECORDS
    elements.append(Paragraph("2. Longitudinal Health Telemetry", section_header))
    
    table_data = [["Date / Time", "HR", "BP", "SpO2", "Temp", "Sleep", "Rad", "Risk"]]
    
    for row in records:
        # Safe extraction
        time_str = str(row.get('recorded_at', 'N/A'))
        if '.' in time_str:
            time_str = time_str.split('.')[0] # Remove milliseconds
            
        hr = str(row.get('heart_rate', 'N/A'))
        sys = str(row.get('systolic_bp', 'N/A'))
        dia = str(row.get('diastolic_bp', 'N/A'))
        spo2 = str(row.get('spo2', 'N/A'))
        temp = str(row.get('body_temp', 'N/A'))
        sleep = str(row.get('sleep_hours', 'N/A'))
        rad = str(row.get('radiation_mSv', 0))
        risk = str(row.get('risk_status', 'N/A'))
        
        table_data.append([time_str, hr, f"{sys}/{dia}", spo2, temp, sleep, rad, risk])

    # Set column widths
    t = Table(table_data, colWidths=[1.3*inch, 0.5*inch, 0.7*inch, 0.5*inch, 0.6*inch, 0.6*inch, 0.5*inch, 0.8*inch])
    
    table_style = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e1e2f")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fb")]),
    ]

    # Color code the Risk column
    for i, row in enumerate(records, start=1):
        status = str(row.get('risk_status', '')).strip()
        if status == 'Critical':
            table_style.append(('TEXTCOLOR', (7, i), (7, i), colors.HexColor("#e74c3c")))
            table_style.append(('FONTNAME', (7, i), (7, i), 'Helvetica-Bold'))
        elif status == 'At Risk':
            table_style.append(('TEXTCOLOR', (7, i), (7, i), colors.HexColor("#f39c12")))
        elif status == 'Normal':
            table_style.append(('TEXTCOLOR', (7, i), (7, i), colors.HexColor("#2ecc71")))

    t.setStyle(TableStyle(table_style))
    elements.append(t)

    # FOOTER
    elements.append(Spacer(1, 30))
    footer_text = "Generated by AstroHealth. This document contains confidential medical information and is intended for Mission Control personnel only."
    elements.append(Paragraph(footer_text, ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=1)))

    # Build the PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer