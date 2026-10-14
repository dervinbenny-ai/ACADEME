"""PDF layout for the same authorized, filtered dataset shown in the preview."""
import io
from pathlib import Path
from datetime import datetime, timezone
from xml.sax.saxutils import escape

def export_pdf(item,institution,keys,rows):
    import reportlab
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, LongTable, TableStyle, PageBreak
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from services.report_service import filtered_stats
    fonts=Path(reportlab.__file__).resolve().parent/'fonts'
    for name,file in [('AcademeReport','Vera.ttf'),('AcademeReportBold','VeraBd.ttf')]:
        if name not in pdfmetrics.getRegisteredFontNames(): pdfmetrics.registerFont(TTFont(name,str(fonts/file)))
    buffer=io.BytesIO();page=landscape(A4)
    document=SimpleDocTemplate(buffer,pagesize=page,rightMargin=32,leftMargin=32,topMargin=32,bottomMargin=40,title=item.title,author=institution)
    normal=ParagraphStyle('report',fontName='AcademeReport',fontSize=8,leading=12,textColor=colors.HexColor('#25304a'),wordWrap='CJK')
    heading=ParagraphStyle('title',parent=normal,fontName='AcademeReportBold',fontSize=19,leading=25,spaceAfter=9)
    header=ParagraphStyle('header',parent=normal,fontName='AcademeReportBold',textColor=colors.white)
    subtitle=ParagraphStyle('subtitle',parent=heading,fontSize=13,leading=18)
    def p(text,style=normal): return Paragraph(escape(str(text if text is not None else '')).replace('\n','<br/>'),style)
    fixed=[key for key in ('name','register_number') if key in keys]
    rest=[key for key in keys if key not in fixed]
    groups=[fixed+rest[i:i+4] for i in range(0,len(rest),4)] or [fixed]
    details=['Requirement: '+(item.requirement.title if item.requirement else 'Independent collection'),
        'Department: '+item.academic_class.department.name+' | Class: '+item.academic_class.name,
        'Teacher: '+item.teacher.name,'Generated: '+datetime.now(timezone.utc).strftime('%d %b %Y %H:%M UTC')]
    story=[];stats=filtered_stats(rows)
    for index,group in enumerate(groups):
        if index: story.append(PageBreak())
        story.extend([p(institution,heading),p(item.title,subtitle)])
        for line in details: story.append(p(line))
        story.extend([Spacer(1,10),p(' | '.join(f'{key.title()}: {value}' for key,value in stats.items())),p(f'Column group {index+1} of {len(groups)} - stored submission data'),Spacer(1,12)])
        table_rows=[[p(key.replace('_',' ').title(),header) for key in group]]
        table_rows.extend([[p(row.get(key,'')) for key in group] for row in rows])
        if not rows: table_rows.append([p('No matching records')]+[p('') for _ in group[1:]])
        table=LongTable(table_rows,colWidths=[document.width/max(1,len(group))]*len(group),repeatRows=1,splitByRow=1,splitInRow=1,hAlign='LEFT')
        table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#344575')),('VALIGN',(0,0),(-1,-1),'TOP'),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F3F6FC')]),('LINEBELOW',(0,0),(-1,-1),.4,colors.HexColor('#DEE4EF')),
            ('TOPPADDING',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),9),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8)]))
        story.append(table)
    def footer(canvas,doc):
        canvas.saveState();canvas.setStrokeColor(colors.HexColor('#DCE3EE'));canvas.line(32,29,page[0]-32,29)
        canvas.setFont('AcademeReport',8);canvas.setFillColor(colors.HexColor('#69758A'))
        canvas.drawString(32,17,'Academe | Academic collection report');canvas.drawRightString(page[0]-32,17,f'Page {doc.page}');canvas.restoreState()
    document.build(story,onFirstPage=footer,onLaterPages=footer);buffer.seek(0);return buffer
