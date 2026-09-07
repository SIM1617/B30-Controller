#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate B30 Word spec sheet."""
import pathlib
from docx import Document
from docx.shared import Pt, Inches, RGBColor, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.section import WD_ORIENTATION
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml

OUT = pathlib.Path("D:/Projects/B30_Spec.docx")
NAVY = RGBColor(0x0F, 0x17, 0x2A)
NAVY2 = RGBColor(0x1E, 0x29, 0x3B)
AMBER = RGBColor(0xF5, 0x9E, 0x0B)
MUTED = RGBColor(0x64, 0x74, 0x8B)
GREEN = RGBColor(0x10, 0xB9, 0x81)

def set_cell_bg(cell, color_hex):
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>')
    cell._tc.get_or_add_tcPr().append(shd)

def add_para(doc, text, size=9, bold=False, color=None, align=WD_ALIGN_PARAGRAPH.RIGHT, font="Tahoma", space_after=2):
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.line_spacing = 1.15
    # RTL
    pPr = p._p.get_or_add_pPr()
    bidi = parse_xml(f'<w:bidi {nsdecls("w")} w:val="1"/>')
    pPr.append(bidi)
    run = p.add_run(text)
    run.font.name = font
    run._element.rPr.rFonts.set(qn("w:eastAsia"), font)
    run._element.rPr.rFonts.set(qn("w:cs"), font)
    run.font.size = Pt(size)
    run.bold = bold
    if color: run.font.color.rgb = color
    return p

def add_heading(doc, text, level=1):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    pPr = p._p.get_or_add_pPr()
    pPr.append(parse_xml(f'<w:bidi {nsdecls("w")} w:val="1"/>'))
    # bottom border
    pBdr = parse_xml(f'<w:pBdr {nsdecls("w")}><w:bottom w:val="single" w:sz="6" w:space="4" w:color="F59E0B"/></w:pBdr>')
    pPr.append(pBdr)
    p.paragraph_format.space_before = Pt(10 if level==1 else 6)
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(text)
    run.font.name = "Tahoma"
    run._element.rPr.rFonts.set(qn("w:cs"), "Tahoma")
    run.font.size = Pt(13 if level==1 else 10)
    run.bold = True
    run.font.color.rgb = NAVY
    return p

def add_bullet(doc, text):
    p = doc.add_paragraph(style="List Bullet")
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    pPr = p._p.get_or_add_pPr()
    pPr.append(parse_xml(f'<w:bidi {nsdecls("w")} w:val="1"/>'))
    p.paragraph_format.space_after = Pt(1.5)
    p.clear()
    run = p.add_run(text)
    run.font.name = "Tahoma"
    run._element.rPr.rFonts.set(qn("w:cs"), "Tahoma")
    run.font.size = Pt(8.5)
    run.font.color.rgb = RGBColor(0x33, 0x41, 0x55)
    return p

def add_table(doc, headers, rows):
    table = doc.add_table(rows=1+len(rows), cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    # Header
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        set_cell_bg(cell, "0F172A")
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pPr = p._p.get_or_add_pPr()
        pPr.append(parse_xml(f'<w:bidi {nsdecls("w")} w:val="1"/>'))
        run = p.add_run(h)
        run.font.name = "Tahoma"; run._element.rPr.rFonts.set(qn("w:cs"), "Tahoma")
        run.font.size = Pt(7.5); run.bold = True; run.font.color.rgb = RGBColor(0xFF,0xFF,0xFF)
        cell.paragraphs[0].paragraph_format.space_after = Pt(1)
    # Rows
    for r_idx, row in enumerate(rows):
        for c_idx, val in enumerate(row):
            cell = table.rows[r_idx+1].cells[c_idx]
            bg = "F1F5F9" if r_idx % 2 == 1 else "FFFFFF"
            set_cell_bg(cell, bg)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if c_idx==0 else WD_ALIGN_PARAGRAPH.RIGHT
            pPr = p._p.get_or_add_pPr()
            pPr.append(parse_xml(f'<w:bidi {nsdecls("w")} w:val="1"/>'))
            run = p.add_run(val)
            run.font.name = "Tahoma"; run._element.rPr.rFonts.set(qn("w:cs"), "Tahoma")
            run.font.size = Pt(7.5)
            run.bold = (c_idx==0)
            run.font.color.rgb = RGBColor(0x1E,0x29,0x3B)
    # Borders
    tbl = table._tbl
    tblPr = tbl.tblPr
    tblBorders = parse_xml(f'<w:tblBorders {nsdecls("w")}><w:top w:val="single" w:sz="4" w:space="0" w:color="E2E8F0"/><w:left w:val="single" w:sz="4" w:space="0" w:color="E2E8F0"/><w:bottom w:val="single" w:sz="4" w:space="0" w:color="E2E8F0"/><w:right w:val="single" w:sz="4" w:space="0" w:color="E2E8F0"/><w:insideH w:val="single" w:sz="4" w:space="0" w:color="E2E8F0"/><w:insideV w:val="single" w:sz="4" w:space="0" w:color="E2E8F0"/></w:tblBorders>')
    tblPr.append(tblBorders)
    return table

doc = Document()
# Page setup
for section in doc.sections:
    section.page_width = Inches(8.27)
    section.page_height = Inches(11.69)
    section.top_margin = Inches(0.55)
    section.bottom_margin = Inches(0.45)
    section.left_margin = Inches(0.55)
    section.right_margin = Inches(0.55)
    sectPr = section._sectPr
    bidi = parse_xml(f'<w:bidi {nsdecls("w")} w:val="1"/>')
    sectPr.append(bidi)

style = doc.styles["Normal"]
style.font.name = "Tahoma"
style._element.rPr.rFonts.set(qn("w:cs"), "Tahoma")
style.font.size = Pt(8.5)
style.paragraph_format.space_after = Pt(2)
style.paragraph_format.bidi = True

# ── HEADER (cover) ──
# Big title
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_after = Pt(2)
run = p.add_run("B30  CONTROLLER")
run.font.name = "Arial"; run._element.rPr.rFonts.set(qn("w:cs"), "Arial")
run.font.size = Pt(28); run.bold = True; run.font.color.rgb = NAVY
# Split color via second run
p2 = doc.add_paragraph()
p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
p2.paragraph_format.space_after = Pt(1)
# Recolor B30 amber — do via separate paragraph trick: just keep as is for docx simplicity
p3 = doc.add_paragraph()
p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
run3 = p3.add_run("دستگاه فرماندهی چراغ راهنمایی — نسل جدید")
run3.font.name = "Tahoma"; run3._element.rPr.rFonts.set(qn("w:cs"), "Tahoma")
run3.font.size = Pt(11); run3.bold = True; run3.font.color.rgb = NAVY2

p4 = doc.add_paragraph()
p4.alignment = WD_ALIGN_PARAGRAPH.CENTER
p4.paragraph_format.space_after = Pt(6)
run4 = p4.add_run("کنترل ۸ فاز  •  ۸ پارت (۲۴ سیگنال)  •  مدهای هوشمند و زمانبندی  •  TCP/IP آنلاین  •  PLC دلتا")
run4.font.name = "Tahoma"; run4._element.rPr.rFonts.set(qn("w:cs"), "Tahoma")
run4.font.size = Pt(7.5); run4.font.color.rgb = MUTED

# Badges as table
bt = doc.add_table(rows=1, cols=3)
bt.alignment = WD_TABLE_ALIGNMENT.CENTER
for i, txt in enumerate(["۸ فاز متوالی", "۸ پارت / ۲۴ خروجی", "PLC Delta صنعتی"]):
    cell = bt.rows[0].cells[i]
    set_cell_bg(cell, "F59E0B" if i!=1 else "0F172A")
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    p = cell.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pPr = p._p.get_or_add_pPr(); pPr.append(parse_xml(f'<w:bidi {nsdecls("w")} w:val="1"/>'))
    run = p.add_run(txt); run.font.name="Tahoma"; run._element.rPr.rFonts.set(qn("w:cs"),"Tahoma")
    run.font.size=Pt(7); run.bold=True
    run.font.color.rgb = NAVY if i!=1 else RGBColor(0xFF,0xFF,0xFF)
doc.add_paragraph().paragraph_format.space_after = Pt(2)

# ── قابلیت نرم افزاری ──
add_heading(doc, "قابلیت‌های نرم‌افزاری", level=1)
add_para(doc, "کنترل فاز و پارت", size=10, bold=True, color=NAVY2)
add_bullet(doc, "کنترل تا ۸ فاز متوالی با زمانبندی مستقل برای هر فاز (سبز، زرد، قرمز، All-Red، حداقل و حداکثر حفاظتی)")
add_bullet(doc, "دارای ۸ پارت خروجی معادل ۲۴ سیگنال مجزای سبز / زرد / قرمز — هر پارت قابل تنظیم در هر فاز به عنوان خودرو، عابر، چشمک زرد یا چشمک قرمز")
add_bullet(doc, "قابلیت تنظیم فازها در دو حالت کم‌باری و اوج بار (دو جدول متفاوت فازبندی)")

add_para(doc, "مدهای کاری", size=10, bold=True, color=NAVY2)
add_table(doc, ["مد", "توضیح"], [
    ["چشمک‌زن دائم", "چشمک زرد / قرمز دائم برای هر پارت"],
    ["زمانبندی (Fixed)", "اجرای جدول زمانبندی ثابت با ۲۷ برنامه هفتگی"],
    ["هوشمند (Actuated)", "فیکس یا هوشمند + کنترل حداقل/حداکثر حفاظتی با دتکتور"],
    ["کنترل پلیس", "کنترل دستی با اعمال فوری"],
])
add_para(doc, "", size=2)

add_para(doc, "زمانبندی و تقویم", size=10, bold=True, color=NAVY2)
add_bullet(doc, "۲۷ زمانبندی مختلف برای روزهای مختلف هفته — هر روز برنامه مجزا")
add_bullet(doc, "تاریخ شمسی و میلادی همزمان + تنظیم سریع ساعت، تاریخ و IP شبکه")
add_bullet(doc, "تنظیم راحت رنگ چشمک‌زن (زرد / قرمز / خاموش دائم) برای هر پارت")

add_para(doc, "هوشمندسازی و شبکه", size=10, bold=True, color=NAVY2)
add_bullet(doc, "۴ دتکتور ۴کاناله (۱۶ لوپ) — تشخیص حضور، Gap/Waste، آلارم")
add_bullet(doc, "قابلیت فیکس یا هوشمند با کنترل حداقل و حداکثر زمان حفاظتی")
add_bullet(doc, "اتصال به مرکز کنترل و تنظیم تمامی پارامترها از طریق TCP/IP به صورت کاملا آنلاین و سریع")
add_bullet(doc, "خاموش کردن تمامی سیگنال‌ها و تست تک‌تک خروجی‌ها (Lamp Test)")

# ── مشخصات سخت افزاری ──
add_heading(doc, "مشخصات سخت‌افزاری", level=1)
add_table(doc, ["بخش", "مشخصات"], [
    ["پردازنده", "PLC دلتا — پردازنده قوی و صنعتی، قابل اعتماد"],
    ["خروجی‌ها", "۲۴ فیوز شیشه‌ای ۳ آمپر + ۲۴ ترمینال سایز ۶ (سبز/زرد/قرمز) — رنگ سیم و ترمینال یکسان، شماره‌گذاری شده"],
    ["تغذیه", "پاور ۲۴ ولت صنعتی + فیوز مینیاتوری ۲۵ آمپر (قطع همزمان فاز و نول) + پریز تابلویی"],
    ["تابلو", "۲۰×۶۶×۴۶ cm — بارانی با کاور آب‌چکان روی قفل — لبه بیرونی پشت برای نصب سریع و محکم"],
    ["امکانات نصب", "چراغ تابلویی برای کار در شب + پنل تاشویی برای لپ‌تاپ"],
])
p = add_para(doc, "تمامی سیم‌کشی‌ها رنگ‌بندی و شماره‌گذاری شده برای سهولت نصب و عیب‌یابی.", size=7, color=MUTED)

# ── نرم افزار ──
add_heading(doc, "نرم‌افزار B30 Controller", level=1)
add_table(doc, ["قابلیت", "توضیح"], [
    ["اتصال آنلاین", "TCP/IP — اتصال همزمان به چند تقاطع، مانیتورینگ زنده"],
    ["زمانبندی گرافیکی", "ویرایش ۲۷ برنامه هفتگی با جدول گرافیکی"],
    ["تست لامپ", "خاموش/روشن تکی هر خروجی و تست سلامت"],
    ["گزارش‌گیری", "خروجی Excel و لاگ وقایع + Probe زنده"],
    ["تنظیم IP گروهی", "تغییر IP/Netmask/Gateway با چک تکراری — دکمه‌های SET/REFRESH"],
    ["امنیت", "رمز عبور برای تنظیمات حساس"],
])
add_para(doc, "نصب: اجرای setup_B30Controller_v2.0.exe — آیکون B30 در تسک‌بار — آدرس‌ها کنار exe (ماندگار).", size=7, color=MUTED)

# ── Footer contact ──
doc.add_paragraph().paragraph_format.space_after = Pt(4)
pt = doc.add_table(rows=1, cols=1)
pt.alignment = WD_TABLE_ALIGNMENT.CENTER
cell = pt.rows[0].cells[0]
set_cell_bg(cell, "F1F5F9")
cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
p = cell.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER
pPr = p._p.get_or_add_pPr(); pPr.append(parse_xml(f'<w:bidi {nsdecls("w")} w:val="1"/>'))
run = p.add_run("SIM1617.github.io/B30-Controller  |  B30Controller.exe  |  تابلو ۲۰×۶۶×۴۶ cm  |  Version 2.0 — 2026")
run.font.name="Arial"; run._element.rPr.rFonts.set(qn("w:cs"),"Arial")
run.font.size=Pt(7); run.font.color.rgb = MUTED

# Fix default language to Persian RTL for whole doc
# Set document default to RTL
doc.core_properties.title = "B30 Controller - Catalog"
doc.core_properties.subject = "Traffic Controller Spec"
doc.core_properties.author = "B30"

doc.save(str(OUT))
print(f"DOCX OK: {OUT}  {OUT.stat().st_size/1024:.0f} KB")
