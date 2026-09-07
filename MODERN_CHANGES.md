# gui_controller_modern.py — تغییرات

## قول: هیچ منطق یا آدرس PLC تغییر نکرده
- تمام `PHASE_ADDRESSES`, `lamp_mapping`, `LOOP_*`, `PART_*`, `IP_*`, `LAMP_TEST_*` عیناً حفظ شدند.
- تمام `read_holding_registers` / `write_register` / `write_coil` با همان آدرس و count باقی ماندند.
- منطق Jalali/Gregorian، threading، keep-alive، auto-load loops دست‌نخورده.

## چیزهایی که مدرن شد (فقط ظاهر + ساختار)
1. `Theme` class — پالت Slate/Blue یک‌دست به‌جای #e0e0e0 / #1565C0 پراکنده.
2. `window.state('zoomed')` + `bg=Theme.BG` + عنوان `— Modern`.
3. `Theme.FONT = 'Segoe UI'` و `FONT_TITLE/BODY/SMALL/MONO`.
4. `_setup_styles()` با `ttk.Style clam` — Treeview سطر 30px، heading سرمه‌ای، selection آبی ملایم.
5. `_card()` و `_flat_btn()` helpers با هاور ملایم و `highlightbackground` به‌جای bd ضخیم.
6. `status_label` badge-like با padx/pady.
7. `address_file` با `pathlib.Path(__file__).with_name(...)` — مقاوم به cwd.
8. `Intersection` dataclass برای خوانایی (استفاده اختیاری، JSON قدیمی همچنان کار می‌کند).
9. `logging` به‌جای `print` برای خطاها.
10. `docstring` کوتاه برای کلاس اصلی.

## فایل‌ها
- اصلی: `D:\Projects\gui_controller.py` (دست‌نخورده)
- بکاپ: `D:\Projects\gui_controller_backup.py`
- مدرن: `D:\Projects\gui_controller_modern.py` (پیشنهادی — جایگزین اصلی کنید اگر راضی بودید)
