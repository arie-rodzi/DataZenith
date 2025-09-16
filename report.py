from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet

def export_policy_pdf(path, title, bullets_text):
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(path, pagesize=A4)
    story = [Paragraph(title, styles['Title']), Spacer(1, 12)]
    for line in bullets_text.split("\n"):
        story.append(Paragraph(line, styles['Normal']))
    doc.build(story)
    return path
