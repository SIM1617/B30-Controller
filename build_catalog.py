#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate B30 Catalog PDF — uses Tahoma for Persian + ReportLab."""
import pathlib, textwrap
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white, Color
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether, PageBreak, Image
from reportlab.lib.fonts import tt2ps
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.graphics.charts.barcharts import VerticalBarChart
import os

OUT = pathlib.Path("D:/Projects/B30_Catalog.pdf")
FONT_DIR = pathlib.Path("C:/Windows/Fonts")

# Register Persian-capable font — Tahoma covers Arabic/Persian glyphs
pdfmetrics.registerFont(TTFont("Tahoma", str(FONT_DIR / "tahoma.ttf")))
pdfmetrics.registerFont(TTFont("Tahoma-Bold", str(FONT_DIR / "tahomabd.ttf")))
# Fallback Arial for Latin
pdfmetrics.registerFont(TTFont("Arial", str(FONT_DIR / "arial.ttf")))
pdfmetrics.registerFont(TTFont("Arial-Bold", str(FONT_DIR / "arialbd.ttf")))

# Colors
NAVY = HexColor("#0F172A")
NAVY2 = HexColor("#1E293B")
ACCENT = HexColor("#F59E0B")  # amber for highlights
ACCENT2 = HexColor("#2563EB")
GREEN = HexColor("#10B981")
RED = HexColor("#EF4444")
YELLOW = HexColor("#FCD34D")
GRAY_BG = HexColor("#F1F5F9")
GRAY_LINE = HexColor("#E2E8F0")
MUTED = HexColor("#64748B")

W, H = A4
MARGIN = 14*mm

def header_footer(canvas, doc):
    canvas.saveState()
    # Top bar
    canvas.setFillColor(NAVY)
    canvas.rect(0, H-18*mm, W, 18*mm, fill=1, stroke=0)
    canvas.setFillColor(white)
    canvas.setFont("Tahoma-Bold", 11)
    canvas.drawCentredString(W/2, H-10*mm, "B30  |  دستگاه فرماندهی چراغ راهنمایی")
    canvas.setFont("Tahoma", 7)
    canvas.setFillColor(HexColor("#94A3B8"))
    canvas.drawCentredString(W/2, H-14*mm, "B30 Traffic Controller  •  Delta PLC  •  TCP/IP Online Control")
    # Bottom bar
    canvas.setFillColor(GRAY_BG)
    canvas.rect(0, 0, W, 10*mm, fill=1, stroke=0)
    canvas.setFillColor(MUTED)
    canvas.setFont("Arial", 6.5)
    canvas.drawCentredString(W/2, 4*mm, "B30 Controller  |  SIM1617.github.io/B30-Controller  |  2026")
    canvas.setFont("Tahoma", 6.5)
    canvas.setFillColor(ACCENT)
    try:
        pg = canvas.getPageNumber()
        canvas.drawRightString(W-12*mm, 4*mm, f"{pg}")
    except: pass
    canvas.restoreState()

# Styles
sTitle = ParagraphStyle("title", fontName="Tahoma-Bold", fontSize=22, leading=28, textColor=NAVY, alignment=TA_CENTER, spaceAfter=2*mm)
sSub = ParagraphStyle("sub", fontName="Tahoma", fontSize=9, leading=13, textColor=MUTED, alignment=TA_CENTER, spaceAfter=4*mm)
sH1 = ParagraphStyle("h1", fontName="Tahoma-Bold", fontSize=13, leading=17, textColor=NAVY, alignment=TA_RIGHT, spaceBefore=6*mm, spaceAfter=2*mm, borderPadding=(0,0,2*mm,0))
sH2 = ParagraphStyle("h2", fontName="Tahoma-Bold", fontSize=10, leading=14, textColor=NAVY2, alignment=TA_RIGHT, spaceBefore=3*mm, spaceAfter=1.5*mm)
sBody = ParagraphStyle("body", fontName="Tahoma", fontSize=8.5, leading=13, textColor=HexColor("#334155"), alignment=TA_JUSTIFY, spaceAfter=1.5*mm, rightIndent=2*mm)
sBullet = ParagraphStyle("bullet", fontName="Tahoma", fontSize=8.5, leading=13, textColor=HexColor("#334155"), alignment=TA_RIGHT, leftIndent=6*mm, rightIndent=2*mm, spaceAfter=1.2*mm, bulletIndent=3*mm)
sSmall = ParagraphStyle("small", fontName="Tahoma", fontSize=7.5, leading=11, textColor=MUTED, alignment=TA_RIGHT)
sCell = ParagraphStyle("cell", fontName="Tahoma", fontSize=7.5, leading=10, textColor=HexColor("#1E293B"), alignment=TA_CENTER)
sCellHead = ParagraphStyle("cellh", fontName="Tahoma-Bold", fontSize=7.5, leading=10, textColor=white, alignment=TA_CENTER)
sCaption = ParagraphStyle("caption", fontName="Tahoma", fontSize=6.5, leading=9, textColor=MUTED, alignment=TA_CENTER)

def bullet(text):
    return Paragraph(f'<font color="#F59E0B">●</font>  {text}', sBullet)

def hr():
    return HRFlowable(width="100%", thickness=0.6, color=GRAY_LINE, spaceAfter=2*mm, spaceBefore=2*mm)

def badge(text, bg=ACCENT, fg=NAVY):
    t = Table([[Paragraph(f'<font color="{fg.hexval() if hasattr(fg,"hexval") else fg}"><b>{text}</b></font>', ParagraphStyle("b", fontName="Tahoma-Bold", fontSize=7, leading=9, textColor=fg, alignment=TA_CENTER))]], colWidths=[28*mm])
    t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),bg),("ROUNDEDCORNERS",[3,3,3,3]),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),4),("RIGHTPADDING",(0,0),(-1,-1),4),("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3)]))
    return t

story = []

# ── COVER ──
story.append(Spacer(1, 10*mm))
# Big B30 mark
cover_title = Paragraph('<font color="#F59E0B">B30</font> <font color="#0F172A">CONTROLLER</font>', ParagraphStyle("ct", fontName="Arial-Bold", fontSize=36, leading=38, alignment=TA_CENTER))
story.append(cover_title)
story.append(Spacer(1, 2*mm))
story.append(Paragraph("دستگاه فرماندهی چراغ راهنمایی — نسل جدید", ParagraphStyle("cs", fontName="Tahoma-Bold", fontSize=12, leading=16, textColor=NAVY2, alignment=TA_CENTER)))
story.append(Spacer(1, 2*mm))
story.append(HRFlowable(width="30%", thickness=1.2, color=ACCENT, spaceAfter=3*mm, spaceBefore=1*mm, hAlign="CENTER"))
story.append(Paragraph("کنترل ۸ فاز • ۸ پارت (۲۴ سیگنال) • مدهای هوشمند و زمانبندی • TCP/IP آنلاین • PLC دلتا", sSub))
story.append(Spacer(1, 4*mm))

# Cover badges
badges = Table([
    [badge("۸ فاز"), badge("۸ پارت / ۲۴ خروجی"), badge("PLC Delta")],
    [badge("TCP/IP Online", bg=NAVY2, fg=white), badge("۱۶ لوپ / ۴ دتکتور", bg=NAVY2, fg=white), badge("شمسی + میلادی", bg=NAVY2, fg=white)],
], colWidths=[32*mm, 38*mm, 32*mm], spaceBefore=2*mm, spaceAfter=2*mm)
badges.setStyle(TableStyle([("ALIGN",(0,0),(-1,-1),"CENTER"),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),3),("RIGHTPADDING",(0,0),(-1,-1),3),("TOPPADDING",(0,0),(-1,-1),2),("BOTTOMPADDING",(0,0),(-1,-1),2)]))
story.append(badges)
story.append(Spacer(1, 6*mm))

# Cover feature strip
strip_data = [
    [Paragraph('<b>۲۴</b><br/><font color="#64748B" size=6>سیگنال خروجی</font>', sCaption),
     Paragraph('<b>۲۷</b><br/><font color="#64748B" size=6>زمانبندی هفتگی</font>', sCaption),
     Paragraph('<b>۱۶</b><br/><font color="#64748B" size=6>لوپ هوشمند</font>', sCaption),
     Paragraph('<b>Online</b><br/><font color="#64748B" size=6>کنترل TCP/IP</font>', sCaption)],
]
strip = Table(strip_data, colWidths=[W/4 - 8*mm]*4)
strip.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1), GRAY_BG),("BOX",(0,0),(-1,-1),0.5,GRAY_LINE),("INNERGRID",(0,0),(-1,-1),0.3,GRAY_LINE),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4)]))
story.append(strip)
story.append(Spacer(1, 8*mm))
story.append(Paragraph("کاتالوگ فنی — مشخصات نرم‌افزاری و سخت‌افزاری", ParagraphStyle("cf", fontName="Tahoma", fontSize=8, leading=11, textColor=MUTED, alignment=TA_CENTER)))
story.append(Spacer(1, 2*mm))
story.append(Paragraph("Version 2.0  •  2026  •  B30 Controller", ParagraphStyle("cv", fontName="Arial", fontSize=7, leading=9, textColor=MUTED, alignment=TA_CENTER)))

# ── PAGE 2 — نرم افزار ──
story.append(PageBreak())
story.append(Paragraph("قابلیت‌های نرم‌افزاری", sH1))
story.append(hr())

story.append(Paragraph("کنترل فاز و پارت", sH2))
story.append(bullet("کنترل تا <b>۸ فاز متوالی</b> با زمانبندی مستقل برای هر فاز (سبز، زرد، قرمز، All-Red، حداقل و حداکثر حفاظتی)"))
story.append(bullet("دارای <b>۸ پارت خروجی</b> معادل <b>۲۴ سیگنال مجزای سبز / زرد / قرمز</b> — هر پارت قابل تنظیم در هر فاز به عنوان خودرو، عابر، چشمک زرد یا چشمک قرمز"))
story.append(bullet("قابلیت تنظیم فازها در دو حالت <b>کم‌باری و اوج بار</b> (دو جدول متفاوت فازبندی) و انتخاب جدول فعال در هر زمان"))

story.append(Paragraph("مدهای کاری", sH2))
modes = [
    ["مد", "توضیح"],
    ["چشمک‌زن دائم", "چشمک زرد / قرمز دائم برای هر پارت — قابل تنظیم برای هر خروجی"],
    ["زمانبندی (Fixed)", "اجرای جدول زمانبندی ثابت با ۲۷ برنامه هفتگی"],
    ["هوشمند (Actuated)", "فیکس یا هوشمند + کنترل حداقل/حداکثر زمان حفاظتی با دتکتور"],
    ["کنترل پلیس", "کنترل دستی توسط پلیس با اعمال فوری"],
]
t = Table([[Paragraph(c, sCellHead if i==0 else sCell) for c in row] for i,row in enumerate(modes) and modes or []], colWidths=[28*mm, W-28*mm-2*MARGIN])
# Build correctly
rows = []
for idx,row in enumerate(modes):
    style = sCellHead if idx==0 else sCell
    rows.append([Paragraph(f"<b>{c}</b>" if idx==0 else c, style) for c in row])
t2 = Table(rows, colWidths=[30*mm, W - 30*mm - 2*MARGIN - 6*mm])
t2.setStyle(TableStyle([
    ("BACKGROUND",(0,0),(-1,0), NAVY), ("TEXTCOLOR",(0,0),(-1,0), white),
    ("ROWBACKGROUNDS",(0,1),(-1,-1), [white, GRAY_BG]),
    ("GRID",(0,0),(-1,-1),0.4, GRAY_LINE), ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3),
    ("LEFTPADDING",(0,0),(-1,-1),4),("RIGHTPADDING",(0,0),(-1,-1),4),
]))
story.append(t2)

story.append(Paragraph("زمانبندی و تقویم", sH2))
story.append(bullet("<b>۲۷ زمانبندی مختلف</b> برای روزهای مختلف هفته — هر روز هفته برنامه مجزا"))
story.append(bullet("تاریخ <b>شمسی و میلادی</b> همزمان + تنظیم سریع ساعت، تاریخ و IP شبکه از نرم‌افزار"))
story.append(bullet("تنظیم راحت رنگ سیگنال چشمک‌زن (زرد / قرمز / خاموش دائم) برای هر پارت"))

story.append(Paragraph("هوشمندسازی و شبکه", sH2))
story.append(bullet("قابلیت هوشمندسازی با <b>۴ دتکتور ۴کاناله (۱۶ لوپ)</b> — تشخیص حضور، Gap/Waste، آلارم"))
story.append(bullet("قابلیت تنظیم به صورت <b>فیکس یا هوشمند</b> با کنترل حداقل و حداکثر زمان حفاظتی در مد هوشمند"))
story.append(bullet("اتصال به مرکز کنترل و تنظیم <b>تمامی پارامترهای کنترلی از طریق TCP/IP</b> به صورت کاملا آنلاین و سریع"))
story.append(bullet("قابلیت <b>خاموش کردن تمامی سیگنال‌ها</b> و تست سالم بودن تک‌تک خروجی‌ها (Lamp Test)"))

# ── سخت افزار ──
story.append(Paragraph("مشخصات سخت‌افزاری", sH1))
story.append(hr())

hw = [
    ["بخش", "مشخصات"],
    ["پردازنده", "PLC دلتا — پردازنده قوی و صنعتی"],
    ["خروجی‌ها", "۲۴ فیوز شیشه‌ای ۳ آمپر + ۲۴ ترمینال سایز ۶ (سبز/زرد/قرمز) — رنگ سیم و ترمینال یکسان، شماره‌گذاری شده"],
    ["تغذیه", "پاور ۲۴ ولت صنعتی + فیوز مینیاتوری ۲۵ آمپر (قطع همزمان فاز و نول) + پریز تابلویی"],
    ["تابلو", "ابعاد ۲۰×۶۶×۴۶ cm — تابلو بارانی با کاور آب‌چکان روی قفل — لبه بیرونی پشت تابلو برای نصب سریع و محکم"],
    ["امکانات نصب", "چراغ تابلویی برای کار در شب + پنل تاشویی برای لپ‌تاپ"],
]
rows2=[]
for idx,row in enumerate(hw):
    st = sCellHead if idx==0 else ParagraphStyle(f"c{idx}", parent=sCell, alignment=TA_RIGHT)
    # Keep header centered, body right-aligned
    if idx==0:
        rows2.append([Paragraph(f"<b>{c}</b>", sCellHead) for c in row])
    else:
        rows2.append([Paragraph(row[0], ParagraphStyle("a", parent=sCell, alignment=TA_CENTER, fontName="Tahoma-Bold")), Paragraph(row[1], ParagraphStyle("b", parent=sCell, alignment=TA_RIGHT))])
t3 = Table(rows2, colWidths=[30*mm, W - 30*mm - 2*MARGIN - 6*mm])
t3.setStyle(TableStyle([
    ("BACKGROUND",(0,0),(-1,0), NAVY), ("TEXTCOLOR",(0,0),(-1,0), white),
    ("ROWBACKGROUNDS",(0,1),(-1,-1), [white, GRAY_BG]),
    ("GRID",(0,0),(-1,-1),0.4, GRAY_LINE), ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3),
    ("LEFTPADDING",(0,0),(-1,-1),4),("RIGHTPADDING",(0,0),(-1,-1),4),
]))
story.append(t3)
story.append(Spacer(1, 3*mm))
story.append(Paragraph("تمامی سیم‌کشی‌ها رنگ‌بندی شده و شماره‌گذاری شده برای سهولت نصب و عیب‌یابی.", sSmall))

# ── نرم افزار B30Controller ──
story.append(Paragraph("نرم‌افزار B30 Controller", sH1))
story.append(hr())
sw = [
    ["قابلیت", "توضیح"],
    ["اتصال آنلاین", "TCP/IP — اتصال همزمان به چند تقاطع، مانیتورینگ زنده وضعیت"],
    ["زمانبندی گرافیکی", "ویرایش ۲۷ برنامه هفتگی با جدول گرافیکی + تنظیم پارامترهای هوشمند"],
    ["تست لامپ", "خاموش/روشن تکی هر خروجی و تست سلامت سیگنال‌ها"],
    ["گزارش‌گیری", "خروجی Excel و لاگ وقایع + Probe زنده وضعیت تقاطع‌ها"],
    ["تنظیم IP گروهی", "تغییر IP/Netmask/Gateway برای چند تقاطع با چک تکراری + دکمه‌های SET/REFRESH"],
    ["امنیت", "رمز عبور برای تنظیمات حساس (لامپ تست و IP گروهی)"],
]
rows3=[]
for idx,row in enumerate(sw):
    if idx==0:
        rows3.append([Paragraph(f"<b>{c}</b>", sCellHead) for c in row])
    else:
        rows3.append([Paragraph(row[0], ParagraphStyle("a2", parent=sCell, alignment=TA_CENTER, fontName="Tahoma-Bold")), Paragraph(row[1], ParagraphStyle("b2", parent=sCell, alignment=TA_RIGHT))])
t4 = Table(rows3, colWidths=[32*mm, W - 32*mm - 2*MARGIN - 6*mm])
t4.setStyle(TableStyle([
    ("BACKGROUND",(0,0),(-1,0), NAVY), ("TEXTCOLOR",(0,0),(-1,0), white),
    ("ROWBACKGROUNDS",(0,1),(-1,-1), [white, GRAY_BG]),
    ("GRID",(0,0),(-1,-1),0.4, GRAY_LINE), ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3),
    ("LEFTPADDING",(0,0),(-1,-1),4),("RIGHTPADDING",(0,0),(-1,-1),4),
]))
story.append(t4)
story.append(Spacer(1, 3*mm))
story.append(Paragraph("نصب: اجرای setup_B30Controller_v2.0.exe — آیکون B30 در تسک‌بار — آدرس‌ها کنار exe ذخیره می‌شود (ماندگار).", sSmall))

# ── تماس ──
story.append(Spacer(1, 6*mm))
contact = Table([
    [Paragraph('<font color="#0F172A"><b>اطلاعات تماس و پشتیبانی</b></font>', ParagraphStyle("ct2", fontName="Tahoma-Bold", fontSize=9, leading=12, textColor=NAVY, alignment=TA_CENTER))],
    [Paragraph('وب‌سایت کاتالوگ:  SIM1617.github.io/B30-Controller  |  نرم‌افزار: B30Controller.exe  |  تابلو: ۲۰×۶۶×۴۶ cm', ParagraphStyle("ct3", fontName="Arial", fontSize=7, leading=10, textColor=MUTED, alignment=TA_CENTER))],
], colWidths=[W - 2*MARGIN])
contact.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1), GRAY_BG),("BOX",(0,0),(-1,-1),0.5,GRAY_LINE),("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),("LEFTPADDING",(0,0),(-1,-1),6),("RIGHTPADDING",(0,0),(-1,-1),6)]))
story.append(contact)

doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=20*mm, bottomMargin=12*mm, title="B30 Controller - Catalog", author="B30")
doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
print(f"PDF OK: {OUT}  {OUT.stat().st_size/1024:.0f} KB")
