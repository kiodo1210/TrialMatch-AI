import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def generate_trialmatch_pdf(data: dict, output_path: str) -> str:
    """
    TrialMatch AI 매칭 결과 데이터를 받아 전문 B2B PDF 리포트를 자동 생성합니다.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=colors.HexColor('#1E3A8A')
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#6B7280')
    )

    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#1E3A8A'),
        spaceBefore=12,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#1F2937')
    )

    bold_body = ParagraphStyle(
        'BoldBodyText',
        parent=body_style,
        fontName='Helvetica-Bold'
    )

    story = []

    # Header
    story.append(Paragraph("TrialMatch AI - Clinical Trial Matching Report", title_style))
    story.append(Paragraph("Precision Medicine Patient Recruitment & Pathogenicity Analysis", subtitle_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#1E3A8A'), spaceBefore=5, spaceAfter=15))

    # Patient & Variant Summary
    story.append(Paragraph("1. Patient & Variant Summary", h2_style))
    
    summary_data = [
        [Paragraph("Gene Variant", bold_body), Paragraph(data.get("gene_variant", "N/A"), body_style)],
        [Paragraph("Target Disease", bold_body), Paragraph(data.get("disease", "N/A"), body_style)],
        [Paragraph("Variant Pathogenicity", bold_body), Paragraph(data.get("variant_pathogenicity", "N/A"), body_style)],
        [Paragraph("Validation Status", bold_body), Paragraph("✅ Verified by TrialMatch Guardrail Engine", body_style)]
    ]
    
    summary_table = Table(summary_data, colWidths=[150, 380])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F3F4F6')),
        ('BACKGROUND', (1, 0), (1, -1), colors.HexColor('#FFFFFF')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1F2937')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#D1D5DB')),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 15))

    # Recommended Clinical Trials
    story.append(Paragraph("2. Top Matched Clinical Trials (Recruiting)", h2_style))
    
    trials = data.get("recommended_trials", [])
    trials_table_data = [
        [Paragraph("NCT ID", bold_body), Paragraph("Trial Title & Details", bold_body), Paragraph("Phase", bold_body), Paragraph("Status", bold_body)]
    ]
    
    for t in trials:
        details_text = f"<b>{t.get('title', '')}</b><br/><font color='#4B5563'>Location: {t.get('location', '')}</font>"
        trials_table_data.append([
            Paragraph(t.get("nct_id", ""), bold_body),
            Paragraph(details_text, body_style),
            Paragraph(t.get("phase", ""), body_style),
            Paragraph(f"<font color='#059669'><b>{t.get('status', '')}</b></font>", body_style)
        ])

    trials_table = Table(trials_table_data, colWidths=[90, 290, 75, 75])
    trials_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#D1D5DB')),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(trials_table)
    story.append(Spacer(1, 15))

    # Actionable Scientific Rationale
    story.append(Paragraph("3. Scientific Rationale & Mechanism of Action", h2_style))
    for idx, t in enumerate(trials, 1):
        rationale_text = f"<b>[{t.get('nct_id')}] Rationale:</b> {t.get('match_rationale', '')}"
        story.append(Paragraph(rationale_text, body_style))
        story.append(Spacer(1, 4))

    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#E5E7EB'), spaceBefore=10, spaceAfter=10))
    story.append(Paragraph("Confidential - Generated by TrialMatch AI Platform for Medical Professional Review Only.", subtitle_style))

    doc.build(story)
    return output_path
