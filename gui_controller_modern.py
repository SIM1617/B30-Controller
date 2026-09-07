import tkinter as tk
from tkinter import ttk, messagebox
from pymodbus.client import ModbusTcpClient
import json
import os
import sys
import subprocess
import pathlib
import threading
import time
import logging
from datetime import datetime
from dataclasses import dataclass

# ─── B30 License System (embedded public key, hwid, online activation) ───
from license_helper import HWID, verify_license_lic
from license_dialog import show_license_dialog, activate_with_file_dialog
_LICENSE_FILE = "license.lic"
_LICENSE_EXPIRY_DAYS = 365

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

# ── Crash handler — برنامه را به‌جای بستن، نگه می‌دارد و پیغام می‌دهد ──
import traceback as _tb
import queue as _queue

# ─────────────────────────────────────────────
# Theme — فقط ظاهر / only visuals
# هیچ آدرس PLC تغییر نکرده
# ─────────────────────────────────────────────
class Theme:
    BG              = "#F1F5F9"
    BG_CARD         = "#FFFFFF"
    BG_SIDEBAR      = "#0F172A"
    BG_SURFACE      = "#E2E8F0"
    BG_TABLE_HEAD   = "#1E3A5F"
    BG_PRIMARY      = "#2563EB"
    BG_PRIMARY_DARK = "#1D4ED8"
    TEXT            = "#0F172A"
    TEXT_MUTED      = "#64748B"
    TEXT_ON_DARK    = "#F8FAFC"
    BORDER          = "#E2E8F0"
    SUCCESS         = "#10B981"
    WARNING         = "#F59E0B"
    DANGER          = "#EF4444"
    FONT            = "Segoe UI"

FONT_TITLE = (Theme.FONT, 13, "bold")
FONT_BODY  = (Theme.FONT, 10)
FONT_SMALL = (Theme.FONT, 9)
FONT_MONO  = ("Consolas", 10, "bold")

@dataclass
class Intersection:
    name: str
    ip: str
    port: str = "502"
    desc: str = ""
    status: str = "\u0642\u0637\u0639"


class TrafficControllerApp:
    """B30 Traffic Controller — Modern UI (logic & PLC addresses unchanged)."""

    # ─── License helpers — called from __init__ after window creation ───
    def _check_license(self):
        ok, msg = verify_license_lic(pathlib.Path(_LICENSE_FILE))
        if ok:
            print("[LICENSE] OK:", msg)
            return True
        return False

    def _show_activation_dialog(self):
        hwid = HWID.get()
        win = tk.Toplevel(self.window)
        win.title("فعال‌سازی B30 Controller")
        win.geometry("520x420")
        win.transient(self.window)
        win.grab_set()
        try:
            win.configure(bg=Theme.BG)
        except Exception:
            pass
        frm = ttk.Frame(win, padding=18)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text="کد دستگاه شما:", font=FONT_SMALL).pack(anchor="e")
        h_lbl = ttk.Label(frm, text=hwid, font=FONT_MONO, foreground=Theme.BG_PRIMARY)
        h_lbl.pack(anchor="e", pady=(2, 10))
        ttk.Label(frm, text="پلن را انتخاب کنید:", font=FONT_SMALL).pack(anchor="e", pady=(6, 4))
        plan_var = tk.StringVar(value="base")
        plans = [("پایه — 1 تقاطع / 6 ماهه — 1.5م", "base"), ("حرفه‌ای — 5 تقاطع / 1 ساله — 4.5م", "pro"), ("نامحدود — دائمی — 9م", "unlimited")]
        for label, val in plans:
            ttk.Radiobutton(frm, text=label, variable=plan_var, value=val).pack(anchor="e")
        ttk.Label(frm, text="ایمیل (برای دریافت لایسنس):", font=FONT_SMALL).pack(anchor="e", pady=(10, 2))
        email_var = tk.StringVar()
        ttk.Entry(frm, textvariable=email_var, width=36, justify="center").pack(anchor="e")
        status_lbl = ttk.Label(frm, text="پس از پرداخت، فایل license.lic کنار exe قرار می‌گیرد.", font=FONT_SMALL, foreground=Theme.TEXT_MUTED)
        status_lbl.pack(anchor="e", pady=(10, 6))

        def on_open_site():
            email = email_var.get().strip()
            if not email or "@" not in email:
                messagebox.showwarning("ایمیل", "ایمیل معتبر وارد کنید.", parent=win)
                return
            plan = plan_var.get()
            price_map = {"base": 1500000, "pro": 4500000, "unlimited": 9000000}
            amount = price_map.get(plan, 1500000)
            url = f"https://SIM1617.github.io/B30-Controller/?email={email}&plan={plan}&hwid={hwid}&amount={amount}"
            try:
                import webbrowser as _wb
                _wb.open(url)
            except Exception:
                pass
            try:
                win.clipboard_clear()
                win.clipboard_append(f"HWID:{hwid} | Email:{email} | Plan:{plan}")
            except Exception:
                pass
            messagebox.showinfo("کپی شد", f"لینک پرداخت در مرورگر باز شد.\nHWID کپی شد: {hwid}\nاگر مرورگر باز نشد، این آدرس را دستی باز کنید:\n{url}", parent=win)

        btn_row = ttk.Frame(frm)
        btn_row.pack(fill="x", pady=(12, 0))
        ttk.Button(btn_row, text="باز کردن صفحه پرداخت", command=on_open_site).pack(side="left")
        ttk.Button(btn_row, text="انتخاب فایل license.lic", command=lambda: self._pick_license_file(win)).pack(side="left", padx=(8, 0))
        win.bind("<Return>", lambda _e: on_open_site())

    def _pick_license_file(self, parent_win=None):
        p = filedialog.askopenfilename(title="انتخاب فایل license.lic", filetypes=[("License", "*.lic"), ("All", "*.*")])
        if not p:
            return
        try:
            data = pathlib.Path(p).read_bytes()
            dest = pathlib.Path(_LICENSE_FILE)
            dest.write_bytes(data)
            ok, msg = verify_license_lic(dest)
            if ok:
                messagebox.showinfo("لایسنس", f"فعال شد: {msg}", parent=parent_win or self.window)
                if parent_win:
                    try:
                        parent_win.destroy()
                    except Exception:
                        pass
            else:
                messagebox.showerror("لایسنس", f"نامعتبر: {msg}", parent=parent_win or self.window)
        except Exception as e:
            messagebox.showerror("خطا", str(e), parent=parent_win or self.window)

    def __init__(self):
        self.window = tk.Tk()
        self.window.title("B30 Controller")
        # window / taskbar icon (works both in dev and inside PyInstaller onefile)
        try:
            _base = pathlib.Path(sys.executable).parent if getattr(sys, "frozen", False) else pathlib.Path(__file__).parent
            for _p in (_base / "B30.ico", pathlib.Path(__file__).with_name("B30.ico"), pathlib.Path("D:/Projects/B30.ico")):
                if _p.exists():
                    self.window.iconbitmap(str(_p))
                    break
        except Exception:
            pass
        try:
            _png = pathlib.Path(__file__).with_name("B30_preview.png")
            if _png.exists():
                _img = tk.PhotoImage(file=str(_png))
                self.window.iconphoto(True, _img)
                self._icon_ref = _img  # keep ref
        except Exception:
            pass
        self.window.geometry("1500x900")
        try:
            self.window.state("zoomed")
        except Exception:
            pass
        self.window.configure(bg=Theme.BG)
        self._setup_styles()
        
        self.client = None
        self.is_connected = False
        self.address_file = str(pathlib.Path(__file__).with_name("addresses.json")) if "__file__" in globals() else "addresses.json"
        self.is_updating = False
        self.current_page = "login"
        self.selected_option = None
        self.auto_update_running = False
        self.connection_lost = False
        self.keep_alive_running = False
        self.police_alive_running = False
        self.timing_page_auto_load_running = False
        self.blink_page_auto_load_running = False
        self.phase_count_update_running = False
        self.part_settings_page_auto_load_running = False
        self.loop_settings_page_auto_load_running = False
        self.loop_status_page_auto_load_running = False
        self._loop_status_loading = False
        
        self.focused_timing_entry = None
        self.focused_timing_field = None
        self.focused_timing_prog = None
        self.user_is_editing_timing = False
        self._timing_pending = {}
        self._timing_write_scheduled = False
        self.user_is_editing_blink = False
        self.user_is_editing_part_settings = False
        self._part_pending = {}
        self._part_write_scheduled = False
        self.user_is_editing_loops = False
        self.bulk_ip_unlocked = False
        self.bulk_ip_rows = {}
        self._bulk_pinging = False
        
        self.plc_lock = threading.Lock()
        self.is_editing_settings = False
        self.is_editing_table = False
        self._focused_phase_entry = None
        
        self.phase_count = 2
        self.work_mode = 0
        self.current_phase = 1
        self.demo_mode = True
        self.command_on = False
        
        self.lamp_status = {
            i: {"green": False, "yellow": False, "red": False} for i in range(1, 9)
        }
        
        self.SETTINGS_ADDRESSES = {
            "sensors": {"address": 4535},
            "green_time": {"address": 4686},
            "control_mode": {"address": 4685},
        }
        
        self.PHASE_ADDRESSES = {
            "green":  [4537, 4538, 4539, 4540, 4541, 4542, 4543, 4544],
            "yellow": [4507, 4508, 4509, 4510, 4511, 4512, 4513, 4514],
            "red":    [4097, 4098, 4099, 4100, 4101, 4102, 4103, 4104],
            "all_red":[4527, 4528, 4529, 4530, 4531, 4532, 4533, 4534],
            "min":    [4547, 4548, 4549, 4550, 4551, 4552, 4553, 4554],
            "max":    [4517, 4518, 4519, 4520, 4521, 4522, 4523, 4524],
        }
        
        self.lamp_mapping = {
            1: {"green": 2124, "yellow": 2123, "red": 2122},
            2: {"green": 2121, "yellow": 2120, "red": 2119},
            3: {"green": 2144, "yellow": 2143, "red": 2142},
            4: {"green": 2141, "yellow": 2140, "red": 2139},
            5: {"green": 2137, "yellow": 2136, "red": 2135},
            6: {"green": 2134, "yellow": 2133, "red": 2132},
            7: {"green": 2131, "yellow": 2130, "red": 2129},
            8: {"green": 2127, "yellow": 2126, "red": 2125},
        }
        
        self.phase_lamp_mapping = {
            1: {"green": 2251, "yellow": 2250, "red": 2249},
            2: {"green": 2254, "yellow": 2253, "red": 2252},
            3: {"green": 2257, "yellow": 2256, "red": 2255},
            4: {"green": 2260, "yellow": 2259, "red": 2258},
            5: {"green": 2271, "yellow": 2270, "red": 2269},
            6: {"green": 2274, "yellow": 2273, "red": 2272},
            7: {"green": 2277, "yellow": 2276, "red": 2275},
            8: {"green": 2280, "yellow": 2279, "red": 2278},
        }
        
        self.timing_base_addresses = [6096 + (i * 32) for i in range(27)]
        
        self.PART_BLINK_ADDRESSES = {
            1: 4687, 2: 4688, 3: 4689, 4: 4690,
            5: 4691, 6: 4692, 7: 4693, 8: 4694,
        }
        self.PEDESTRIAN_BLINK_ADDRESS = 4695
        
        self.PART_SETTINGS_TABLE1_BASE = 4555
        self.PART_SETTINGS_TABLE2_BASE = 4620
        
        self.PHASE_COUNT_ADDRESS = 4684  # سازگاری legacy
        self.MAIN_PHASE_COUNT_READ_ADDRESS = 4504  # صفحه اصلی — فقط خواندن تعداد فاز
        self.PART_PHASE_COUNT_ADDRESS = 4619  # جدول1
        self.PART_PHASE_COUNT_TABLE1 = 4619  # تعداد فاز جدول1 (R/W)
        self.PART_PHASE_COUNT_TABLE2 = 4684  # تعداد فاز جدول2 (R/W)
        
        self.LOOP_TABLE1_BASE = 7746
        self.LOOP_TABLE2_BASE = 7876
        
        self.DETECTOR_RESET_ADDRESSES = {
            1: 2149, 2: 2150, 3: 2151, 4: 2152,
        }
        
        self.DETECTOR_ERROR_ADDRESSES = {
            1: 2055, 2: 2056, 3: 2057, 4: 2058,
        }
        
        self.LOOP_SENSOR_STATUS = {
            1: 2327, 2: 2328, 3: 2329, 4: 2330,
            5: 2335, 6: 2336, 7: 2337, 8: 2338,
            9: 2343, 10: 2344, 11: 2345, 12: 2346,
            13: 2351, 14: 2352, 15: 2353, 16: 2354
        }
        
        self.LOOP_ALARM_STATUS = {
            1: 2506, 2: 2507, 3: 2508, 4: 2509,
            5: 2510, 6: 2511, 7: 2512, 8: 2513,
            9: 2514, 10: 2515, 11: 2516, 12: 2517,
            13: 2518, 14: 2519, 15: 2520, 16: 2521
        }
        
        self.LOOP_CAR_STATUS = {
            1: 2323, 2: 2324, 3: 2325, 4: 2326,
            5: 2331, 6: 2332, 7: 2333, 8: 2334,
            9: 2339, 10: 2340, 11: 2341, 12: 2342,
            13: 2347, 14: 2348, 15: 2349, 16: 2350
        }
        
        self.LOOP_GAP_ADDRESSES = {i: 7714 + (i-1)*2 for i in range(1, 17)}
        self.LOOP_WASTE_ADDRESSES = {i: 7715 + (i-1)*2 for i in range(1, 17)}
        
        self.LOOP_GAP_TIME_ADDRESSES = {i: 4298 + (i-1)*5 for i in range(1, 17)}
        self.LOOP_WASTE_TIME_ADDRESSES = {i: 4299 + (i-1)*5 for i in range(1, 17)}
        
        self.IP_SET_COIL = 2162
        self.IP_REFRESH_COIL = 2163
        self.TIME_SET_COIL = 2104
        self.DST_ADDRESS = 7496
        
        self.POLICE_ALIVE_COIL = 2110  # پلیس زنده — هر 5 ثانیه پالس 1 (PLC خود 0 می‌کند)
        self.LAMP_TEST_MODE_ADDRESS = 4506
        self.LAMP_TEST_BASE_ADDRESS = 2649
        
        self.day_names = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه", "شنبه", "یکشنبه"]
        self.WEEKDAY_5414_ADDRESS = 5414
        self.WEEKDAY_5414_NAMES = self.day_names  # 5414: 1=دوشنبه .. 7=یکشنبه
        self.WEEKDAY_4247_NAMES = self.day_names  # 4247: همان منطق 1=دوشنبه .. 7=یکشنبه
        
        self.blink_vars = {}
        self.blink_status_labels = {}
        
        self.part_settings_combos = {}
        self.current_part_table = 1
        
        self.loop_combos = {}
        self._loop_building = False
        self._loop_loading = False
        self.current_loop_table = 1
        
        self.card_error_lights = {}
        self.card_reset_buttons = {}
        self.loop_status_widgets = {}
        
        self.lamp_test_lights = {}
        self.lamp_test_lights_colors = {}
        self.lamp_test_running = False
        self.lamp_test_enabled_var = None
        self.lamp_test_momentary_var = None
        self._last_lamp_test_toggle = 0
        self.blink_combos = {}
        
        self.setup_ui()
        self.load_data()
        # ── License gate — block UI if not licensed (show activation, wait) ──
        self._license_ok = self._check_license()
        if not self._license_ok:
            # Defer showing dialog until window is drawn, so Toplevel can parent correctly
            self.window.after(400, self._show_activation_dialog)
        self.live_status_running = False
        self._after_ids = {}
        self._crash_log_path = str(pathlib.Path(__file__).with_name("crash.log")) if "__file__" in globals() else "crash.log"
        self._last_crash_time = 0
        self._crash_count = 0
        try:
            self.window.protocol("WM_DELETE_WINDOW", self._on_window_close)
        except Exception:
            pass
        self._install_crash_handlers()
        self._start_live_status_probe()

    def _install_crash_handlers(self):
        import sys as _sys
        import threading as _th
        try:
            self._orig_excepthook = _sys.excepthook
        except Exception:
            self._orig_excepthook = None
        try:
            self._orig_thread_excepthook = getattr(_th, 'excepthook', None)
        except Exception:
            self._orig_thread_excepthook = None
        try:
            self._orig_report_callback = getattr(self.window, 'report_callback_exception', None)
        except Exception:
            self._orig_report_callback = None

        def _excepthook(exc_type, exc_val, exc_tb):
            try:
                logging.error("UNCAUGHT: %s: %s\n%s", exc_type.__name__, exc_val, "".join(_tb.format_exception(exc_type, exc_val, exc_tb)))
                self._handle_crash(exc_type, exc_val, exc_tb)
            except Exception:
                pass
            try:
                if self._orig_excepthook and self._orig_excepthook is not _excepthook:
                    self._orig_excepthook(exc_type, exc_val, exc_tb)
            except Exception:
                pass

        def _thread_excepthook(args):
            try:
                logging.error("THREAD UNCAUGHT in %s: %s: %s\n%s", getattr(args, 'thread', '?'), args.exc_type.__name__, args.exc_value, "".join(_tb.format_exception(args.exc_type, args.exc_value, args.exc_traceback)))
                self._handle_crash(args.exc_type, args.exc_value, args.exc_traceback, thread_name=str(getattr(args, 'thread', '?')))
            except Exception:
                pass
            try:
                if self._orig_thread_excepthook and self._orig_thread_excepthook is not _thread_excepthook:
                    try:
                        self._orig_thread_excepthook(args)
                    except TypeError:
                        pass
            except Exception:
                pass

        try:
            _sys.excepthook = _excepthook
        except Exception:
            pass
        try:
            _th.excepthook = _thread_excepthook
        except Exception:
            pass
        try:
            self.window.report_callback_exception = lambda exc_type, exc_val, exc_tb: _excepthook(exc_type, exc_val, exc_tb)
        except Exception:
            pass

    def _handle_crash(self, exc_type, exc_val, exc_tb, thread_name=None):
        import time as _t
        if not exc_type or not exc_val:
            return
        now = _t.time()
        if now - getattr(self, '_last_crash_time', 0) < 2:
            self._crash_count = getattr(self, '_crash_count', 0) + 1
            if self._crash_count > 2:
                return
        else:
            self._crash_count = 0
        self._last_crash_time = now
        try:
            tb_text = "".join(_tb.format_exception(exc_type, exc_val, exc_tb))
        except Exception:
            tb_text = f"{exc_type.__name__}: {exc_val}"
        where = f" [{thread_name}]" if thread_name else ""
        msg_short = f"{exc_type.__name__}{where}: {exc_val}"
        try:
            with open(self._crash_log_path, "a", encoding="utf-8") as f:
                f.write(f"\n{'='*60}\n{time.strftime('%Y-%m-%d %H:%M:%S')} {msg_short}\n{tb_text}\n")
        except Exception:
            pass
        # حلقه‌ها را قبل از هر دیالوگ متوقف کن تا هنگ جمع نشود — بدون لمس ویجت‌ها
        try:
            for k in list(getattr(self, '_after_ids', {}).keys()):
                try:
                    self._cancel_after(k)
                except Exception:
                    pass
            for attr in ["timing_page_auto_load_running", "blink_page_auto_load_running",
                         "part_settings_page_auto_load_running", "loop_settings_page_auto_load_running",
                         "loop_status_page_auto_load_running", "auto_update_running",
                         "phase_count_update_running", "keep_alive_running",
                         "police_alive_running", "lamp_test_keepalive_running", "live_status_running",
                         "_ip_time_live_running"]:
                try:
                    setattr(self, attr, False)
                except Exception:
                    pass
        except Exception:
            pass
        # ویجت ممکن است از بین رفته باشد — فقط اگر پنجره زنده است دیالوگ نشان بده
        try:
            if not getattr(self, 'window', None) or not self.window.winfo_exists():
                return
        except Exception:
            return
        def _show():
            try:
                if not self.window.winfo_exists():
                    return
                if now - getattr(self, '_last_crash_dialog', 0) < 5:
                    return
                self._last_crash_dialog = now
                detail = tb_text[-900:] if len(tb_text) > 900 else tb_text
                if not messagebox.askretrycancel("خطای برنامه — کرش هندلر",
                    f"یک خطای غیرمنتظره رخ داد ولی برنامه باز نگه داشته شد:\n\n{msg_short}\n\n"
                    f"جزئیات:\n{detail}\n\n"
                    f"لاگ: {self._crash_log_path}\n\n"
                    "Retry = ادامه و تلاش مجدد\nCancel = بازگشت به صفحه ورود",
                    icon="warning", parent=self.window):
                    try:
                        self.go_back()
                    except Exception:
                        pass
                else:
                    try:
                        idx = getattr(self, 'selected_option', None)
                        if idx == 0:
                            self.start_auto_update()
                        elif idx == 1:
                            self.timing_page_auto_load_running = True
                            self._auto_load_timing_loop()
                        elif idx == 2:
                            self.blink_page_auto_load_running = True
                            self._auto_load_blink_loop()
                        elif idx == 3:
                            self.part_settings_page_auto_load_running = True
                            self._auto_load_part_settings_loop()
                        elif idx == 4:
                            self.loop_settings_page_auto_load_running = True
                            self._auto_load_loop_loop()
                        elif idx == 5:
                            self.loop_status_page_auto_load_running = True
                            self._auto_load_loop_status_loop()
                    except Exception:
                        pass
            except Exception:
                pass
        try:
            self.window.after(100, _show)
        except Exception:
            pass
        
    def _schedule_after(self, key, delay, func):
        try:
            old = self._after_ids.get(key)
            if old:
                try:
                    self.window.after_cancel(old)
                except Exception:
                    pass
        except Exception:
            pass
        try:
            aid = self.window.after(delay, func)
            self._after_ids[key] = aid
            return aid
        except Exception:
            return None

    def _cancel_after(self, key):
        try:
            aid = self._after_ids.pop(key, None)
            if aid:
                try:
                    self.window.after_cancel(aid)
                except Exception:
                    pass
        except Exception:
            pass

    def _setup_styles(self):
        try:
            style = ttk.Style(self.window)
            try:
                style.theme_use("clam")
            except Exception:
                pass
            style.configure("TLabel", background=Theme.BG, foreground=Theme.TEXT, font=FONT_BODY)
            style.configure("TFrame", background=Theme.BG)
            style.configure("Card.TFrame", background=Theme.BG_CARD)
            style.configure("Card.TLabel", background=Theme.BG_CARD, foreground=Theme.TEXT)
            style.configure("TButton", font=(Theme.FONT, 10, "bold"), padding=6)
            style.configure("Primary.TButton", background=Theme.BG_PRIMARY, foreground="white")
            style.configure("Treeview", background=Theme.BG_CARD, fieldbackground=Theme.BG_CARD,
                            foreground=Theme.TEXT, rowheight=30, font=FONT_BODY, borderwidth=0, relief="flat")
            style.configure("Treeview.Heading", background=Theme.BG_TABLE_HEAD, foreground="white",
                            font=(Theme.FONT, 10, "bold"), padding=8, relief="flat")
            style.map("Treeview", background=[("selected", "#DBEAFE")], foreground=[("selected", Theme.TEXT)])
            style.map("Green.TCombobox", fieldbackground=[("readonly", "#66BB6A")], background=[("readonly", "#66BB6A")])
            style.map("Red.TCombobox", fieldbackground=[("readonly", "#EF5350")], background=[("readonly", "#EF5350")])
            style.map("Yellow.TCombobox", fieldbackground=[("readonly", "#FBC02D")], background=[("readonly", "#FBC02D")])
            style.configure("LightGreen.TCombobox", fieldbackground="#A5D6A7", background="#A5D6A7", foreground="black", arrowcolor="black")
            style.configure("DarkGreen.TCombobox", fieldbackground="#2E7D32", background="#2E7D32", foreground="white", arrowcolor="white")
            style.map("LightGreen.TCombobox", fieldbackground=[("readonly", "#A5D6A7")], background=[("readonly", "#A5D6A7")])
            style.map("DarkGreen.TCombobox", fieldbackground=[("readonly", "#2E7D32")], background=[("readonly", "#2E7D32")])
            style.configure("TEntry", padding=5, relief="flat")
            style.configure("TCombobox", padding=5)
            style.configure("Vertical.TScrollbar", background=Theme.BG_SURFACE, troughcolor=Theme.BG, arrowcolor=Theme.TEXT_MUTED)
            style.configure("Horizontal.TScrollbar", background=Theme.BG_SURFACE, troughcolor=Theme.BG, arrowcolor=Theme.TEXT_MUTED)
            # رنگ فیلدها: غیرفعال قرمز، فعال سبز، پلیس قرمز، چشمک‌زرد زرد
            style.configure("Green.TCombobox", fieldbackground="#66BB6A", background="#66BB6A", foreground="black", arrowcolor="black")
            style.configure("Red.TCombobox", fieldbackground="#EF5350", background="#EF5350", foreground="white", arrowcolor="white")
            style.configure("Yellow.TCombobox", fieldbackground="#FBC02D", background="#FBC02D", foreground="black", arrowcolor="black")
            style.configure("White.TCombobox", fieldbackground="white", background="white", foreground="black", arrowcolor="black")
            # کارت مدرن — با highlight به‌جای bd
            self._card_kwargs = dict(bg=Theme.BG_CARD, highlightbackground=Theme.BORDER, highlightthickness=1, bd=0)
        except Exception as e:
            logging.debug(f"style error: {e}")

    def _apply_main_settings_colors(self):
        def _set_combo(combo, style_name, field_bg):
            try:
                combo.configure(style=style_name)
                # خود فیلد هم باید پررنگ شود — بعضی تم‌ها فقط style را جزئی اعمال می‌کنند
                style = __import__('tkinter').ttk.Style(combo)
                style.map(style_name, fieldbackground=[("readonly", field_bg), ("!readonly", field_bg)],
                          background=[("readonly", field_bg)], foreground=[("readonly", "black")])
                # fallback: مستقیم روی ویجت هم اگر theme اجازه داد
                try:
                    combo.tk.call(combo._w, "configure", "-fieldbackground", field_bg)
                except Exception:
                    pass
            except Exception:
                pass
        try:
            v = self.sensors_var.get() if hasattr(self, 'sensors_var') else ""
            if hasattr(self, 'sensors_combo'):
                if v == "فعال":
                    _set_combo(self.sensors_combo, "Green.TCombobox", "#66BB6A")
                else:
                    _set_combo(self.sensors_combo, "Red.TCombobox", "#EF5350")
            v2 = self.green_time_var.get() if hasattr(self, 'green_time_var') else ""
            if hasattr(self, 'green_time_combo'):
                if v2 == "دستی":
                    _set_combo(self.green_time_combo, "Green.TCombobox", "#66BB6A")
                else:
                    _set_combo(self.green_time_combo, "Red.TCombobox", "#EF5350")
            v3 = self.control_var.get() if hasattr(self, 'control_var') else ""
            if hasattr(self, 'control_combo'):
                if v3 == "پلیس":
                    _set_combo(self.control_combo, "Red.TCombobox", "#EF5350")
                elif v3 == "دائمی فلش":
                    _set_combo(self.control_combo, "Yellow.TCombobox", "#FBC02D")
                else:
                    _set_combo(self.control_combo, "White.TCombobox", "#FFFFFF")
        except Exception:
            pass

    def _apply_blink_colors(self):
        def _set_combo(combo, style_name, field_bg):
            try:
                combo.configure(style=style_name)
                style = __import__('tkinter').ttk.Style(combo)
                is_red = field_bg == "#EF5350"
                style.map(style_name, fieldbackground=[("readonly", field_bg), ("!readonly", field_bg)],
                          background=[("readonly", field_bg)], foreground=[("readonly", "white" if is_red else "black")])
                try:
                    combo.tk.call(combo._w, "configure", "-fieldbackground", field_bg)
                except Exception:
                    pass
            except Exception:
                pass
        try:
            for part_num in range(1, 9):
                if part_num in getattr(self, 'blink_vars', {}) and part_num in getattr(self, 'blink_combos', {}):
                    combo = self.blink_combos[part_num]
                    var = self.blink_vars[part_num][0]
                    val = var.get()
                    if val == "چشمک زن قرمز":
                        _set_combo(combo, "Red.TCombobox", "#EF5350")
                    elif val == "چشمک زن زرد":
                        _set_combo(combo, "Yellow.TCombobox", "#FBC02D")
                    else:
                        _set_combo(combo, "White.TCombobox", "#FFFFFF")
            if "pedestrian" in getattr(self, 'blink_vars', {}) and "pedestrian" in getattr(self, 'blink_combos', {}):
                try:
                    w = self.blink_combos["pedestrian"]
                    var = self.blink_vars["pedestrian"][0]
                    val = var.get()
                    # اگر Button باشد (عابر جدید شاسی است)
                    if isinstance(w, tk.Button):
                        if val == "چشمک زن قرمز":
                            w.configure(bg="#EF5350", fg="white", activebackground="#EF5350")
                        elif val == "چشمک زن سبز":
                            w.configure(bg="#66BB6A", fg="black", activebackground="#66BB6A")
                        else:
                            w.configure(bg="#FFFFFF", fg="black", activebackground="#FFFFFF")
                    else:
                        if val == "چشمک زن قرمز":
                            _set_combo(w, "Red.TCombobox", "#EF5350")
                        elif val == "چشمک زن سبز":
                            _set_combo(w, "Green.TCombobox", "#66BB6A")
                        else:
                            _set_combo(w, "White.TCombobox", "#FFFFFF")
                except Exception:
                    pass
        except Exception:
            pass

    def _apply_part_settings_colors(self):
        def _set_combo(combo, style_name, field_bg):
            try:
                combo.configure(style=style_name)
                style = __import__('tkinter').ttk.Style(combo)
                is_dark = style_name == "DarkGreen.TCombobox" or field_bg in ("#2E7D32", "#EF5350")
                fg = "white" if is_dark else "black"
                style.map(style_name, fieldbackground=[("readonly", field_bg), ("!readonly", field_bg)],
                          background=[("readonly", field_bg)], foreground=[("readonly", fg)])
                try:
                    combo.tk.call(combo._w, "configure", "-fieldbackground", field_bg)
                except Exception:
                    pass
            except Exception:
                pass
        try:
            for part in range(1, 9):
                for phase in range(1, 9):
                    if part not in self.part_settings_combos or phase not in self.part_settings_combos[part]:
                        continue
                    combo, var, _addr = self.part_settings_combos[part][phase]
                    val = var.get()
                    if val == "خودرو":
                        _set_combo(combo, "LightGreen.TCombobox", "#A5D6A7")
                    elif val == "چشمک زن زرد":
                        _set_combo(combo, "Yellow.TCombobox", "#FBC02D")
                    elif val == "چشمک زن قرمز":
                        _set_combo(combo, "Red.TCombobox", "#EF5350")
                    elif val == "عابر پیاده":
                        _set_combo(combo, "DarkGreen.TCombobox", "#2E7D32")
                    else:
                        _set_combo(combo, "White.TCombobox", "#FFFFFF")
        except Exception:
            pass

    def _apply_loop_settings_colors(self):
        try:
            for phase in range(1, 9):
                for loop in range(1, 17):
                    if phase not in self.loop_combos or loop not in self.loop_combos[phase]:
                        continue
                    btn, var, _addr = self.loop_combos[phase][loop]
                    if var.get() == "فعال":
                        btn.configure(bg="#66BB6A", fg="black", activebackground="#4CAF50")
                    else:
                        btn.configure(bg="#EF5350", fg="white", activebackground="#E53935")
        except Exception:
            pass

    def _toggle_loop_btn(self, phase, loop):
        try:
            if phase not in self.loop_combos or loop not in self.loop_combos[phase]:
                return
            btn, var, _addr = self.loop_combos[phase][loop]
            var.set("فعال" if var.get() == "غیر فعال" else "غیر فعال")
            # رنگ فوری برای حس شاسی
            try:
                if var.get() == "فعال":
                    btn.configure(bg="#66BB6A", fg="black", activebackground="#4CAF50")
                else:
                    btn.configure(bg="#EF5350", fg="white", activebackground="#E53935")
            except Exception: pass
            self._on_loop_setting_change(phase, loop, var)
        except Exception: pass

    def _card(self, parent, **kw):
        kw.setdefault("bg", Theme.BG_CARD)
        kw.setdefault("highlightbackground", Theme.BORDER)
        kw.setdefault("highlightthickness", 1)
        kw.setdefault("bd", 0)
        return tk.Frame(parent, **kw)

    def _flat_btn(self, parent, text, bg=Theme.BG_PRIMARY, fg="white", command=None, **kw):
        kw.setdefault("activebackground", Theme.BG_PRIMARY_DARK)
        kw.setdefault("activeforeground", "white")
        kw.setdefault("bd", 0)
        kw.setdefault("relief", "flat")
        kw.setdefault("cursor", "hand2")
        kw.setdefault("font", (Theme.FONT, 10, "bold"))
        kw.setdefault("padx", 14)
        kw.setdefault("pady", 7)
        btn = tk.Button(parent, text=text, bg=bg, fg=fg, command=command, **kw)
        _orig, _hover = bg, Theme.BG_PRIMARY_DARK if bg not in (Theme.DANGER, Theme.SUCCESS, Theme.WARNING) else bg
        # هاور بسیار ملایم — فقط برای primary
        if bg == Theme.BG_PRIMARY:
            btn.bind("<Enter>", lambda e, b=btn: b.configure(bg=Theme.BG_PRIMARY_DARK))
            btn.bind("<Leave>", lambda e, b=btn, o=_orig: b.configure(bg=o))
        return btn
        
    def setup_ui(self):
        self.login_frame = tk.Frame(self.window, bg=Theme.BG)
        self.login_frame.pack(fill="both", expand=True)
        
        add_frame = tk.LabelFrame(self.login_frame, text=" افزودن تقاطع جدید", 
                                  bg=Theme.BG_SURFACE, font=("Arial", 12, "bold"), padx=10, pady=10)
        add_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(add_frame, text="نام:", bg=Theme.BG_SURFACE, font=("Arial", 10)).pack(side="right", padx=5)
        self.new_name_entry = tk.Entry(add_frame, width=15, font=("Arial", 10), justify="center")
        self.new_name_entry.pack(side="right", padx=5)
        
        tk.Label(add_frame, text="IP:", bg=Theme.BG_SURFACE, font=("Arial", 10)).pack(side="right", padx=5)
        self.new_ip_entry = tk.Entry(add_frame, width=15, font=("Arial", 10), justify="center")
        self.new_ip_entry.pack(side="right", padx=5)
        self.new_ip_entry.insert(0, "192.168.1.")
        
        tk.Label(add_frame, text="Port:", bg=Theme.BG_SURFACE, font=("Arial", 10)).pack(side="right", padx=5)
        self.new_port_entry = tk.Entry(add_frame, width=8, font=("Arial", 10), justify="center")
        self.new_port_entry.pack(side="right", padx=5)
        self.new_port_entry.insert(0, "502")
        
        tk.Label(add_frame, text="توضیحات:", bg=Theme.BG_SURFACE, font=("Arial", 10)).pack(side="right", padx=5)
        self.new_desc_entry = tk.Entry(add_frame, width=30, font=("Arial", 10), justify="center")
        self.new_desc_entry.pack(side="right", padx=5)
        
        add_btn = tk.Button(add_frame, text="✓ ثبت تقاطع", command=self.add_intersection,
                           bg="green", fg="white", font=("Arial", 10, "bold"), width=15)
        add_btn.pack(side="right", padx=10)
        
        select_frame = tk.Frame(self.login_frame, bg=Theme.BG_SURFACE, pady=10)
        select_frame.pack(fill="x", padx=10)
        
        tk.Label(select_frame, text="نام تقاطع:", bg=Theme.BG_SURFACE, font=("Arial", 11, "bold")).pack(side="right", padx=10)
        self.name_var = tk.StringVar()
        self.name_combo = ttk.Combobox(select_frame, textvariable=self.name_var, width=20, state="readonly", justify="center")
        self.name_combo.pack(side="right", padx=5)
        self.name_combo.bind("<<ComboboxSelected>>", self.on_name_selected)
        
        tk.Label(select_frame, text="IP:", bg=Theme.BG_SURFACE, font=("Arial", 11, "bold")).pack(side="right", padx=10)
        self.ip_entry = tk.Entry(select_frame, width=15, state="readonly", font=("Arial", 11), justify="center")
        self.ip_entry.pack(side="right", padx=5)
        
        tk.Label(select_frame, text="Port:", bg=Theme.BG_SURFACE, font=("Arial", 11, "bold")).pack(side="right", padx=10)
        self.port_entry = tk.Entry(select_frame, width=8, state="readonly", font=("Arial", 11), justify="center")
        self.port_entry.pack(side="right", padx=5)
        
        self.connect_btn = tk.Button(select_frame, text="اتصال به PLC", command=self.toggle_connection,
                                     bg="green", fg="white", font=("Arial", 11, "bold"), width=15)
        self.connect_btn.pack(side="right", padx=10)
        
        del_btn = tk.Button(select_frame, text="🗑️ حذف", command=self.delete_intersection,
                           bg="red", fg="white", font=("Arial", 11, "bold"), width=10)
        del_btn.pack(side="right", padx=10)

        self.bulk_ip_btn = tk.Button(select_frame, text="⚙ تنظیم IP گروهی", command=self._on_bulk_ip_click,
                                     bg="#37474F", fg="white", font=("Arial", 10, "bold"), width=16)
        self.bulk_ip_btn.pack(side="right", padx=10)

        self.status_label = tk.Label(select_frame, text="وضعیت: قطع", bg=Theme.BG_SURFACE,
                                     font=("Arial", 11), fg="gray")
        self.status_label.pack(side="right", padx=20)

        self.table_frame = tk.Frame(self.login_frame, bg=Theme.BG)
        table_frame = self.table_frame
        table_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        columns = ("name", "ip", "port", "desc", "status")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20)
        
        self.tree.heading("name", text="نام تقاطع")
        self.tree.heading("ip", text="IP")
        self.tree.heading("port", text="Port")
        self.tree.heading("desc", text="توضیحات")
        self.tree.heading("status", text="وضعیت")
        
        self.tree.column("name", width=150, anchor="center")
        self.tree.column("ip", width=130, anchor="center")
        self.tree.column("port", width=80, anchor="center")
        self.tree.column("desc", width=250, anchor="center")
        self.tree.column("status", width=120, anchor="center")
        
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_click)

        # ── پنل تنظیم IP گروهی (رمزدار) ──
        self.bulk_ip_frame = tk.Frame(self.login_frame, bg="#263238", bd=1, relief="groove")
        # header
        bulk_head = tk.Frame(self.bulk_ip_frame, bg="#263238")
        bulk_head.pack(fill="x", padx=8, pady=6)
        tk.Label(bulk_head, text="تنظیم IP گروهی — همه PLCها", bg="#263238", fg="white",
                 font=("Arial", 12, "bold")).pack(side="right")
        self.bulk_ping_status = tk.Label(bulk_head, text="", bg="#263238", fg="#B0BEC5", font=("Arial", 9))
        self.bulk_ping_status.pack(side="right", padx=12)
        tk.Button(bulk_head, text="↻ پینگ همه", bg="#455A64", fg="white", font=("Arial", 9, "bold"),
                  command=self._ping_all_bulk).pack(side="left", padx=4)
        tk.Button(bulk_head, text="📥 اکسل همه", bg="#2E7D32", fg="white", font=("Arial", 9, "bold"),
                  command=self._export_all_bulk_excel).pack(side="left", padx=4)
        tk.Button(bulk_head, text="✕ بستن", bg="#455A64", fg="white", font=("Arial", 9, "bold"),
                  command=lambda: self.bulk_ip_frame.pack_forget()).pack(side="left", padx=4)
        # scrollable list
        bulk_canvas = tk.Canvas(self.bulk_ip_frame, bg="#263238", highlightthickness=0, height=260)
        bulk_vsb = ttk.Scrollbar(self.bulk_ip_frame, orient="vertical", command=bulk_canvas.yview)
        bulk_canvas.configure(yscrollcommand=bulk_vsb.set)
        self.bulk_list_frame = tk.Frame(bulk_canvas, bg="#263238")
        bulk_canvas.create_window((0,0), window=self.bulk_list_frame, anchor="nw")
        self.bulk_list_frame.bind("<Configure>", lambda e, c=bulk_canvas: c.configure(scrollregion=c.bbox("all")))
        bulk_canvas.pack(side="left", fill="both", expand=True, padx=(8,0), pady=4)
        bulk_vsb.pack(side="right", fill="y", pady=4)
        self._bulk_canvas = bulk_canvas
        # header row for list
        hdr = tk.Frame(self.bulk_list_frame, bg="#37474F")
        hdr.grid(row=0, column=0, columnspan=8, sticky="ew", padx=2, pady=2)
        for ci, txt in enumerate(["تقاطع", "IP فعلی", "وضعیت", "IP جدید", "Netmask", "Gateway", "", ""]):
            tk.Label(hdr, text=txt, bg="#37474F", fg="white", font=("Arial", 8, "bold"), width=10 if ci>2 else 14).grid(row=0, column=ci, padx=1, pady=2)

        self.control_frame = tk.Frame(self.window, bg=Theme.BG)
        
        self.sidebar = tk.Frame(self.control_frame, bg=Theme.BG_SIDEBAR, width=200)
        self.sidebar.pack(side="right", fill="y")
        self.sidebar.pack_propagate(False)
        
        back_btn = tk.Button(self.sidebar, text="↩ بازگشت", command=self.go_back,
                            bg="#f44336", fg="white", font=("Arial", 12, "bold"), height=2)
        back_btn.pack(fill="x", pady=10, padx=10)

        new_win_btn = tk.Button(self.sidebar, text="◫ باز کردن تقاطع دیگر", bg="#607D8B", fg="white",
                                font=("Arial", 10, "bold"), height=2, command=self.open_another_intersection)
        new_win_btn.pack(fill="x", pady=6, padx=10)
        try:
            from tkinter import TclError as _Tcl
            new_win_btn.bind("<Enter>", lambda e: new_win_btn.configure(bg="#455A64"))
            new_win_btn.bind("<Leave>", lambda e: new_win_btn.configure(bg="#607D8B"))
        except Exception:
            pass

        tk.Label(self.sidebar, text="منوی تنظیمات", bg=Theme.BG_SIDEBAR, fg="white",
                font=("Arial", 14, "bold")).pack(pady=10)
        
        self.option_buttons = []
        options = [
            ("صفحه اصلی", "#2196F3"),
            ("زمان‌بندی", "#4CAF50"),
            ("تنظیمات چشمک زن", "#FF9800"),
            ("تنظیم پارت ها", "#9C27B0"),
            ("تنظیم لوپ ها", "#00BCD4"),
            ("وضعیت لوپ ها", "#E91E63"),
            ("تنظیم IP و زمان", "#795548"),
            ("تست لامپ ها", "#FF5722"),
        ]
        
        for i, (text, color) in enumerate(options):
            btn = tk.Button(self.sidebar, text=text, bg=color, fg="white",
                           font=("Arial", 11, "bold"), height=2,
                           command=lambda idx=i: self.show_page(idx))
            btn.pack(fill="x", pady=3, padx=10)
            self.option_buttons.append(btn)

        # — اطلاعات تقاطع متصل — زیر منوی تنظیمات (درخواست کاربر) — راست‌چین
        self.sidebar_info_card = tk.Frame(self.sidebar, bg="#1E3A5F", bd=1, relief="groove")
        self.sidebar_info_card.pack(side="bottom", fill="x", padx=10, pady=10, ipady=6, ipadx=6)
        tk.Label(self.sidebar_info_card, text="تقاطع متصل", bg="#1E3A5F", fg="#93C5FD",
                font=("Arial", 9, "bold"), anchor="e", justify="right").pack(fill="x", anchor="e")
        self.sidebar_conn_name = tk.Label(self.sidebar_info_card, text="—", bg="#1E3A5F", fg="white",
                                          font=("Arial", 10, "bold"), anchor="e", justify="right", wraplength=175)
        self.sidebar_conn_name.pack(fill="x", pady=(4, 1))
        self.sidebar_conn_ip = tk.Label(self.sidebar_info_card, text="—", bg="#1E3A5F", fg="#BFDBFE",
                                        font=("Consolas", 9), anchor="e", justify="right")
        self.sidebar_conn_ip.pack(fill="x")

        self.content_frame = tk.Frame(self.control_frame, bg=Theme.BG)
        self.content_frame.pack(side="right", fill="both", expand=True)
        
        self.pages = {}
        self.build_main_page()
    
    def build_main_page(self):
        page = tk.Frame(self.content_frame, bg=Theme.BG)
        
        header_frame = tk.Frame(page, bg=Theme.BG, height=60)
        header_frame.pack(fill="x", padx=10, pady=5)
        header_frame.pack_propagate(False)
        
        self.reset_card_btn = tk.Button(header_frame, text="خطر: ریست کارت چراغ ها",
                                        bg="darkred", fg="white", font=("Arial", 11, "bold"),
                                        command=self.reset_light_card)
        self.reset_card_btn.pack(side="right", padx=10, pady=10)

        tk.Label(header_frame, text="تعداد فاز", bg=Theme.BG,
                font=("Arial", 12, "bold")).pack(side="right", padx=10)
        self.phase_count_display = tk.Label(header_frame, text="2", bg="#FF69B4", fg="white",
                                            font=("Arial", 18, "bold"), width=3)
        self.phase_count_display.pack(side="right", padx=5)
        
        phase_table_frame = tk.Frame(page, bg=Theme.BG_TABLE_HEAD)
        phase_table_frame.pack(fill="x", padx=10, pady=5)
        
        self.phase_light_canvases = {}
        self.phase_entries = {}
        
        all_rows = [
            ("green",  "سبز",         "#00FF00", True),
            ("yellow", "زرد",         "#FFFF00", True),
            ("red",    "قرمز",        "#FF0000", False),
            ("all_red","ALL RED",     "#FF1493", True),
            ("min",    "سبز Min هوشمند", "#90EE90", True),
            ("max",    "سبز Max هوشمند", "#90EE90", True),
        ]
        
        self.mode_label_table = tk.Label(phase_table_frame, text="نرمال", bg=Theme.BG,
                                         fg="black", font=("Arial", 10, "bold"), width=12)
        self.mode_label_table.grid(row=4, column=0, padx=2, pady=1)

        for r, (key, name, color, editable) in enumerate(all_rows):
            tk.Label(phase_table_frame, text=name, bg=color, fg="black",
                    font=("Arial", 9, "bold"), width=12).grid(row=r+2, column=0, padx=2, pady=1)
        
        for col in range(8):
            phase_num = col + 1
            grid_col = col + 1
            
            light_canvas = tk.Canvas(phase_table_frame, width=30, height=60, bg=Theme.BG_TABLE_HEAD, highlightthickness=0)
            light_canvas.grid(row=0, column=grid_col, padx=2, pady=2)
            red = light_canvas.create_oval(5, 2, 25, 20, fill="#550000", outline="black")
            yellow = light_canvas.create_oval(5, 21, 25, 39, fill="#555500", outline="black")
            green = light_canvas.create_oval(5, 40, 25, 58, fill="#005500", outline="black")
            
            self.phase_light_canvases[phase_num] = {
                "canvas": light_canvas, "red": red, "yellow": yellow, "green": green
            }
            
            tk.Label(phase_table_frame, text=f"فاز {phase_num}", bg=Theme.BG,
                    font=("Arial", 12, "bold")).grid(row=1, column=grid_col, padx=2, pady=2)
            
            for r, (key, name, color, editable) in enumerate(all_rows):
                cell_frame = tk.Frame(phase_table_frame, bg=Theme.BG_TABLE_HEAD)
                cell_frame.grid(row=r+2, column=grid_col, padx=1, pady=1)
                
                address = self.PHASE_ADDRESSES[key][col]
                
                if editable:
                    e = tk.Entry(cell_frame, width=6, font=("Arial", 9, "bold"), justify="center", bg=color, fg="black",
                                 readonlybackground=color, bd=1,
                                 highlightthickness=1, highlightbackground="#AAAAAA",
                                 highlightcolor=Theme.BG_PRIMARY, insertbackground="black")
                    e.pack(side="right", padx=1, fill="x", expand=True)
                    e.insert(0, "0")
                    e.bind("<FocusIn>", lambda event, ent=e: self._on_phase_entry_focus_in(ent))
                    e.bind("<FocusOut>", lambda event, ent=e, addr=address, row=key: self._on_phase_entry_focus_out(ent, addr, row))
                    e.bind("<Return>", lambda event, ent=e, addr=address, row=key: self._on_phase_entry_submit(ent, addr, row))
                    e.bind("<Escape>", lambda event, ent=e: self.window.focus_set())
                    self.phase_entries[(key, phase_num)] = {
                        "entry": e,
                        "readonly": e,
                        "editable": e,
                        "address": address,
                        "color": color,
                        "is_editable": True
                    }
                else:
                    e_readonly = tk.Entry(cell_frame, width=6, font=("Arial", 9, "bold"), justify="center", bg=color, fg="black",
                                          state="readonly", readonlybackground=color)
                    e_readonly.pack(side="right", padx=1, fill="x", expand=True)
                    e_readonly.insert(0, "0")
                    
                    self.phase_entries[(key, phase_num)] = {
                        "entry": e_readonly,
                        "readonly": e_readonly,
                        "editable": None,
                        "address": address,
                        "color": color,
                        "is_editable": False
                    }
        
        main_content = tk.Frame(page, bg=Theme.BG)
        main_content.pack(fill="both", expand=True, padx=10, pady=5)
        
        map_frame = tk.Frame(main_content, bg=Theme.BG)
        map_frame.pack(side="right", fill="both", expand=True)
        
        self.traffic_canvas = tk.Canvas(map_frame, width=700, height=500, bg="#90EE90", 
                                        highlightthickness=2, highlightbackground="#333")
        self.traffic_canvas.pack(pady=5)
        
        left_panel = tk.Frame(main_content, bg=Theme.BG, width=220)
        left_panel.pack(side="right", fill="y", padx=5)
        left_panel.pack_propagate(False)
        
        self.day_label = tk.Label(left_panel, text="چهارشنبه", bg="#FF69B4", fg="white",
                                  font=("Arial", 13, "bold"))
        self.day_label.pack(fill="x", pady=5)
        
        tk.Label(left_panel, text="ساعت", bg=Theme.BG, font=("Arial", 12, "bold")).pack()
        self.time_big_label = tk.Label(left_panel, text="--:--:--", bg="#FF8C00", fg="white",
                                       font=("Arial", 24, "bold"))
        self.time_big_label.pack(pady=5)
        
        tk.Label(left_panel, text="تاریخ شمسی", bg=Theme.BG, font=("Arial", 11, "bold")).pack()
        self.shamsi_big_label = tk.Label(left_panel, text="----/--/--", bg=Theme.BG, fg="#006400",
                                         font=("Arial", 16, "bold"))
        self.shamsi_big_label.pack(pady=2)
        
        tk.Label(left_panel, text="تاریخ میلادی", bg=Theme.BG, font=("Arial", 11, "bold")).pack()
        self.miladi_big_label = tk.Label(left_panel, text="----/--/--", bg=Theme.BG, fg="#00008B",
                                         font=("Arial", 14, "bold"))
        self.miladi_big_label.pack(pady=2)
        
        # لیبل‌های آبی 3 و 4 حذف شد (درخواست کاربر)
        
        settings_frame = tk.Frame(left_panel, bg=Theme.BG, relief="groove", bd=2)
        settings_frame.pack(fill="x", pady=10, padx=5)
        
        row1 = tk.Frame(settings_frame, bg=Theme.BG)
        row1.pack(fill="x", pady=5, padx=5)
        
        tk.Label(row1, text="سنسورها:", bg=Theme.BG, font=("Arial", 9, "bold"), width=10, anchor="w").pack(side="right", padx=2)
        self.sensors_var = tk.StringVar(value="غیر فعال")
        self.sensors_combo = ttk.Combobox(row1, textvariable=self.sensors_var,
                                          values=["غیر فعال", "فعال"],
                                          state="readonly", width=12, justify="center")
        self.sensors_combo.pack(side="right", padx=2)
        self.sensors_combo.bind("<<ComboboxSelected>>", lambda e: self._on_settings_change("sensors"))
        self.sensors_combo.bind("<<ComboboxSelected>>", lambda e: self.window.after(60, lambda: (self.sensors_combo.selection_clear(), self.window.focus_set())), add="+")
        
        row2 = tk.Frame(settings_frame, bg=Theme.BG)
        row2.pack(fill="x", pady=5, padx=5)
        
        tk.Label(row2, text="زمان سبزها:", bg=Theme.BG, font=("Arial", 9, "bold"), width=10, anchor="w").pack(side="right", padx=2)
        self.green_time_var = tk.StringVar(value="اتوماتیک")
        self.green_time_combo = ttk.Combobox(row2, textvariable=self.green_time_var,
                                             values=["اتوماتیک", "دستی"],
                                             state="readonly", width=12, justify="center")
        self.green_time_combo.pack(side="right", padx=2)
        self.green_time_combo.bind("<<ComboboxSelected>>", lambda e: self._on_settings_change("green_time"))
        self.green_time_combo.bind("<<ComboboxSelected>>", lambda e: self.window.after(60, lambda: (self.green_time_combo.selection_clear(), self.window.focus_set())), add="+")
        
        row3 = tk.Frame(settings_frame, bg=Theme.BG)
        row3.pack(fill="x", pady=5, padx=5)
        
        tk.Label(row3, text="کنترل:", bg=Theme.BG, font=("Arial", 9, "bold"), width=10, anchor="w").pack(side="right", padx=2)
        self.control_var = tk.StringVar(value="اتوماتیک")
        self.control_combo = ttk.Combobox(row3, textvariable=self.control_var,
                                          values=["اتوماتیک", "پلیس", "دائمی فلش"],
                                          state="readonly", width=12, justify="center")
        self.control_combo.pack(side="right", padx=2)
        self.control_combo.bind("<<ComboboxSelected>>", lambda e: (self._on_settings_change("control_mode"), self._apply_main_settings_colors(), self.window.after(60, lambda: (self.control_combo.selection_clear(), self.window.focus_set()))))
        try:
            self.window.after(400, self._apply_main_settings_colors)
        except Exception:
            pass
        # همچنین تغییر انتخاب هم رنگ را عوض کند
        self.sensors_combo.bind("<<ComboboxSelected>>", lambda e: self.window.after(30, self._apply_main_settings_colors), add="+")
        self.green_time_combo.bind("<<ComboboxSelected>>", lambda e: self.window.after(30, self._apply_main_settings_colors), add="+")
        self.control_combo.bind("<<ComboboxSelected>>", lambda e: self.window.after(30, self._apply_main_settings_colors), add="+")
        
        self.settings_status = tk.Label(settings_frame, text="", bg=Theme.BG,
                                        font=("Arial", 9), fg="gray")
        self.settings_status.pack(pady=5)

        # — فاز بعد — کنار فیلد حالت (تعداد فاز به هدر برگشت)
        phase_row = tk.Frame(settings_frame, bg=Theme.BG)
        phase_row.pack(fill="x", pady=6, padx=5)
        self.next_phase_btn = tk.Button(phase_row, text="➡ فاز بعد",
                                        bg="#FF9800", fg="white", font=("Arial", 9, "bold"),
                                        command=self.next_phase, width=12)
        self.next_phase_btn.pack(fill="x", pady=2)
        self.next_phase_btn.pack_forget()
        
        bottom_route = tk.Frame(page, bg=Theme.BG)
        bottom_route.pack(fill="x", padx=10)
        
        tk.Label(bottom_route, text="6", bg=Theme.BG, font=("Arial", 14, "bold"), width=3).pack(side="right", padx=5)
        tk.Label(bottom_route, text="6", bg="#0000CD", fg="white", font=("Arial", 12, "bold"), width=15).pack(side="right", padx=2)
        tk.Label(bottom_route, text="5", bg="#0000CD", fg="white", font=("Arial", 12, "bold"), width=15).pack(side="right", padx=2)
        tk.Label(bottom_route, text="5", bg=Theme.BG, font=("Arial", 14, "bold"), width=3).pack(side="right", padx=5)
        
        self.pages[0] = page
        self.draw_intersection_map()
    
    def draw_intersection_map(self):
        canvas = self.traffic_canvas
        canvas.delete("all")

        W, H = 700, 500

        # ── پالت مطابق عکس: کاغذ روشن، آسفالت تیره مایل به زرشکی، پیاده‌رو طوسی روشن ──
        PAPER   = "#7EC87E"
        SIDEWALK= "#D8D2C4"
        ROAD    = "#404040"
        CURB    = "#B8B0A0"

        canvas.create_rectangle(0, 0, W, H, fill=PAPER, outline="")

        # پیاده‌رو / حاشیه اطراف خیابان
        canvas.create_rectangle(245, 0, 455, H, fill=SIDEWALK, outline="")
        canvas.create_rectangle(0, 145, W, 355, fill=SIDEWALK, outline="")
        # گرد کردن گوشه‌های تقاطع (شعاع ~18)
        for cx, cy in [(245, 145), (455, 145), (245, 355), (455, 355)]:
            canvas.create_oval(cx-18, cy-18, cx+18, cy+18, fill=SIDEWALK, outline=CURB, width=1)

        # آسفالت
        canvas.create_rectangle(260, 0, 440, H, fill=ROAD, outline="")
        canvas.create_rectangle(0, 160, W, 340, fill=ROAD, outline="")

        # خط‌کشی طولی (سفید) — هر خیابان 2 لاین رفت/برگشت + خط وسط
        for y in range(0, 160, 25):
            canvas.create_line(350, y, 350, y+12, fill="white", width=3)
        for y in range(340, H, 25):
            canvas.create_line(350, y, 350, y+12, fill="white", width=3)
        for x in range(0, 280, 25):
            canvas.create_line(x, 250, x+12, 250, fill="white", width=3)
        for x in range(420, W, 25):
            canvas.create_line(x, 250, x+12, 250, fill="white", width=3)
        # خط ممتد جداکننده لاین‌های هم‌جهت (ظریف)
        canvas.create_line(335, 0, 335, 145, fill="white", width=1)
        canvas.create_line(365, 0, 365, 145, fill="white", width=1)
        canvas.create_line(335, 355, 335, H, fill="white", width=1)
        canvas.create_line(365, 355, 365, H, fill="white", width=1)
        canvas.create_line(0, 235, 245, 235, fill="white", width=1)
        canvas.create_line(0, 265, 245, 265, fill="white", width=1)
        canvas.create_line(455, 235, W, 235, fill="white", width=1)
        canvas.create_line(455, 265, W, 265, fill="white", width=1)

        # خط عابر (زبرا) — 8 نوار ضخیم هر سمت، عین عکس
        for i in range(0, 180, 15):
            canvas.create_line(260+i, 160, 260+i+7, 160, fill="white", width=8)
            canvas.create_line(260+i, 340, 260+i+7, 340, fill="white", width=8)
        for i in range(0, 180, 15):
            canvas.create_line(260, 160+i, 260, 160+i+7, fill="white", width=8)
            canvas.create_line(440, 160+i, 440, 160+i+7, fill="white", width=8)
        # خط ایست ضخیم پشت زبرا
        canvas.create_line(260, 152, 440, 152, fill="white", width=3)
        canvas.create_line(260, 348, 440, 348, fill="white", width=3)
        canvas.create_line(252, 160, 252, 340, fill="white", width=3)
        canvas.create_line(448, 160, 448, 340, fill="white", width=3)

        # جزیره گوشه (مثلثی کوچک) — 4 گوشه
        for pts in [
            [(245, 145), (260, 145), (245, 160)],
            [(455, 145), (440, 145), (455, 160)],
            [(245, 355), (260, 355), (245, 340)],
            [(455, 355), (440, 355), (455, 340)],
        ]:
            canvas.create_polygon(pts, fill=SIDEWALK, outline=CURB, width=1)

        # وسط هر لاین رفت + قرمز سمت مرکز — هر جفت نزدیک به هم (1-2، 3-4، 5-6، 7-8)
        CX, CY = 350, 250
        # شمال → چپ، غرب → پایین، شرق → بالا (اصلاح کاربر)
        lights_layout = [
            (285, 72,  2, "V"),   # شمال — چپ جاده
            (325, 72,  1, "V"),
            (585, 175, 8, "H"),  # شرق — بالا جاده
            (585, 215, 7, "H"),
            (375, 428, 5, "V"),  # جنوب — 5 و 6 جابجا شد
            (415, 428, 6, "V"),
            (105, 285, 3, "H"),  # غرب — پایین جاده
            (105, 325, 4, "H"),
        ]

        def _is_north(y): return y < CY
        def _is_south(y): return y > CY
        def _is_east(x):  return x > CX
        def _is_west(x):  return x < CX

        self.map_lights = {}
        for x, y, phase_num, orient in lights_layout:
            if orient == "V":
                canvas.create_rectangle(x-14, y-32, x+14, y+32, fill="#1a1a1a", outline="#555", width=2)
                # شمال: red پایین (نزدیک مرکز)، جنوب: red بالا
                if _is_north(y):
                    green  = canvas.create_oval(x-10, y-28, x+10, y-10, fill="#003300", outline="black", width=2)
                    yellow = canvas.create_oval(x-10, y-8,  x+10, y+8,  fill="#333300", outline="black", width=2)
                    red    = canvas.create_oval(x-10, y+10, x+10, y+28, fill="#330000", outline="black", width=2)
                else:  # جنوب
                    red    = canvas.create_oval(x-10, y-28, x+10, y-10, fill="#330000", outline="black", width=2)
                    yellow = canvas.create_oval(x-10, y-8,  x+10, y+8,  fill="#333300", outline="black", width=2)
                    green  = canvas.create_oval(x-10, y+10, x+10, y+28, fill="#003300", outline="black", width=2)
            else:
                canvas.create_rectangle(x-32, y-14, x+32, y+14, fill="#1a1a1a", outline="#555", width=2)
                if _is_east(x):
                    red    = canvas.create_oval(x-28, y-10, x-10, y+10, fill="#330000", outline="black", width=2)
                    yellow = canvas.create_oval(x-8,  y-10, x+8,  y+10, fill="#333300", outline="black", width=2)
                    green  = canvas.create_oval(x+10, y-10, x+28, y+10, fill="#003300", outline="black", width=2)
                else:  # غرب
                    green  = canvas.create_oval(x-28, y-10, x-10, y+10, fill="#003300", outline="black", width=2)
                    yellow = canvas.create_oval(x-8,  y-10, x+8,  y+10, fill="#333300", outline="black", width=2)
                    red    = canvas.create_oval(x+10, y-10, x+28, y+10, fill="#330000", outline="black", width=2)

            self.map_lights[phase_num] = {"red": red, "yellow": yellow, "green": green, "x": x, "y": y, "orient": orient}

        canvas.create_line(285, 100, 285, 145, fill="white", width=4, arrow=tk.LAST)
        canvas.create_line(325, 100, 325, 145, fill="white", width=4, arrow=tk.LAST)
        canvas.create_line(375, 400, 375, 355, fill="white", width=4, arrow=tk.LAST)
        canvas.create_line(415, 400, 415, 355, fill="white", width=4, arrow=tk.LAST)
        canvas.create_line(560, 175, 455, 175, fill="white", width=4, arrow=tk.LAST)
        canvas.create_line(560, 215, 455, 215, fill="white", width=4, arrow=tk.LAST)
        canvas.create_line(140, 285, 245, 285, fill="white", width=4, arrow=tk.LAST)
        canvas.create_line(140, 325, 245, 325, fill="white", width=4, arrow=tk.LAST)
    
    def next_phase(self):
        if not self.is_connected:
            return
        
        def _send():
            try:
                with self.plc_lock:
                    self.client.write_coil(address=2096, value=True, device_id=1)
                time.sleep(0.5)
                with self.plc_lock:
                    self.client.write_coil(address=2096, value=False, device_id=1)
            except Exception as e:
                logging.warning(f"خطا در فاز بعد: {e}")
                self._handle_connection_error()
        
        threading.Thread(target=_send, daemon=True).start()
    
    def start_keep_alive(self):
        def _keep_alive_loop():
            while self.keep_alive_running and self.is_connected:
                try:
                    if self.client:
                        with self.plc_lock:
                            self.client.write_coil(address=2100, value=True, device_id=1)
                        time.sleep(0.5)
                        with self.plc_lock:
                            self.client.write_coil(address=2100, value=False, device_id=1)
                except Exception as e:
                    logging.warning(f"خطا در keep-alive: {e}")
                    self._handle_connection_error()
                    break
                time.sleep(10)
        
        self.keep_alive_running = True
        threading.Thread(target=_keep_alive_loop, daemon=True).start()
    
    def stop_keep_alive(self):
        self.keep_alive_running = False
        self._stop_police_alive()

    def _start_police_alive(self):
        if self.police_alive_running:
            return
        self.police_alive_running = True
        def _loop():
            while self.police_alive_running and self.is_connected and self.client:
                try:
                    # فقط وقتی پلیس است پالس بفرست
                    is_police = False
                    try:
                        is_police = self.control_var.get() == "\u067e\u0644\u06cc\u0633"
                    except Exception:
                        pass
                    if is_police:
                        with self.plc_lock:
                            self.client.write_coil(address=self.POLICE_ALIVE_COIL, value=True, device_id=1)
                        import time as _t
                        _t.sleep(0.2)
                        try:
                            with self.plc_lock:
                                self.client.write_coil(address=self.POLICE_ALIVE_COIL, value=False, device_id=1)
                        except Exception:
                            pass
                except Exception:
                    try:
                        self._handle_connection_error()
                    except Exception:
                        pass
                    break
                import time as _t2
                _t2.sleep(5)
            self.police_alive_running = False
        import threading as _th
        _th.Thread(target=_loop, daemon=True).start()

    def _stop_police_alive(self):
        self.police_alive_running = False

    def _police_alive_pulse_once(self):
        if not self.is_connected or not self.client:
            return
        try:
            with self.plc_lock:
                self.client.write_coil(address=self.POLICE_ALIVE_COIL, value=True, device_id=1)
            import time as _t
            _t.sleep(0.2)
            with self.plc_lock:
                self.client.write_coil(address=self.POLICE_ALIVE_COIL, value=False, device_id=1)
        except Exception:
            pass
    
    def start_phase_count_update(self):
        if not self.phase_count_update_running:
            self.phase_count_update_running = True
            self._phase_count_update_loop()
    
    def stop_phase_count_update(self):
        self.phase_count_update_running = False
    
    def _phase_count_update_loop(self):
        if not self.phase_count_update_running:
            return
        if self.is_connected and self.client and self.selected_option == 0:
            def _update():
                try:
                    result = self._read_register(self.MAIN_PHASE_COUNT_READ_ADDRESS, 1)
                    if not result.isError():
                        new_count = result.registers[0]
                        if new_count != self.phase_count:
                            self.phase_count = new_count
                            self.window.after(0, lambda: self.phase_count_display.configure(text=str(new_count)))
                except:
                    pass
            threading.Thread(target=_update, daemon=True).start()
        self._schedule_after("phase_count", 1000, self._phase_count_update_loop)
    
    def build_timing_page(self):
        page = tk.Frame(self.content_frame, bg=Theme.BG_TABLE_HEAD)
        
        canvas = tk.Canvas(page, bg=Theme.BG_TABLE_HEAD, highlightthickness=0)
        v_scrollbar = ttk.Scrollbar(page, orient="vertical", command=canvas.yview)
        h_scrollbar = ttk.Scrollbar(page, orient="horizontal", command=canvas.xview)
        try:
            h_scrollbar.configure(width=16)
            v_scrollbar.configure(width=16)
        except Exception:
            pass
        canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        scrollable_frame = tk.Frame(canvas, bg=Theme.BG_TABLE_HEAD, width=2500)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        _win = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        try:
            canvas.itemconfigure(_win, width=2500)
        except Exception:
            pass
        self.timing_canvas = canvas
        self.timing_scrollable = scrollable_frame

        # اسکرول با موس: چرخ عمودی و Shift+چرخ افقی
        def _timing_scroll(evt):
            try:
                # Shift نگه داشته = افقی
                if getattr(evt, 'state', 0) & 0x0001:
                    if evt.delta:
                        canvas.xview_scroll(int(-evt.delta/60), "units")
                    elif evt.num == 4:
                        canvas.xview_scroll(-4, "units")
                    elif evt.num == 5:
                        canvas.xview_scroll(4, "units")
                    return "break"
                # عادی = عمودی، افقی آنقدر بزرگ نیست که عمودی مزاحم شود
                if evt.delta:
                    canvas.yview_scroll(int(-evt.delta/120), "units")
                elif evt.num == 4:
                    canvas.yview_scroll(-3, "units")
                elif evt.num == 5:
                    canvas.yview_scroll(3, "units")
            except Exception:
                pass
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>", "<Shift-MouseWheel>", "<Shift-Button-4>", "<Shift-Button-5>"):
            try:
                canvas.bind(seq, _timing_scroll)
                page.bind(seq, _timing_scroll)
                scrollable_frame.bind(seq, _timing_scroll)
            except Exception:
                pass
        # کلیدهای جهت هم افقی/عمودی
        def _timing_keys(evt):
            try:
                if evt.keysym in ("Left", "Right"):
                    canvas.xview_scroll(-4 if evt.keysym == "Left" else 4, "units")
                    return "break"
                if evt.keysym in ("Up", "Down"):
                    canvas.yview_scroll(-3 if evt.keysym == "Up" else 3, "units")
                    return "break"
            except Exception:
                pass
        for seq in ("<Left>", "<Right>", "<Up>", "<Down>", "<Prior>", "<Next>"):
            try:
                canvas.bind(seq, _timing_keys)
                page.bind(seq, _timing_keys)
            except Exception:
                pass
        try:
            canvas.focus_set()
        except Exception:
            pass
        canvas.bind("<Enter>", lambda e: canvas.focus_set())

        # ترتیب pack: اول نوارها بعد کانواس تا دیده شود
        h_scrollbar.pack(side="bottom", fill="x")
        v_scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        
        datetime_frame = tk.Frame(scrollable_frame, bg=Theme.BG_TABLE_HEAD)
        datetime_frame.pack(fill="x", padx=10, pady=10)

        hour_frame = tk.Frame(datetime_frame, bg=Theme.BG_TABLE_HEAD)
        hour_frame.pack(side="left", padx=20)
        
        tk.Label(hour_frame, text="ساعت", bg=Theme.BG_TABLE_HEAD, fg="white",
                font=("Arial", 14, "bold")).pack()
        
        self.timing_min_label = tk.Label(hour_frame, text="--", bg="#FF8C00", fg="white",
                                          font=("Arial", 24, "bold"), width=3)
        self.timing_min_label.pack(side="right", padx=2)
        
        tk.Label(hour_frame, text=":", bg=Theme.BG_TABLE_HEAD, fg="white", font=("Arial", 24, "bold")).pack(side="right")
        
        self.timing_hour_label = tk.Label(hour_frame, text="--", bg="#FF8C00", fg="white",
                                           font=("Arial", 24, "bold"), width=3)
        self.timing_hour_label.pack(side="right", padx=2)
        
        date_frame = tk.Frame(datetime_frame, bg=Theme.BG_TABLE_HEAD)
        date_frame.pack(side="left", padx=20)
        
        tk.Label(date_frame, text="امروز", bg=Theme.BG_TABLE_HEAD, fg="white",
                font=("Arial", 14, "bold")).pack()
        
        self.timing_day_name_label = tk.Label(date_frame, text="------", bg="#FF69B4", fg="white",
                                               font=("Arial", 14, "bold"), width=10)
        self.timing_day_name_label.pack(pady=2)
        
        self.timing_shamsi_date_label = tk.Label(date_frame, text="----/--/--", bg="#FF8C00", fg="white",
                                                  font=("Arial", 16, "bold"))
        self.timing_shamsi_date_label.pack(pady=2)
        
        control_frame = tk.Frame(scrollable_frame, bg=Theme.BG_TABLE_HEAD)
        control_frame.pack(fill="x", padx=10, pady=10)
        
        self.visible_programs_var = tk.IntVar(value=9)
        # تعداد برنامه‌ها چپ — ساعت هم چپ است (درخواست کاربر)
        btn_plus = tk.Button(control_frame, text="➕", bg="#4CAF50", fg="white",
                             font=("Arial", 14, "bold"), width=2,
                             command=self.increase_visible_programs)
        btn_plus.pack(side="left", padx=5)
        tk.Label(control_frame, textvariable=self.visible_programs_var, bg=Theme.BG, fg="black",
                font=("Arial", 16, "bold"), width=3).pack(side="left", padx=5)
        btn_minus = tk.Button(control_frame, text="➖", bg="#f44336", fg="white",
                              font=("Arial", 14, "bold"), width=2,
                              command=self.decrease_visible_programs)
        btn_minus.pack(side="left", padx=5)
        tk.Label(control_frame, text="تعداد برنامه‌های فعال:", bg=Theme.BG_TABLE_HEAD, fg="white",
                font=("Arial", 12, "bold")).pack(side="left", padx=10)
        # ریست کلی حذف شد — هر برنامه دکمه ریست خودش را دارد (درخواست کاربر)
        
        # هدر — هر برنامه فقط یک ردیف + دکمه ریست انتهای ردیف
        header_row = tk.Frame(scrollable_frame, bg=Theme.BG_TABLE_HEAD, highlightbackground="#FF8C00", highlightthickness=1)
        header_row.pack(fill="x", padx=10, pady=(10, 2))
        headers_global = ["برنامه", "وضعیت", "روزها", "حالت", "از", "تا",
                       "سبز1", "سبز2", "سبز3", "سبز4", "سبز5", "سبز6", "سبز7", "سبز8",
                       "فاز1", "فاز2", "فاز3", "فاز4", "فاز5", "فاز6", "فاز7", "فاز8",
                       "جدول پارت", "ریست"]
        # عرض هر ستون هدر دقیقا هم‌اندازه فیلد زیرش — قبل 9/6 بیش از حد عریض بود و هدر می‌لغزید
        header_widths = [7, 7, 32, 7, 8, 8, 4, 4, 4, 4, 4, 4, 4, 4, 7, 7, 7, 7, 7, 7, 7, 7, 5, 7]
        for col_idx, header in enumerate(headers_global):
            w = header_widths[col_idx]
            lbl = tk.Label(header_row, text=header, bg=Theme.BG_TABLE_HEAD, fg="white",
                    font=("Arial", 8, "bold"), width=w, anchor="center")
            # سبزها فشرده‌تر تا روی فیلد 4کاراکتری بیفتد
            px = 0 if 6 <= col_idx <= 13 else 1
            lbl.grid(row=0, column=col_idx, padx=px, pady=2, sticky="nsew")
            header_row.grid_columnconfigure(col_idx, weight=w, minsize=w*7)

        self.timing_programs = {}
        self.program_frames = {}
        
        for prog_idx in range(27):
            base_addr = self.timing_base_addresses[prog_idx]
            
            prog_frame = tk.Frame(scrollable_frame, bg=Theme.BG_TABLE_HEAD, 
                                  highlightbackground="#FF8C00", highlightthickness=1)
            prog_frame.pack(fill="x", padx=10, pady=2)
            
            # یک ردیف افقی: برچسب برنامه + همه فیلدها کنار هم
            row_frame = tk.Frame(prog_frame, bg=Theme.BG_TABLE_HEAD)
            row_frame.pack(fill="x", padx=5, pady=4)

            tk.Label(row_frame, text=f"{prog_idx + 1}", bg="#FF8C00", fg="white",
                    font=("Arial", 9, "bold"), width=7).grid(row=0, column=0, padx=1, pady=1)
            
            self.timing_programs[prog_idx] = {
                "entries": {},
                "vars": {},
                "frame": prog_frame,
                "row_frame": row_frame,
                "base_addr": base_addr
            }
            for c_idx, w in enumerate(header_widths):
                row_frame.grid_columnconfigure(c_idx, weight=w, minsize=w*7)
            
            self._create_timing_program_row(row_frame, prog_idx, base_addr, col_offset=1)
            self.program_frames[prog_idx] = prog_frame
            
            if prog_idx > 8:
                prog_frame.pack_forget()
        
        self.pages[1] = page
    
    def _create_timing_program_row(self, parent, prog_idx, base_addr, col_offset=0):
        prog_data = self.timing_programs[prog_idx]
        
        status_var = tk.StringVar(value="فعال" if prog_idx < 9 else "غیر فعال")
        def _status_colors(val):
            return ("#4CAF50", "white") if val == "فعال" else ("#EF5350", "white")
        bg, fg = _status_colors(status_var.get())
        status_btn = tk.Button(parent, textvariable=status_var, bg=bg, fg=fg,
                               activebackground=bg, activeforeground=fg,
                               font=("Arial", 9, "bold"), width=7, bd=1, relief="raised",
                               cursor="hand2",
                               command=lambda p=prog_idx, v=status_var: self._toggle_timing_status(p, v))
        status_var.trace_add("write", lambda *_a, b=status_btn, v=status_var: b.configure(bg=_status_colors(v.get())[0], fg=_status_colors(v.get())[1], activebackground=_status_colors(v.get())[0]))
        status_btn.grid(row=0, column=col_offset+0, padx=1, pady=1)
        prog_data["vars"]["status"] = (status_var, base_addr + 0)
        prog_data["status_btn"] = status_btn
        
        days_frame = tk.Frame(parent, bg=Theme.BG_TABLE_HEAD)
        days_frame.grid(row=0, column=col_offset+1, padx=1, pady=1)

        # ——— باکس روزها: لیبل‌ها دقیقاً بالای هر روز، و دکمه‌ها با تیک/ضربدر ———
        # ساختار: یک گرید 7 ستونه؛ سطر 0 = نام روز، سطر 1 = دکمهٔ تیک/ضربدر
        days_inner = tk.Frame(days_frame, bg=Theme.BG_TABLE_HEAD)
        days_inner.pack()

        def _make_day_cell(col_idx):
            cell = tk.Frame(days_inner, bg=Theme.BG_TABLE_HEAD)
            cell.grid(row=0, column=6 - col_idx, padx=1, pady=1)

            tk.Label(cell, text=self.day_names[col_idx], bg=Theme.BG_TABLE_HEAD, fg="white",
                     font=("Arial", 7, "bold"), width=4, anchor="center").pack(side="left")

            day_var = tk.BooleanVar(value=(prog_idx == 0 and col_idx == 0))

            btn = tk.Button(cell, width=2, height=1, bd=1, relief="raised",
                            font=("Arial", 8, "bold"), cursor="hand2",
                            command=lambda p=prog_idx, d=col_idx, v=day_var: self._toggle_day(p, d, v))
            # استایل اولیه
            def _refresh_day_btn():
                if day_var.get():
                    btn.configure(text="✓", bg="#4CAF50", fg="white", activebackground="#388E3C")
                else:
                    btn.configure(text="✕", bg="#FFCDD2", fg="#B71C1C", activebackground="#EF9A9A")
            # هر بار مقدار عوض شد، رفرش
            day_var.trace_add("write", lambda *_args, b=btn, v=day_var: _refresh_day_btn())
            _refresh_day_btn()
            btn.pack(side="left", padx=1)

            # کلیک روی کل سلول هم تگگل کند
            cell.bind("<Button-1>", lambda e, p=prog_idx, d=col_idx, v=day_var: self._toggle_day(p, d, v))

            prog_data["vars"][f"day_{col_idx}"] = (day_var, base_addr + 1 + col_idx)
            # نگه‌داشتن رفرش برای بعد از load
            if "day_btns" not in prog_data:
                prog_data["day_btns"] = {}
            prog_data["day_btns"][col_idx] = (btn, day_var)

        for day_col in range(7):
            _make_day_cell(day_col)
        
        mode_var = tk.StringVar(value="زمان ثابت")
        mode_combo = ttk.Combobox(parent, textvariable=mode_var,
                                   values=["زمان ثابت", "هوشمند"],
                                   state="readonly", width=7, justify="center")
        mode_combo.grid(row=0, column=col_offset+2, padx=1, pady=1, sticky="ew")
        mode_combo.bind("<<ComboboxSelected>>", 
                       lambda e, p=prog_idx: self._on_timing_change(p, "mode"))
        prog_data["vars"]["mode"] = (mode_var, base_addr + 31)
        
        from_frame = tk.Frame(parent, bg=Theme.BG_TABLE_HEAD)
        from_frame.grid(row=0, column=col_offset+3, padx=1, pady=1, sticky="ew")
        
        for i, label in reversed(list(enumerate(["H", "M", "S"]))):
            e = tk.Entry(from_frame, width=2, font=("Arial", 8), justify="center", bg=Theme.BG, fg="black")
            e.pack(side="right", padx=1)
            e.insert(0, "0")
            e.bind("<FocusIn>", lambda event, p=prog_idx, f=f"from_{label}": self._on_timing_focus_in(p, f))
            e.bind("<FocusOut>", lambda event, p=prog_idx, f=f"from_{label}": self._on_timing_focus_out(p, f))
            e.bind("<Return>", lambda event, p=prog_idx, f=f"from_{label}": self._on_timing_enter(p, f))
            prog_data["entries"][f"from_{label}"] = (e, base_addr + 8 + i)
        
        to_frame = tk.Frame(parent, bg=Theme.BG_TABLE_HEAD)
        to_frame.grid(row=0, column=col_offset+4, padx=1, pady=1)
        
        for i, label in reversed(list(enumerate(["H", "M", "S"]))):
            e = tk.Entry(to_frame, width=2, font=("Arial", 8), justify="center", bg=Theme.BG, fg="black")
            e.pack(side="right", padx=1)
            e.insert(0, "0")
            e.bind("<FocusIn>", lambda event, p=prog_idx, f=f"to_{label}": self._on_timing_focus_in(p, f))
            e.bind("<FocusOut>", lambda event, p=prog_idx, f=f"to_{label}": self._on_timing_focus_out(p, f))
            e.bind("<Return>", lambda event, p=prog_idx, f=f"to_{label}": self._on_timing_enter(p, f))
            prog_data["entries"][f"to_{label}"] = (e, base_addr + 11 + i)
        
        for phase in range(8):
            e = tk.Entry(parent, width=4, font=("Arial", 8), justify="center", bg="#00FF00", fg="black")
            e.grid(row=0, column=col_offset+5+phase, padx=1, pady=1)
            e.insert(0, "0")
            e.bind("<FocusIn>", lambda event, p=prog_idx, f=f"green_{phase+1}": self._on_timing_focus_in(p, f))
            e.bind("<FocusOut>", lambda event, p=prog_idx, f=f"green_{phase+1}": self._on_timing_focus_out(p, f))
            e.bind("<Return>", lambda event, p=prog_idx, f=f"green_{phase+1}": self._on_timing_enter(p, f))
            prog_data["entries"][f"green_{phase+1}"] = (e, base_addr + 14 + phase)
        
        for phase in range(8):
            phase_var = tk.StringVar(value="------")
            phase_combo = ttk.Combobox(parent, textvariable=phase_var,
                                        values=["------", "زمان ثابت", "ماکزیمم"],
                                        state="readonly", width=7, justify="center")
            phase_combo.grid(row=0, column=col_offset+13+phase, padx=1, pady=1)
            phase_combo.bind("<<ComboboxSelected>>", 
                            lambda e, p=prog_idx, ph=phase: self._on_timing_change(p, f"phase_{ph+1}"))
            prog_data["vars"][f"phase_{phase+1}"] = (phase_var, base_addr + 22 + phase)
        
        part_var = tk.StringVar(value="جدول 1")
        part_combo = ttk.Combobox(parent, textvariable=part_var,
                                   values=["جدول 1", "جدول 2"],
                                   state="readonly", width=5, justify="center")
        part_combo.grid(row=0, column=col_offset+21, padx=1, pady=1)
        part_combo.bind("<<ComboboxSelected>>", 
                       lambda e, p=prog_idx: self._on_timing_change(p, "part"))
        prog_data["vars"]["part"] = (part_var, base_addr + 30)

        reset_btn = tk.Button(parent, text="⚠ ریست", bg="darkred", fg="white",
                              activebackground="#8B0000", activeforeground="white",
                              font=("Arial", 8, "bold"), width=7, bd=1, relief="raised", cursor="hand2",
                              command=lambda p=prog_idx: self._reset_single_timing_program(p))
        reset_btn.grid(row=0, column=col_offset+22, padx=6, pady=1, sticky="ew")
        prog_data["reset_btn"] = reset_btn
    
    def _on_timing_focus_in(self, prog_idx, field_name):
        self.focused_timing_entry = prog_idx
        self.focused_timing_field = field_name
        self.focused_timing_prog = prog_idx
        self.user_is_editing_timing = True
    
    def _on_timing_focus_out(self, prog_idx, field_name):
        self._save_timing_entry(prog_idx, field_name)
    
    def _toggle_timing_status(self, prog_idx, var):
        var.set("غیر فعال" if var.get() == "فعال" else "فعال")
        self._on_timing_change(prog_idx, "status")

    def _toggle_day(self, prog_idx, day_col, var):
        var.set(not var.get())
        self._on_timing_change(prog_idx, f"day_{day_col}")

    def _refresh_day_buttons(self, prog_idx):
        prog_data = self.timing_programs.get(prog_idx)
        if not prog_data or "day_btns" not in prog_data:
            return
        for col, (btn, var) in prog_data["day_btns"].items():
            if var.get():
                btn.configure(text="✓", bg="#4CAF50", fg="white", activebackground="#388E3C")
            else:
                btn.configure(text="✕", bg="#FFCDD2", fg="#B71C1C", activebackground="#EF9A9A")

    def _on_timing_enter(self, prog_idx, field_name):
        self._save_timing_entry(prog_idx, field_name)
        self._move_to_next_field(prog_idx, field_name)
    
    def _save_timing_entry(self, prog_idx, field_name):
        if not self.is_connected or not self.client:
            self.user_is_editing_timing = False
            return
        
        try:
            prog_data = self.timing_programs[prog_idx]
            entry, addr = prog_data["entries"][field_name]
            value_str = entry.get().strip()
            
            if not value_str:
                self.user_is_editing_timing = False
                return
            
            try:
                value = int(value_str)
            except:
                self.user_is_editing_timing = False
                return
            
            if "H" in field_name and value > 23:
                value = 23
                entry.delete(0, "end")
                entry.insert(0, str(value))
            elif ("M" in field_name or "S" in field_name) and value > 59:
                value = 59
                entry.delete(0, "end")
                entry.insert(0, str(value))
            
            try:
                self._timing_pending[(prog_idx, field_name)] = (addr, value)
            except Exception: pass
            self.user_is_editing_timing = True
            if not getattr(self, '_timing_write_scheduled', False):
                self._timing_write_scheduled = True
                def _flush_timing():
                    try:
                        items = dict(self._timing_pending)
                        self._timing_pending = {}
                        self._timing_write_scheduled = False
                        import time as _t2
                        for (pp, ff), (aa, vv) in list(items.items()):
                            try:
                                with self.plc_lock:
                                    r = self.client.write_register(address=aa, value=vv, device_id=1)
                                    if hasattr(r, 'isError') and r.isError():
                                        logging.warning(f"timing write fail {pp}/{ff} @{aa}={vv}")
                                _t2.sleep(0.02)
                            except Exception as e:
                                logging.warning(f"timing batch {pp}/{ff}: {e}")
                        self.window.after(0, lambda: setattr(self, 'user_is_editing_timing', False))
                    except Exception as e:
                        logging.warning(f"timing flush batch: {e}")
                        try: self.window.after(0, lambda: setattr(self, 'user_is_editing_timing', False))
                        except Exception: pass
                    finally:
                        self._timing_write_scheduled = False
                self.window.after(600, lambda: __import__('threading').Thread(target=_flush_timing, daemon=True).start())
                self.window.after(3500, lambda: setattr(self, 'user_is_editing_timing', False))
        except Exception as e:
            logging.warning(f"خطا در _save_timing_entry: {e}")
            self.user_is_editing_timing = False
    
    def _move_to_next_field(self, prog_idx, field_name):
        try:
            prog_data = self.timing_programs[prog_idx]
            entry_order = [
                "from_H", "from_M", "from_S",
                "to_H", "to_M", "to_S",
                "green_1", "green_2", "green_3", "green_4", "green_5", "green_6", "green_7", "green_8"
            ]
            
            if field_name in entry_order:
                current_idx = entry_order.index(field_name)
                if current_idx < len(entry_order) - 1:
                    next_field = entry_order[current_idx + 1]
                    next_entry = prog_data["entries"][next_field][0]
                    next_entry.focus_set()
                    next_entry.select_range(0, "end")
        except:
            pass
    
    def _on_timing_change(self, prog_idx, field_name):
        if not self.is_connected or not self.client:
            self.user_is_editing_timing = False
            return
        try:
            prog_data = self.timing_programs[prog_idx]
            if field_name == "status":
                var, addr = prog_data["vars"]["status"]
                value = 1 if var.get() == "فعال" else 0
            elif field_name.startswith("day_"):
                day_col = int(field_name.split("_")[1])
                var, addr = prog_data["vars"][f"day_{day_col}"]
                value = 1 if var.get() else 0
            elif field_name == "mode":
                var, addr = prog_data["vars"]["mode"]
                value = 1 if var.get() == "هوشمند" else 0
            elif field_name.startswith("phase_"):
                phase_num = int(field_name.split("_")[1])
                var, addr = prog_data["vars"][f"phase_{phase_num}"]
                val_map = {"------": 0, "زمان ثابت": 1, "ماکزیمم": 2}
                value = val_map.get(var.get(), 0)
            elif field_name == "part":
                var, addr = prog_data["vars"]["part"]
                value = 0 if var.get() == "جدول 1" else 1
            else:
                return
            self._timing_pending[(prog_idx, field_name)] = (addr, value)
        except Exception as e:
            logging.warning(f"timing change queue {field_name}: {e}")
            return
        self.user_is_editing_timing = True
        self._cancel_after("timing_edit_guard")
        self._schedule_after("timing_edit_guard", 3500, lambda: setattr(self, 'user_is_editing_timing', False))
        if not getattr(self, '_timing_write_scheduled', False):
            self._timing_write_scheduled = True
            def _flush_timing2():
                try:
                    items = dict(self._timing_pending)
                    self._timing_pending = {}
                    self._timing_write_scheduled = False
                    import time as _t2
                    for (pp, ff), (aa, vv) in list(items.items()):
                        try:
                            with self.plc_lock:
                                r = self.client.write_register(address=aa, value=vv, device_id=1)
                                if hasattr(r, 'isError') and r.isError():
                                    logging.warning(f"timing write fail {pp}/{ff} @{aa}={vv}")
                            _t2.sleep(0.02)
                        except Exception as e:
                            logging.warning(f"timing batch2 {pp}/{ff}: {e}")
                    self.window.after(0, lambda: setattr(self, 'user_is_editing_timing', False))
                except Exception as e:
                    logging.warning(f"timing flush2: {e}")
                    try: self.window.after(0, lambda: setattr(self, 'user_is_editing_timing', False))
                    except Exception: pass
                finally:
                    self._timing_write_scheduled = False
            self._schedule_after("timing_write", 500, lambda: __import__('threading').Thread(target=_flush_timing2, daemon=True).start())
    
    def _load_timing_program(self, prog_idx):
        if not self.is_connected or not self.client:
            return
        
        def _load():
            try:
                prog_data = self.timing_programs[prog_idx]
                base_addr = prog_data["base_addr"]
                
                with self.plc_lock:
                    result = self.client.read_holding_registers(address=base_addr, count=32, device_id=1)
                
                if result.isError():
                    return
                
                regs = result.registers
                
                status = "فعال" if regs[0] == 1 else "غیر فعال"
                self.window.after(0, lambda v=prog_data["vars"]["status"][0], s=status: v.set(s))
                
                for day_col in range(7):
                    day_value = regs[1 + day_col] == 1
                    self.window.after(0, lambda v=prog_data["vars"][f"day_{day_col}"][0], val=day_value: v.set(val))
                self.window.after(0, lambda p=prog_idx: self._refresh_day_buttons(p))

                mode = "هوشمند" if regs[31] == 1 else "زمان ثابت"
                self.window.after(0, lambda v=prog_data["vars"]["mode"][0], m=mode: v.set(m))
                
                for i, label in enumerate(["H", "M", "S"]):
                    entry_key = f"from_{label}"
                    entry = prog_data["entries"][entry_key][0]
                    value = regs[8 + i]
                    if not (self.focused_timing_prog == prog_idx and self.focused_timing_field == entry_key):
                        self.window.after(0, lambda e=entry, v=value: self._set_entry_value_safe(e, v))
                    
                    entry_key = f"to_{label}"
                    entry = prog_data["entries"][entry_key][0]
                    value = regs[11 + i]
                    if not (self.focused_timing_prog == prog_idx and self.focused_timing_field == entry_key):
                        self.window.after(0, lambda e=entry, v=value: self._set_entry_value_safe(e, v))
                
                for phase in range(8):
                    entry_key = f"green_{phase+1}"
                    entry = prog_data["entries"][entry_key][0]
                    value = regs[14 + phase]
                    if not (self.focused_timing_prog == prog_idx and self.focused_timing_field == entry_key):
                        self.window.after(0, lambda e=entry, v=value: self._set_entry_value_safe(e, v))
                
                phase_map = {0: "------", 1: "زمان ثابت", 2: "ماکزیمم"}
                for phase in range(8):
                    var = prog_data["vars"][f"phase_{phase+1}"][0]
                    value = phase_map.get(regs[22 + phase], "------")
                    self.window.after(0, lambda v=var, val=value: v.set(val))
                
                part_var = prog_data["vars"]["part"][0]
                part_value = "جدول 1" if regs[30] == 0 else "جدول 2"
                self.window.after(0, lambda v=part_var, p=part_value: v.set(p))
            except Exception as e:
                logging.warning(f"خطا در بارگذاری برنامه {prog_idx}: {e}")
        
        threading.Thread(target=_load, daemon=True).start()
    
    def _load_all_timing_programs(self):
        visible_count = self.visible_programs_var.get()
        for prog_idx in range(visible_count):
            self._load_timing_program(prog_idx)
            time.sleep(0.05)
    
    def _auto_load_timing_loop(self):
        if not self.timing_page_auto_load_running:
            return
        if self.selected_option != 1:
            self._schedule_after("timing", 2000, self._auto_load_timing_loop)
            return
        if self.is_connected and self.client and not self.user_is_editing_timing:
            self._load_all_timing_programs()
            self._load_timing_datetime()
        self._schedule_after("timing", 2000, self._auto_load_timing_loop)
    
    def _load_timing_datetime(self):
        if not self.is_connected or not self.client:
            return
        
        def _load():
            try:
                time_result = self._read_register(5409, 3)
                if not time_result.isError():
                    sec = time_result.registers[0]
                    minute = time_result.registers[1]
                    hour = time_result.registers[2]
                    self.window.after(0, lambda: self.timing_hour_label.configure(text=f"{hour:02d}"))
                    self.window.after(0, lambda: self.timing_min_label.configure(text=f"{minute:02d}"))
                
                year_result = self._read_register(4193, 1)
                month_result = self._read_register(4206, 1)
                day_result = self._read_register(4208, 1)
                
                if not year_result.isError() and not month_result.isError() and not day_result.isError():
                    y = year_result.registers[0]
                    mo = month_result.registers[0]
                    d = day_result.registers[0]
                    date_str = f"{y}/{mo:02d}/{d:02d}"
                    self.window.after(0, lambda: self.timing_shamsi_date_label.configure(text=date_str))
                    
                    # 5414: 1=دوشنبه .. 7=یکشنبه (مطابق برنامه اصلی — 1..7)
                    try:
                        wd5414 = self._read_register(self.WEEKDAY_5414_ADDRESS, 1)
                        if not wd5414.isError():
                            raw = wd5414.registers[0]
                            if 1 <= raw <= 7:
                                v = raw - 1
                            elif raw == 0:
                                v = 6
                            else:
                                v = (raw - 1) % 7
                            if 0 <= v < len(self.day_names):
                                day_name = self.day_names[v]
                                self.window.after(0, lambda n=day_name: self.timing_day_name_label.configure(text=n))
                            else:
                                raise ValueError()
                        else:
                            raise ValueError()
                    except Exception:
                        day_name = self._get_jalali_day_name(y, mo, d)
                        self.window.after(0, lambda: self.timing_day_name_label.configure(text=day_name))
            except Exception as e:
                logging.warning(f"خطا در بارگذاری ساعت/تاریخ: {e}")
        
        threading.Thread(target=_load, daemon=True).start()
    
    def _get_jalali_day_name(self, jy, jm, jd):
        try:
            gy, gm, gd = self._jalali_to_gregorian_date(jy, jm, jd)
            from datetime import datetime as _dt
            date = _dt(gy, gm, gd)
            days_fa = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه", "شنبه", "یکشنبه"]
            return days_fa[date.weekday()]
        except:
            return "------"
    
    def _jalali_to_gregorian_date(self, jy, jm, jd):
        try:
            gy = jy + 621
            if jm <= 6:
                day_of_year = (jm - 1) * 31 + jd
            else:
                day_of_year = 186 + (jm - 7) * 30 + jd
            
            if (gy % 4 == 0 and gy % 100 != 0) or (gy % 400 == 0):
                start_day = 80
            else:
                start_day = 79
            
            total_day = start_day + day_of_year - 1
            days_in_year = 366 if ((gy % 4 == 0 and gy % 100 != 0) or (gy % 400 == 0)) else 365
            
            if total_day < days_in_year:
                gm, gd = self._day_to_month_day(total_day, days_in_year == 366)
                return gy, gm, gd
            else:
                total_day -= days_in_year
                gy += 1
                if (gy % 4 == 0 and gy % 100 != 0) or (gy % 400 == 0):
                    days_in_next_year = 366
                else:
                    days_in_next_year = 365
                gm, gd = self._day_to_month_day(total_day, days_in_next_year == 366)
                return gy, gm, gd
        except:
            return 2026, 1, 1
    
    def increase_visible_programs(self):
        current = self.visible_programs_var.get()
        if current < 27:
            new_count = current + 1
            self.visible_programs_var.set(new_count)
            prog_frame = self.program_frames[new_count - 1]
            prog_frame.pack(fill="x", padx=10, pady=3)
    
    def decrease_visible_programs(self):
        current = self.visible_programs_var.get()
        if current > 1:
            self._set_program_status(current - 1, "غیر فعال")
            self._on_timing_change(current - 1, "status")
            prog_frame = self.program_frames[current - 1]
            prog_frame.pack_forget()
            new_count = current - 1
            self.visible_programs_var.set(new_count)
    
    def _set_program_status(self, prog_idx, status):
        if prog_idx in self.timing_programs:
            status_var, addr = self.timing_programs[prog_idx]["vars"]["status"]
            status_var.set(status)
    
    def _set_entry_value(self, entry, value):
        try:
            entry.delete(0, "end")
            entry.insert(0, str(value))
        except:
            pass
    
    def _set_entry_value_safe(self, entry, value):
        try:
            if entry != self.window.focus_get():
                entry.delete(0, "end")
                entry.insert(0, str(value))
        except:
            pass

    def _reset_single_timing_program(self, prog_idx):
        if not self.is_connected or not self.client:
            messagebox.showwarning("هشدار", "ابتدا به PLC متصل شوید!")
            return
        if prog_idx not in self.timing_programs:
            return
        import time as _t
        key = f"_last_reset_timing_{prog_idx}"
        if _t.time() - getattr(self, key, 0) < 1.5:
            return
        if not messagebox.askyesno("تایید ریست برنامه",
                                    f"برنامه {prog_idx + 1} ریست میشود",
                                    icon="warning"):
            return
        if not messagebox.askyesno("تایید نهایی",
                                    "تمام لامپ ها خاموش میشوند !!",
                                    icon="warning"):
            return
        setattr(self, key, _t.time())
        prog_data = self.timing_programs[prog_idx]
        try:
            btn = prog_data.get("reset_btn")
            if btn:
                btn.configure(state="disabled")
                self.window.after(2000, lambda b=btn: b.configure(state="normal"))
        except Exception:
            pass
        self.user_is_editing_timing = True

        def _do(p=prog_idx, pd=prog_data):
            try:
                base = pd["base_addr"]
                # UI: برنامه غیر فعال
                if "status" in pd["vars"]:
                    var, _addr = pd["vars"]["status"]
                    self.window.after(0, lambda v=var: v.set("غیر فعال"))
                # UI: روزها همه غیر فعال + دکمه‌ها رفرش
                for d in range(7):
                    k = f"day_{d}"
                    if k in pd["vars"]:
                        var, _addr = pd["vars"][k]
                        self.window.after(0, lambda v=var: v.set(False))
                self.window.after(30, lambda pp=p: self._refresh_day_buttons(pp))
                # UI: ساعت از/تا 0
                for k in ["from_H", "from_M", "from_S", "to_H", "to_M", "to_S"]:
                    if k in pd["entries"]:
                        e, _addr = pd["entries"][k]
                        self.window.after(0, lambda ee=e: (ee.delete(0, "end"), ee.insert(0, "0")))
                # UI: سبزها 0
                for ph in range(1, 9):
                    k = f"green_{ph}"
                    if k in pd["entries"]:
                        e, _addr = pd["entries"][k]
                        self.window.after(0, lambda ee=e: (ee.delete(0, "end"), ee.insert(0, "0")))
                # UI: فازها ------
                for ph in range(1, 9):
                    k = f"phase_{ph}"
                    if k in pd["vars"]:
                        var, _addr = pd["vars"][k]
                        self.window.after(0, lambda v=var: v.set("------"))
                # UI: حالت = زمان ثابت
                if "mode" in pd["vars"]:
                    var, _addr = pd["vars"]["mode"]
                    self.window.after(0, lambda v=var: v.set("زمان ثابت"))
                # UI: جدول 1
                if "part" in pd["vars"]:
                    var, _addr = pd["vars"]["part"]
                    self.window.after(0, lambda v=var: v.set("جدول 1"))
                # PLC: برنامه غیر فعال
                try:
                    with self.plc_lock:
                        self.client.write_register(address=base + 0, value=0, device_id=1)
                    _t.sleep(0.02)
                except Exception:
                    pass
                # PLC: روزها 0
                for d in range(7):
                    try:
                        with self.plc_lock:
                            self.client.write_register(address=base + 1 + d, value=0, device_id=1)
                        _t.sleep(0.02)
                    except Exception:
                        pass
                # PLC: H/M/S از و تا
                for offset in [8, 9, 10, 11, 12, 13]:
                    try:
                        with self.plc_lock:
                            self.client.write_register(address=base + offset, value=0, device_id=1)
                        _t.sleep(0.02)
                    except Exception:
                        pass
                # PLC: سبزها
                for ph in range(8):
                    try:
                        with self.plc_lock:
                            self.client.write_register(address=base + 14 + ph, value=0, device_id=1)
                        _t.sleep(0.02)
                    except Exception:
                        pass
                # PLC: فازها 0
                for ph in range(8):
                    try:
                        with self.plc_lock:
                            self.client.write_register(address=base + 22 + ph, value=0, device_id=1)
                        _t.sleep(0.02)
                    except Exception:
                        pass
                # PLC: حالت = زمان ثابت (0)
                try:
                    with self.plc_lock:
                        self.client.write_register(address=base + 31, value=0, device_id=1)
                    _t.sleep(0.02)
                except Exception:
                    pass
                # PLC: جدول 1
                try:
                    with self.plc_lock:
                        self.client.write_register(address=base + 30, value=0, device_id=1)
                    _t.sleep(0.02)
                except Exception:
                    pass
                self.window.after(0, lambda pp=p: messagebox.showinfo("موفق", f"برنامه {pp + 1} ریست شد"))
            except Exception as e:
                logging.warning(f"reset timing {p} failed: {e}")
                self.window.after(0, lambda: messagebox.showerror("خطا", f"خطا در ریست: {e}"))
            finally:
                self.window.after(800, lambda: setattr(self, 'user_is_editing_timing', False))

        import threading as _th2
        _th2.Thread(target=_do, daemon=True).start()

    def _reset_timing_programs(self):
        # سازگاری — اگر صدا زده شد، همه را تکی ریست کن
        for i in range(27):
            if i in self.timing_programs:
                self._reset_single_timing_program(i)
                break
    
    def build_blink_page(self):
        page = tk.Frame(self.content_frame, bg=Theme.BG_TABLE_HEAD)

        title_frame = tk.Frame(page, bg=Theme.BG_TABLE_HEAD)
        title_frame.pack(fill="x", padx=10, pady=10)
        tk.Label(title_frame, text="تنظیمات چشمک زن — چهارراه", bg=Theme.BG_TABLE_HEAD, fg="white",
                font=("Arial", 18, "bold")).pack()

        # ── چهارراه 700×500 مثل صفحه اصلی — 8 پارت سر جاش، عابر وسط ──
        map_wrap = tk.Frame(page, bg=Theme.BG_TABLE_HEAD)
        map_wrap.pack(fill="both", expand=True, padx=12, pady=8)

        self.blink_canvas = tk.Canvas(map_wrap, width=700, height=500, bg=Theme.BG_TABLE_HEAD,
                                      highlightthickness=0)
        self.blink_canvas.pack(pady=6)

        # فریم‌های انتخاب هر پارت — روی نقشه با window_create سوار می‌شوند
        for key in list(self.blink_vars.keys()):
            if isinstance(key, int):
                del self.blink_vars[key]

        # کارت‌ها بیرون چهارراه — شرق/غرب کمی داخل‌تر تا کادر از فیلد کوچک‌تر نماند و بریده نشود
        part_positions = {
            1: (250, 50), 2: (450, 50),   # شمال — فاصله 200px
            3: (620, 185), 4: (620, 315), # شرق — 15px داخل‌تر از لبه
            5: (450, 450), 6: (250, 450), # جنوب — فاصله 200px
            7: (80, 315), 8: (80, 185),   # غرب — 15px داخل‌تر از لبه
        }
        # عابر وسط
        ped_pos = (350, 250)

        for part_num in range(1, 9):
            card = tk.Frame(self.blink_canvas, bg="#2B2B2B", bd=1, relief="raised")
            tk.Label(card, text=f"PART {part_num}", bg="#FF9800", fg="white",
                    font=("Arial", 11, "bold"), width=12, height=2).pack(fill="x")
            var = tk.StringVar(value="غیر فعال")
            combo = ttk.Combobox(card, textvariable=var,
                                 values=["غیر فعال", "چشمک زن قرمز", "چشمک زن زرد"],
                                 state="readonly", width=14, font=("Arial", 11, "bold"), justify="center", style="White.TCombobox")
            combo.pack(padx=6, pady=6, ipady=4)
            combo.bind("<<ComboboxSelected>>",
                      lambda e, p=part_num, v=var: (self._on_blink_change(p, v), self.window.after(30, self._apply_blink_colors)))
            combo.bind("<<ComboboxSelected>>",
                      lambda e, c=combo: self.window.after(60, lambda: (c.selection_clear(), self.window.focus_set())), add="+")
            if not hasattr(self, 'blink_combos'):
                self.blink_combos = {}
            self.blink_combos[part_num] = combo
            self.blink_vars[part_num] = (var, self.PART_BLINK_ADDRESSES[part_num])
            x, y = part_positions[part_num]
            self.blink_canvas.create_window(x, y, window=card, anchor="center")

        # عابر وسط — دکمه شاسی (نه فیلد) — یک کلیک بین سبز/قرمز
        ped_card = tk.Frame(self.blink_canvas, bg="#1B5E20", bd=2, relief="raised")
        tk.Label(ped_card, text="عابر پیاده", bg="#00C853", fg="white",
                font=("Arial", 12, "bold"), width=14, height=2).pack(fill="x")
        pedestrian_var = tk.StringVar(value="چشمک زن سبز")
        def _ped_colors(val):
            return ("#66BB6A", "black") if val == "چشمک زن سبز" else ("#EF5350", "white")
        pbg, pfg = _ped_colors(pedestrian_var.get())
        pedestrian_btn = tk.Button(ped_card, textvariable=pedestrian_var, bg=pbg, fg=pfg,
                                   activebackground=pbg, activeforeground=pfg,
                                   font=("Arial", 11, "bold"), width=14, bd=1, relief="raised", cursor="hand2",
                                   command=lambda v=pedestrian_var: (v.set("چشمک زن قرمز" if v.get() == "چشمک زن سبز" else "چشمک زن سبز"), self._on_blink_change("pedestrian", v), self.window.after(30, self._apply_blink_colors)))
        pedestrian_var.trace_add("write", lambda *_a, b=pedestrian_btn, v=pedestrian_var: b.configure(bg=_ped_colors(v.get())[0], fg=_ped_colors(v.get())[1], activebackground=_ped_colors(v.get())[0]))
        pedestrian_btn.pack(padx=8, pady=8, ipady=4)
        self.blink_vars["pedestrian"] = (pedestrian_var, self.PEDESTRIAN_BLINK_ADDRESS)
        # برای سازگاری با _apply_blink_colors که blink_combos را می‌خواند، دکمه را هم آنجا بگذار
        if not hasattr(self, 'blink_combos'):
            self.blink_combos = {}
        self.blink_combos["pedestrian"] = pedestrian_btn
        self.blink_canvas.create_window(ped_pos[0], ped_pos[1], window=ped_card, anchor="center")
        try:
            self.window.after(300, self._apply_blink_colors)
        except Exception:
            pass
        self.pages[2] = page

    def _draw_blink_map(self):
        pass
    
    def _poll_lamp_test_status(self):
        if not self.is_connected or not self.client or getattr(self, 'selected_option', None) != 7:
            self._schedule_after("lamp_poll", 1500, self._poll_lamp_test_status)
            return
        def _read():
            try:
                with self.plc_lock:
                    r = self.client.read_holding_registers(address=self.LAMP_TEST_MODE_ADDRESS, count=1, device_id=1)
                if not r.isError():
                    v = r.registers[0]
                    is_on = (v == 1)
                    self.window.after(0, lambda: self.lamp_test_enabled_var.set(1 if is_on else 0) if hasattr(self, 'lamp_test_enabled_var') else None)
                    self.window.after(0, lambda: self.lamp_test_toggle_btn.configure(text="غیرفعال کردن حالت تست" if is_on else "فعال کردن حالت تست", bg="#F44336" if is_on else "#4CAF50") if hasattr(self, 'lamp_test_toggle_btn') else None)
                    self.window.after(0, lambda: self.lamp_test_status_label.configure(text="وضعیت: فعال (PLC)" if is_on else "وضعیت: غیرفعال (PLC)", bg="#4CAF50" if is_on else "#78909C") if hasattr(self, 'lamp_test_status_label') else None)
            except Exception:
                pass
        import threading as _thp
        _thp.Thread(target=_read, daemon=True).start()
        self._schedule_after("lamp_poll", 1200, self._poll_lamp_test_status)

    def _on_blink_change(self, key, var):
        if not self.is_connected or not self.client:
            self.user_is_editing_blink = False
            return
        
        self.user_is_editing_blink = True
        
        def _save():
            try:
                if key == "pedestrian":
                    addr = self.PEDESTRIAN_BLINK_ADDRESS
                    val_map = {"چشمک زن سبز": 0, "چشمک زن قرمز": 1}
                    value = val_map.get(var.get(), 0)
                else:
                    addr = self.PART_BLINK_ADDRESSES[key]
                    val_map = {"غیر فعال": 0, "چشمک زن قرمز": 1, "چشمک زن زرد": 2}
                    value = val_map.get(var.get(), 0)
                
                with self.plc_lock:
                    self.client.write_register(address=addr, value=value, device_id=1)
                
                self.window.after(0, lambda: setattr(self, 'user_is_editing_blink', False))
            except Exception as e:
                logging.warning(f"خطا در ذخیره چشمک زن {key}: {e}")
                self._handle_connection_error()
                self.window.after(0, lambda: setattr(self, 'user_is_editing_blink', False))
        
        threading.Thread(target=_save, daemon=True).start()
        self.window.after(5000, lambda: setattr(self, 'user_is_editing_blink', False))
    
    def _load_blink_page(self):
        if not self.is_connected or not self.client:
            return
        
        def _load():
            try:
                part_val_map = {0: "غیر فعال", 1: "چشمک زن قرمز", 2: "چشمک زن زرد"}
                
                for part_num in range(1, 9):
                    if part_num in self.blink_vars:
                        var, addr = self.blink_vars[part_num]
                        result = self._read_register(addr, 1)
                        if not result.isError():
                            value = result.registers[0]
                            text = part_val_map.get(value, "غیر فعال")
                            self.window.after(0, lambda v=var, t=text: v.set(t))
                            self.window.after(10, self._apply_blink_colors)
                
                if "pedestrian" in self.blink_vars:
                    var, addr = self.blink_vars["pedestrian"]
                    result = self._read_register(addr, 1)
                    if not result.isError():
                        value = result.registers[0]
                        pedestrian_val_map = {0: "چشمک زن سبز", 1: "چشمک زن قرمز"}
                        text = pedestrian_val_map.get(value, "چشمک زن سبز")
                        self.window.after(0, lambda v=var, t=text: v.set(t))
                        self.window.after(10, self._apply_blink_colors)
            except Exception as e:
                logging.warning(f"خطا در بارگذاری چشمک زن: {e}")
        
        threading.Thread(target=_load, daemon=True).start()
    
    def _auto_load_blink_loop(self):
        if not self.blink_page_auto_load_running:
            return
        if self.selected_option != 2:
            self._schedule_after("blink", 2000, self._auto_load_blink_loop)
            return
        if self.is_connected and self.client and not self.user_is_editing_blink:
            self._load_blink_page()
        self._schedule_after("blink", 2000, self._auto_load_blink_loop)
    
    def build_part_settings_page(self):
        page = tk.Frame(self.content_frame, bg=Theme.BG_TABLE_HEAD)
        
        header_frame = tk.Frame(page, bg=Theme.BG_TABLE_HEAD)
        header_frame.pack(fill="x", padx=10, pady=10)
        
        phase_count_frame = tk.Frame(header_frame, bg=Theme.BG_TABLE_HEAD)
        phase_count_frame.pack(side="right", padx=20)
        
        tk.Label(phase_count_frame, text="تعداد فازها", bg="#FF69B4", fg="white",
                font=("Arial", 14, "bold")).pack(side="right", padx=5)
        
        self.part_phase_count_var = tk.StringVar(value="2")
        phase_count_combo = ttk.Combobox(phase_count_frame, textvariable=self.part_phase_count_var,
                                          values=[str(i) for i in range(2, 9)],
                                          state="readonly", width=3, font=("Arial", 16, "bold"), justify="center")
        phase_count_combo.pack(side="right", padx=5)
        phase_count_combo.bind("<<ComboboxSelected>>", lambda e: self._on_part_phase_count_change())
        
        tab_frame = tk.Frame(header_frame, bg=Theme.BG_TABLE_HEAD)
        tab_frame.pack(side="right", padx=20)
        
        self.part_table1_btn = tk.Button(tab_frame, text="جدول 1", bg="#FF9800", fg="white",
                                          font=("Arial", 12, "bold"), width=10, height=2,
                                          command=lambda: self._switch_part_table(1))
        self.part_table1_btn.pack(side="right", padx=5)
        
        self.part_table2_btn = tk.Button(tab_frame, text="جدول 2", bg="#9E9E9E", fg="white",
                                          font=("Arial", 12, "bold"), width=10, height=2,
                                          command=lambda: self._switch_part_table(2))
        self.part_table2_btn.pack(side="right", padx=5)
        
        self.part_table_title = tk.Label(page, text="جدول 1", bg="#FF9800", fg="white",
                                          font=("Arial", 18, "bold"))
        self.part_table_title.pack(fill="x", padx=10, pady=5)
        
        table_container = tk.Frame(page, bg=Theme.BG_TABLE_HEAD)
        table_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        canvas = tk.Canvas(table_container, bg=Theme.BG_TABLE_HEAD, highlightthickness=0)
        v_scrollbar = ttk.Scrollbar(table_container, orient="vertical", command=canvas.yview)
        h_scrollbar = ttk.Scrollbar(table_container, orient="horizontal", command=canvas.xview)
        
        self.part_table_frame = tk.Frame(canvas, bg=Theme.BG_TABLE_HEAD)
        
        self.part_table_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.part_table_frame, anchor="nw")
        canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        canvas.pack(side="top", fill="both", expand=True)
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")
        
        self._build_part_settings_table()
        
        self.pages[3] = page
        self.current_part_table = 1
    
    def _build_part_settings_table(self):
        for widget in self.part_table_frame.winfo_children():
            widget.destroy()
        self.part_settings_combos = {}
        
        self.part_options = ["غیر فعال", "خودرو", "چشمک زن زرد", "چشمک زن قرمز", "عابر پیاده"]
        self.part_values = {"غیر فعال": 0, "خودرو": 1, "چشمک زن زرد": 2, "چشمک زن قرمز": 3, "عابر پیاده": 4}
        
        tk.Label(self.part_table_frame, text="", bg=Theme.BG_TABLE_HEAD, width=10).grid(row=0, column=0, padx=3, pady=4)
        for phase in range(1, 9):
            tk.Label(self.part_table_frame, text=f"فاز {phase}", bg="#FF9800", fg="white",
                    font=("Arial", 13, "bold"), width=14, height=2).grid(row=0, column=phase, padx=3, pady=4)
        for part in range(1, 9):
            tk.Label(self.part_table_frame, text=f"PART {part}", bg="#FF9800", fg="white",
                    font=("Arial", 12, "bold"), width=12, height=2).grid(row=part, column=0, padx=3, pady=4)
            
            self.part_settings_combos[part] = {}
            
            for phase in range(1, 9):
                if self.current_part_table == 1:
                    base_addr = self.PART_SETTINGS_TABLE1_BASE
                else:
                    base_addr = self.PART_SETTINGS_TABLE2_BASE
                
                address = base_addr + (phase - 1) * 8 + (part - 1)
                
                var = tk.StringVar(value="غیر فعال")
                combo = ttk.Combobox(self.part_table_frame, textvariable=var,
                                      values=self.part_options,
                                      state="readonly", width=12, font=("Arial", 11, "bold"), justify="center", style="White.TCombobox")
                combo.grid(row=part, column=phase, padx=3, pady=4, ipady=3, sticky="nsew")
                
                combo.bind("<<ComboboxSelected>>",
                          lambda e, p=part, ph=phase, v=var: (self._on_part_setting_change(p, ph, v), self.window.after(30, self._apply_part_settings_colors)))
                combo.bind("<<ComboboxSelected>>",
                          lambda e, c=combo: self.window.after(60, lambda: (c.selection_clear(), self.window.focus_set())), add="+")
                var.trace_add("write", lambda *_a: self.window.after(20, self._apply_part_settings_colors))
                
                self.part_settings_combos[part][phase] = (combo, var, address)
        
        self._on_part_phase_count_change()
        try:
            self.window.after(300, self._apply_part_settings_colors)
        except Exception:
            pass
    
    def _switch_part_table(self, table_num):
        if table_num == self.current_part_table:
            return
        
        self.current_part_table = table_num
        
        if table_num == 1:
            self.part_table1_btn.configure(bg="#FF9800")
            self.part_table2_btn.configure(bg="#9E9E9E")
            self.part_table_title.configure(text="جدول 1", bg="#FF9800")
        else:
            self.part_table1_btn.configure(bg="#9E9E9E")
            self.part_table2_btn.configure(bg="#FF9800")
            self.part_table_title.configure(text="جدول 2", bg="#FF9800")
        
        self._build_part_settings_table()
        
        if self.is_connected and self.client:
            self._load_part_settings_table()
    
    def _on_part_phase_count_change(self):
        try:
            phase_count = int(self.part_phase_count_var.get())
            if phase_count < 2:
                phase_count = 2
                self.part_phase_count_var.set("2")
            elif phase_count > 8:
                phase_count = 8
                self.part_phase_count_var.set("8")
            
            if self.is_connected and self.client:
                target_addr = self.PART_PHASE_COUNT_TABLE1 if self.current_part_table == 1 else self.PART_PHASE_COUNT_TABLE2
                def _write(addr=target_addr):
                    try:
                        with self.plc_lock:
                            self.client.write_register(address=addr, 
                                                       value=phase_count, device_id=1)
                    except Exception as e:
                        logging.warning(f"خطا در نوشتن تعداد فازها: {e}")
                        self._handle_connection_error()
                
                threading.Thread(target=_write, daemon=True).start()
            
            for part in range(1, 9):
                for phase in range(1, 9):
                    if phase in self.part_settings_combos.get(part, {}):
                        combo, var, addr = self.part_settings_combos[part][phase]
                        if phase > phase_count:
                            combo.configure(state="disabled")
                        else:
                            combo.configure(state="readonly")
        except:
            pass
    
    def _on_part_setting_change(self, part, phase, var):
        if not self.is_connected or not self.client:
            self.user_is_editing_part_settings = False
            return
        try:
            if part not in self.part_settings_combos or phase not in self.part_settings_combos[part]:
                return
            _, _, address = self.part_settings_combos[part][phase]
            value = self.part_values.get(var.get(), 0)
            self._part_pending[(part, phase)] = (address, value)
        except Exception as e:
            logging.warning(f"part queue {part}/{phase}: {e}")
            return
        self.user_is_editing_part_settings = True
        self._cancel_after("part_edit_guard")
        self._schedule_after("part_edit_guard", 3500, lambda: setattr(self, 'user_is_editing_part_settings', False))
        if not getattr(self, '_part_write_scheduled', False):
            self._part_write_scheduled = True
            def _flush_part():
                try:
                    items = dict(self._part_pending)
                    self._part_pending = {}
                    self._part_write_scheduled = False
                    import time as _t
                    for (pp, ph), (aa, vv) in list(items.items()):
                        try:
                            with self.plc_lock:
                                r = self.client.write_register(address=aa, value=vv, device_id=1)
                                if hasattr(r, 'isError') and r.isError():
                                    logging.warning(f"part write fail {pp}/{ph} @{aa}={vv}")
                            _t.sleep(0.02)
                        except Exception as e:
                            logging.warning(f"part batch {pp}/{ph}: {e}")
                    self.window.after(0, lambda: setattr(self, 'user_is_editing_part_settings', False))
                except Exception as e:
                    logging.warning(f"part flush: {e}")
                    try: self.window.after(0, lambda: setattr(self, 'user_is_editing_part_settings', False))
                    except Exception: pass
                finally:
                    self._part_write_scheduled = False
            self._schedule_after("part_write", 400, lambda: __import__('threading').Thread(target=_flush_part, daemon=True).start())
    
    def _load_part_settings_table(self):
        if not self.is_connected or not self.client:
            return
        
        def _load():
            try:
                target_addr = self.PART_PHASE_COUNT_TABLE1 if self.current_part_table == 1 else self.PART_PHASE_COUNT_TABLE2
                with self.plc_lock:
                    phase_result = self.client.read_holding_registers(
                        address=target_addr, count=1, device_id=1)
                
                if not phase_result.isError():
                    phase_count = phase_result.registers[0]
                    if phase_count < 2:
                        phase_count = 2
                    elif phase_count > 8:
                        phase_count = 8
                    
                    self.window.after(0, lambda: self.part_phase_count_var.set(str(phase_count)))
                    self.window.after(0, lambda: self._update_phase_columns_state(phase_count))
                
                val_to_text = {0: "غیر فعال", 1: "خودرو", 2: "چشمک زن زرد", 3: "چشمک زن قرمز", 4: "عابر پیاده"}
                
                if self.current_part_table == 1:
                    base_addr = self.PART_SETTINGS_TABLE1_BASE
                else:
                    base_addr = self.PART_SETTINGS_TABLE2_BASE
                
                with self.plc_lock:
                    result = self.client.read_holding_registers(address=base_addr, count=64, device_id=1)
                
                if result.isError():
                    return
                
                regs = result.registers
                
                for phase in range(1, 9):
                    for part in range(1, 9):
                        idx = (phase - 1) * 8 + (part - 1)
                        
                        if idx < len(regs) and part in self.part_settings_combos and phase in self.part_settings_combos[part]:
                            combo, var, addr = self.part_settings_combos[part][phase]
                            value = regs[idx]
                            text = val_to_text.get(value, "غیر فعال")
                            
                            self.window.after(0, lambda v=var, t=text: v.set(t))
                self.window.after(10, self._apply_part_settings_colors)
            except Exception as e:
                logging.warning(f"خطا در بارگذاری تنظیم پارت‌ها: {e}")
        
        threading.Thread(target=_load, daemon=True).start()
    
    def _update_phase_columns_state(self, phase_count):
        for part in range(1, 9):
            for phase in range(1, 9):
                if phase in self.part_settings_combos.get(part, {}):
                    combo, var, addr = self.part_settings_combos[part][phase]
                    if phase > phase_count:
                        combo.configure(state="disabled")
                    else:
                        combo.configure(state="readonly")
    
    def _auto_load_part_settings_loop(self):
        if not self.part_settings_page_auto_load_running:
            return
        if self.selected_option != 3:
            self._schedule_after("part", 4000, self._auto_load_part_settings_loop)
            return
        if getattr(self, '_part_write_scheduled', False):
            self._schedule_after("part", 4000, self._auto_load_part_settings_loop)
            return
        if self.is_connected and self.client and not self.user_is_editing_part_settings:
            try:
                self._load_part_settings_table()
            except Exception as e:
                logging.warning(f"part auto load: {e}")
        self._schedule_after("part", 4000, self._auto_load_part_settings_loop)
    
    def build_loop_settings_page(self):
        page = tk.Frame(self.content_frame, bg=Theme.BG_TABLE_HEAD)
        
        header_frame = tk.Frame(page, bg=Theme.BG_TABLE_HEAD)
        header_frame.pack(fill="x", padx=10, pady=10)
        
        tab_frame = tk.Frame(header_frame, bg=Theme.BG_TABLE_HEAD)
        tab_frame.pack(side="right", padx=20)
        
        self.loop_table1_btn = tk.Button(tab_frame, text="جدول 1", bg="#FF9800", fg="white",
                                          font=("Arial", 12, "bold"), width=10, height=2,
                                          command=lambda: self._switch_loop_table(1))
        self.loop_table1_btn.pack(side="right", padx=5)
        
        self.loop_table2_btn = tk.Button(tab_frame, text="جدول 2", bg="#9E9E9E", fg="white",
                                          font=("Arial", 12, "bold"), width=10, height=2,
                                          command=lambda: self._switch_loop_table(2))
        self.loop_table2_btn.pack(side="right", padx=5)
        
        self.loop_table_title = tk.Label(page, text="جدول 1", bg="#FF9800", fg="white",
                                          font=("Arial", 18, "bold"))
        self.loop_table_title.pack(fill="x", padx=10, pady=5)
        
        table_container = tk.Frame(page, bg=Theme.BG_TABLE_HEAD)
        table_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        canvas = tk.Canvas(table_container, bg=Theme.BG_TABLE_HEAD, highlightthickness=0)
        v_scrollbar = ttk.Scrollbar(table_container, orient="vertical", command=canvas.yview)
        h_scrollbar = ttk.Scrollbar(table_container, orient="horizontal", command=canvas.xview)
        
        self.loop_table_frame = tk.Frame(canvas, bg=Theme.BG_TABLE_HEAD)
        
        self.loop_table_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.loop_table_frame, anchor="nw")
        canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        canvas.pack(side="top", fill="both", expand=True)
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")
        
        self.current_loop_table = 1
        self.loop_combos = {}
        
        self._build_loop_table()
        try:
            self.window.after(300, self._apply_loop_settings_colors)
        except Exception:
            pass
        self.pages[4] = page
    
    def _build_loop_table(self):
        if getattr(self, '_loop_building', False):
            return
        self._loop_building = True
        try:
            for widget in list(self.loop_table_frame.winfo_children()):
                try: widget.destroy()
                except Exception: pass
            self.loop_combos = {}
            self.loop_options = ["غیر فعال", "فعال"]
            self.loop_values = {"غیر فعال": 0, "فعال": 1}
            if self.current_loop_table == 1:
                base_addr = self.LOOP_TABLE1_BASE
            else:
                base_addr = self.LOOP_TABLE2_BASE
            tk.Label(self.loop_table_frame, text="", bg=Theme.BG_TABLE_HEAD, width=8).grid(row=0, column=0, padx=3, pady=4)
            for loop in range(1, 17):
                tk.Label(self.loop_table_frame, text=f"لوپ {loop}", bg="#FF9800", fg="white",
                        font=("Arial", 11, "bold"), width=8, height=2).grid(row=0, column=loop, padx=3, pady=4)
            for phase in range(1, 9):
                tk.Label(self.loop_table_frame, text=f"فاز {phase}", bg="#FF9800", fg="white",
                        font=("Arial", 13, "bold"), width=9, height=2).grid(row=phase, column=0, padx=3, pady=4)
                self.loop_combos[phase] = {}
                for loop in range(1, 17):
                    address = base_addr + (phase - 1) * 16 + (loop - 1)
                    var = tk.StringVar(value="غیر فعال")
                    btn = tk.Button(self.loop_table_frame, textvariable=var,
                                    bg="#EF5350", fg="white", activebackground="#E53935", activeforeground="white",
                                    font=("Arial", 11, "bold"), width=8, height=2, bd=1, relief="raised", cursor="hand2",
                                    command=lambda p=phase, l=loop: self._toggle_loop_btn(p, l))
                    btn.grid(row=phase, column=loop, padx=3, pady=4, ipady=2, sticky="nsew")
                    # رنگ بر اساس var همگام شود (برای لود از PLC)
                    var.trace_add("write", lambda *_a, b=btn, v=var: b.configure(
                        bg="#66BB6A" if v.get()=="فعال" else "#EF5350",
                        fg="black" if v.get()=="فعال" else "white",
                        activebackground="#4CAF50" if v.get()=="فعال" else "#E53935"))
                    self.loop_combos[phase][loop] = (btn, var, address)
        finally:
            self._loop_building = False
            try:
                self.window.after(50, self._apply_loop_settings_colors)
            except Exception: pass

    def _switch_loop_table(self, table_num):
        if table_num == self.current_loop_table:
            return
        if getattr(self, '_loop_building', False) or getattr(self, '_loop_loading', False):
            self.window.after(200, lambda t=table_num: self._switch_loop_table(t))
            return
        try:
            self.loop_table1_btn.configure(state="disabled")
            self.loop_table2_btn.configure(state="disabled")
        except Exception: pass
        
        self.current_loop_table = table_num
        
        if table_num == 1:
            self.loop_table1_btn.configure(bg="#FF9800")
            self.loop_table2_btn.configure(bg="#9E9E9E")
            self.loop_table_title.configure(text="جدول 1", bg="#FF9800")
        else:
            self.loop_table1_btn.configure(bg="#9E9E9E")
            self.loop_table2_btn.configure(bg="#FF9800")
            self.loop_table_title.configure(text="جدول 2", bg="#FF9800")
        
        self._build_loop_table()
        try:
            self.loop_table1_btn.configure(state="normal")
            self.loop_table2_btn.configure(state="normal")
        except Exception: pass
        if self.is_connected and self.client:
            self.window.after(150, self._load_loop_table)
    
    def _on_loop_setting_change(self, phase, loop, var):
        if not self.is_connected or not self.client:
            self.user_is_editing_loops = False
            return
        # debounce — اگر کاربر تند می‌زند، همان آخری بماند
        self.user_is_editing_loops = True
        try:
            pending = getattr(self, '_loop_pending_writes', {})
            pending[(phase, loop)] = var.get()
            self._loop_pending_writes = pending
        except Exception: pass
        self._cancel_after("loop_write")
        def _flush():
            try:
                pending2 = getattr(self, '_loop_pending_writes', {})
                if not pending2:
                    self.user_is_editing_loops = False
                    return
                items = list(pending2.items())
                self._loop_pending_writes = {}
                import time as _tloop
                for (ph, lp), txt in items:
                    try:
                        if ph not in self.loop_combos or lp not in self.loop_combos[ph]:
                            continue
                        _, _, addr = self.loop_combos[ph][lp]
                        val = self.loop_values.get(txt, 0)
                        with self.plc_lock:
                            r = self.client.write_register(address=addr, value=val, device_id=1)
                            if hasattr(r, 'isError') and r.isError():
                                logging.warning(f"loop write fail {ph}/{lp}")
                        _tloop.sleep(0.02)
                    except Exception as e:
                        logging.warning(f"loop write {ph}/{lp}: {e}")
                self.user_is_editing_loops = False
            except Exception as e:
                logging.warning(f"loop flush: {e}")
                self.user_is_editing_loops = False
        self._schedule_after("loop_write", 400, lambda: __import__('threading').Thread(target=_flush, daemon=True).start())
        self._schedule_after("loop_edit_guard", 2500, lambda: setattr(self, 'user_is_editing_loops', False))
    
    def _load_loop_table(self):
        if not self.is_connected or not self.client:
            return
        if getattr(self, '_loop_loading', False):
            return
        if getattr(self, '_loop_building', False):
            self.window.after(200, self._load_loop_table)
            return
        self._loop_loading = True

        def _load():
            try:
                if self.current_loop_table == 1:
                    base_addr = self.LOOP_TABLE1_BASE
                else:
                    base_addr = self.LOOP_TABLE2_BASE

                val_to_text = {0: "غیر فعال", 1: "فعال"}

                for phase in range(1, 9):
                    if getattr(self, '_loop_building', False):
                        break
                    phase_base = base_addr + (phase - 1) * 16
                    try:
                        with self.plc_lock:
                            result = self.client.read_holding_registers(
                                address=phase_base, count=16, device_id=1)
                    except Exception as e:
                        logging.warning(f"loop read phase {phase}: {e}")
                        continue
                    if result.isError():
                        continue
                    try:
                        regs = result.registers
                    except Exception: continue
                    for loop in range(1, 17):
                        try:
                            idx = loop - 1
                            if idx >= len(regs): continue
                            if phase not in self.loop_combos or loop not in self.loop_combos[phase]:
                                continue
                            combo, var, addr = self.loop_combos[phase][loop]
                            # widget may have been destroyed during switch
                            try:
                                if not combo.winfo_exists(): continue
                            except Exception: continue
                            value = regs[idx]
                            text = val_to_text.get(value, "غیر فعال")
                            if var.get() != text:
                                self.window.after(0, lambda v=var, t=text: v.set(t))
                        except Exception:
                            continue
                try:
                    self.window.after(10, self._apply_loop_settings_colors)
                except Exception: pass
            except Exception as e:
                logging.warning(f"خطا در بارگذاری لوپ‌ها: {e}")
            finally:
                self._loop_loading = False

        threading.Thread(target=_load, daemon=True).start()
    
    def _auto_load_loop_loop(self):
        if not self.loop_settings_page_auto_load_running:
            return
        if self.selected_option != 4:
            self._schedule_after("loop", 4000, self._auto_load_loop_loop)
            return
        if getattr(self, '_loop_loading', False) or getattr(self, '_loop_write_scheduled', False):
            self._schedule_after("loop", 4000, self._auto_load_loop_loop)
            return
        if getattr(self, '_loop_building', False):
            self._schedule_after("loop", 4000, self._auto_load_loop_loop)
            return
        if self.is_connected and self.client and not self.user_is_editing_loops:
            try:
                self._load_loop_table()
            except Exception as e:
                logging.warning(f"loop auto load: {e}")
        self._schedule_after("loop", 4000, self._auto_load_loop_loop)
    
    def build_loop_status_page(self):
        page = tk.Frame(self.content_frame, bg=Theme.BG_TABLE_HEAD)
        
        top_section = tk.Frame(page, bg=Theme.BG_TABLE_HEAD)
        top_section.pack(fill="x", padx=10, pady=10)
        
        reset_alarm_frame = tk.Frame(top_section, bg=Theme.BG_TABLE_HEAD)
        reset_alarm_frame.pack(side="left", padx=10)
        
        reset_alarm_btn = tk.Button(reset_alarm_frame, text="ریست آلارم\nو دتکتورها",
                                     bg="#FF0000", fg="white",
                                     font=("Arial", 14, "bold"),
                                     width=12, height=4,
                                     command=self._reset_alarms_and_detectors)
        reset_alarm_btn.pack(pady=10)
        
        for card in range(1, 5):
            det_frame = tk.Frame(top_section, bg=Theme.BG_TABLE_HEAD)
            det_frame.pack(side="left", padx=15)
            
            reset_btn = tk.Button(det_frame, text="ریست کارت",
                                  bg="#FF0000", fg="white",
                                  font=("Arial", 12, "bold"),
                                  width=12, height=2,
                                  command=lambda c=card: self._reset_detector_card(c))
            reset_btn.pack(pady=5)
            self.card_reset_buttons[card] = reset_btn
            
            tk.Label(det_frame, text=f"آلارم و وضعیت ماژول دتکتور {card}",
                    bg="#FF9800", fg="white",
                    font=("Arial", 10, "bold"),
                    width=28).pack(pady=5)
            
            disconnect_btn = tk.Button(det_frame, text=f"ماژول دتکتور {card} قطع می",
                                       bg="#FF0000", fg="white",
                                       font=("Arial", 9),
                                       width=20,
                                       command=lambda c=card: self._toggle_detector_disconnect(c))
            disconnect_btn.pack(pady=5)
            
            error_canvas = tk.Canvas(det_frame, width=50, height=50, bg=Theme.BG_TABLE_HEAD, highlightthickness=0)
            error_canvas.pack(pady=5)
            error_light = error_canvas.create_oval(5, 5, 45, 45, fill="#FF0000", outline="white", width=2)
            self.card_error_lights[card] = (error_canvas, error_light)
        
        bottom_section = tk.Frame(page, bg=Theme.BG_TABLE_HEAD)
        bottom_section.pack(fill="both", expand=True, padx=10, pady=10)
        
        canvas = tk.Canvas(bottom_section, bg=Theme.BG_TABLE_HEAD, highlightthickness=0)
        h_scrollbar = ttk.Scrollbar(bottom_section, orient="horizontal", command=canvas.xview)
        v_scrollbar = ttk.Scrollbar(bottom_section, orient="vertical", command=canvas.yview)
        
        scrollable_frame = tk.Frame(canvas, bg=Theme.BG_TABLE_HEAD)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set)
        
        canvas.pack(side="top", fill="both", expand=True)
        h_scrollbar.pack(side="bottom", fill="x")
        v_scrollbar.pack(side="right", fill="y")
        
        table_frame = tk.Frame(scrollable_frame, bg=Theme.BG_TABLE_HEAD)
        table_frame.pack(side="top", anchor="nw", padx=5, pady=5)
        
        ROW_ALARM, ROW_SENSOR, ROW_CAR = 1, 2, 3
        ROW_GAP_SP, ROW_WASTE_SP, ROW_GAP_PV, ROW_WASTE_PV = 4, 5, 6, 7
        ROW_TIME = 8
        
        row_labels = {
            ROW_ALARM: "آلارم سنسورها",
            ROW_SENSOR: "سنسور سالم/خراب",
            ROW_CAR: "وضعیت خودرو",
            ROW_TIME: "وضعیت زمانی لوپ",
        }
        
        tk.Label(table_frame, text="", bg=Theme.BG_TABLE_HEAD, width=16).grid(row=0, column=0, columnspan=2, padx=3, pady=3)
        for row_idx, text in row_labels.items():
            lbl = tk.Label(table_frame, text=text, bg=Theme.BG_TABLE_HEAD, fg="white",
                          font=("Arial", 9, "bold"), width=16, anchor="e",
                          justify="right")
            lbl.grid(row=row_idx, column=0, columnspan=2, padx=3, pady=3, sticky="nsew")
        
        tk.Label(table_frame, text="SET POINT\n(100ms)", bg="#C2185B", fg="white",
                 font=("Arial", 10, "bold"), width=10, justify="center").grid(
                 row=ROW_GAP_SP, column=0, rowspan=2, padx=3, pady=3, sticky="nsew")
        tk.Label(table_frame, text="Gap", bg=Theme.BG_TABLE_HEAD, fg="white",
                 font=("Arial", 9, "bold"), width=6).grid(row=ROW_GAP_SP, column=1, padx=3, pady=3)
        tk.Label(table_frame, text="Waste", bg=Theme.BG_TABLE_HEAD, fg="white",
                 font=("Arial", 9, "bold"), width=6).grid(row=ROW_WASTE_SP, column=1, padx=3, pady=3)
        
        tk.Label(table_frame, text="PROCESS\nVALUE\n(100ms)", bg="#C2185B", fg="white",
                 font=("Arial", 10, "bold"), width=10, justify="center").grid(
                 row=ROW_GAP_PV, column=0, rowspan=2, padx=3, pady=3, sticky="nsew")
        tk.Label(table_frame, text="Gap", bg=Theme.BG_TABLE_HEAD, fg="white",
                 font=("Arial", 9, "bold"), width=6).grid(row=ROW_GAP_PV, column=1, padx=3, pady=3)
        tk.Label(table_frame, text="Waste", bg=Theme.BG_TABLE_HEAD, fg="white",
                 font=("Arial", 9, "bold"), width=6).grid(row=ROW_WASTE_PV, column=1, padx=3, pady=3)
        
        self.loop_status_widgets = {}
        
        for loop_num in range(1, 17):
            col = loop_num + 1
            extra_left = 15 if (loop_num - 1) % 4 == 0 and loop_num > 1 else 0
            self.loop_status_widgets[loop_num] = {}
            
            tk.Label(table_frame, text=f"لوپ {loop_num}",
                    bg=Theme.BG_TABLE_HEAD, fg="white",
                    font=("Arial", 10, "bold")).grid(
                    row=0, column=col, padx=(3 + extra_left, 3), pady=3)
            
            alarm_canvas = tk.Canvas(table_frame, width=35, height=35, bg=Theme.BG_TABLE_HEAD, highlightthickness=0)
            alarm_light = alarm_canvas.create_oval(5, 5, 30, 30, fill="black", outline="white", width=2)
            alarm_canvas.grid(row=ROW_ALARM, column=col, padx=(3 + extra_left, 3), pady=3)
            self.loop_status_widgets[loop_num]["alarm"] = (alarm_canvas, alarm_light)
            
            sensor_canvas = tk.Canvas(table_frame, width=35, height=35, bg=Theme.BG_TABLE_HEAD, highlightthickness=0)
            sensor_light = sensor_canvas.create_oval(5, 5, 30, 30, fill="black", outline="white", width=2)
            sensor_canvas.grid(row=ROW_SENSOR, column=col, padx=(3 + extra_left, 3), pady=3)
            self.loop_status_widgets[loop_num]["sensor"] = (sensor_canvas, sensor_light)
            
            car_canvas = tk.Canvas(table_frame, width=35, height=35, bg=Theme.BG_TABLE_HEAD, highlightthickness=0)
            car_light = car_canvas.create_oval(5, 5, 30, 30, fill="black", outline="white", width=2)
            car_canvas.grid(row=ROW_CAR, column=col, padx=(3 + extra_left, 3), pady=3)
            self.loop_status_widgets[loop_num]["car"] = (car_canvas, car_light)
            
            gap_sp_var = tk.StringVar(value="20")
            gap_sp_entry = tk.Entry(table_frame, textvariable=gap_sp_var, width=5, font=("Arial", 10, "bold"), justify="center")
            gap_sp_entry.grid(row=ROW_GAP_SP, column=col, padx=(3 + extra_left, 3), pady=3)
            gap_sp_entry.bind("<Return>", lambda e, l=loop_num: self._save_loop_setpoint(l))
            self.loop_status_widgets[loop_num]["gap_sp"] = gap_sp_var
            
            waste_sp_var = tk.StringVar(value="50")
            waste_sp_entry = tk.Entry(table_frame, textvariable=waste_sp_var, width=5, font=("Arial", 10, "bold"), justify="center")
            waste_sp_entry.grid(row=ROW_WASTE_SP, column=col, padx=(3 + extra_left, 3), pady=3)
            waste_sp_entry.bind("<Return>", lambda e, l=loop_num: self._save_loop_setpoint(l))
            self.loop_status_widgets[loop_num]["waste_sp"] = waste_sp_var
            
            gap_pv_var = tk.StringVar(value="0")
            gap_pv_entry = tk.Entry(table_frame, textvariable=gap_pv_var, width=5,
                                    font=("Arial", 10, "bold"), justify="center", state="readonly",
                                    readonlybackground="#E0E0E0")
            gap_pv_entry.grid(row=ROW_GAP_PV, column=col, padx=(3 + extra_left, 3), pady=3)
            self.loop_status_widgets[loop_num]["gap_pv"] = gap_pv_var
            
            waste_pv_var = tk.StringVar(value="0")
            waste_pv_entry = tk.Entry(table_frame, textvariable=waste_pv_var, width=5,
                                      font=("Arial", 10, "bold"), justify="center", state="readonly",
                                      readonlybackground="#E0E0E0")
            waste_pv_entry.grid(row=ROW_WASTE_PV, column=col, padx=(3 + extra_left, 3), pady=3)
            self.loop_status_widgets[loop_num]["waste_pv"] = waste_pv_var
            
            time_canvas = tk.Canvas(table_frame, width=35, height=35, bg=Theme.BG_TABLE_HEAD, highlightthickness=0)
            time_light = time_canvas.create_oval(5, 5, 30, 30, fill="black", outline="white", width=2)
            time_canvas.grid(row=ROW_TIME, column=col, padx=(3 + extra_left, 3), pady=3)
            self.loop_status_widgets[loop_num]["time"] = (time_canvas, time_light)
        
        self.pages[5] = page
    
    def _reset_alarms_and_detectors(self):
        if not self.is_connected or not self.client:
            messagebox.showwarning("هشدار", "ابتدا به PLC متصل شوید!")
            return
        
        def _reset():
            try:
                for card in range(1, 5):
                    address = self.DETECTOR_RESET_ADDRESSES[card]
                    with self.plc_lock:
                        self.client.write_coil(address=address, value=True, device_id=1)
                    time.sleep(0.1)
                    with self.plc_lock:
                        self.client.write_coil(address=address, value=False, device_id=1)
                    time.sleep(0.1)
                
                self.window.after(0, lambda: messagebox.showinfo("موفق", "آلارم‌ها و دتکتورها ریست شدند!"))
            except Exception as e:
                logging.warning(f"خطا در ریست آلارم: {e}")
                self._handle_connection_error()
        
        threading.Thread(target=_reset, daemon=True).start()
    
    def _reset_detector_card(self, card):
        if not self.is_connected or not self.client:
            messagebox.showwarning("هشدار", "ابتدا به PLC متصل شوید!")
            return
        
        def _reset():
            try:
                address = self.DETECTOR_RESET_ADDRESSES[card]
                
                with self.plc_lock:
                    self.client.write_coil(address=address, value=True, device_id=1)
                time.sleep(0.5)
                with self.plc_lock:
                    self.client.write_coil(address=address, value=False, device_id=1)
                
                self.window.after(0, lambda: messagebox.showinfo("موفق", f"کارت دتکتور {card} ریست شد!"))
            except Exception as e:
                logging.warning(f"خطا در ریست کارت دتکتور {card}: {e}")
                self._handle_connection_error()
        
        threading.Thread(target=_reset, daemon=True).start()
    
    def _toggle_detector_disconnect(self, card):
        if not self.is_connected or not self.client:
            messagebox.showwarning("هشدار", "ابتدا به PLC متصل شوید!")
            return
        
        def _toggle():
            try:
                address = self.DETECTOR_ERROR_ADDRESSES[card]
                
                with self.plc_lock:
                    result = self.client.read_coils(address=address, count=1, device_id=1)
                
                if not result.isError():
                    current_status = result.bits[0]
                    new_status = 0 if current_status == 1 else 1
                    
                    with self.plc_lock:
                        self.client.write_coil(address=address, value=new_status, device_id=1)
                    
                    status_text = "وصل" if new_status == 1 else "قطع"
                    self.window.after(0, lambda: messagebox.showinfo("موفق", f"دتکتور {card} {status_text} شد!"))
            except Exception as e:
                logging.warning(f"خطا در قطع/وصل دتکتور {card}: {e}")
                self._handle_connection_error()
        
        threading.Thread(target=_toggle, daemon=True).start()
    
    def _save_loop_setpoint(self, loop_num):
        if not self.is_connected or not self.client:
            messagebox.showwarning("هشدار", "ابتدا به PLC متصل شوید!")
            return
        
        def _save():
            try:
                gap_sp = int(self.loop_status_widgets[loop_num]["gap_sp"].get())
                waste_sp = int(self.loop_status_widgets[loop_num]["waste_sp"].get())
                
                gap_addr = self.LOOP_GAP_ADDRESSES[loop_num]
                waste_addr = self.LOOP_WASTE_ADDRESSES[loop_num]
                
                with self.plc_lock:
                    self.client.write_register(address=gap_addr, value=gap_sp, device_id=1)
                    self.client.write_register(address=waste_addr, value=waste_sp, device_id=1)
                
                self.window.after(0, lambda: messagebox.showinfo("موفق", f"SET POINT لوپ {loop_num} ذخیره شد!"))
            except Exception as e:
                logging.warning(f"خطا در ذخیره SET POINT لوپ {loop_num}: {e}")
                self._handle_connection_error()
        
        threading.Thread(target=_save, daemon=True).start()
    
    def _load_loop_status(self):
        if not self.is_connected or not self.client:
            return
        
        def _load():
            try:
                for card in range(1, 5):
                    address = self.DETECTOR_ERROR_ADDRESSES[card]
                    
                    with self.plc_lock:
                        result = self.client.read_coils(address=address, count=1, device_id=1)
                    
                    if not result.isError():
                        is_error = result.bits[0]
                        color = "red" if is_error else "black"
                        
                        if card in self.card_error_lights:
                            canvas, light_id = self.card_error_lights[card]
                            self.window.after(0, lambda c=canvas, l=light_id, col=color: c.itemconfig(l, fill=col))
                
                for loop_num in range(1, 17):
                    with self.plc_lock:
                        alarm_result = self.client.read_coils(address=self.LOOP_ALARM_STATUS[loop_num], count=1, device_id=1)
                        sensor_result = self.client.read_coils(address=self.LOOP_SENSOR_STATUS[loop_num], count=1, device_id=1)
                        car_result = self.client.read_coils(address=self.LOOP_CAR_STATUS[loop_num], count=1, device_id=1)
                    
                    if not alarm_result.isError():
                        color = "red" if alarm_result.bits[0] else "black"
                        self.window.after(0, lambda l=loop_num, c=color: self._update_loop_light(l, "alarm", c))
                    
                    if not sensor_result.isError():
                        color = "green" if sensor_result.bits[0] else "red"
                        self.window.after(0, lambda l=loop_num, c=color: self._update_loop_light(l, "sensor", c))
                    
                    if not car_result.isError():
                        color = "red" if car_result.bits[0] else "black"
                        self.window.after(0, lambda l=loop_num, c=color: self._update_loop_light(l, "car", c))
                    
                    with self.plc_lock:
                        gap_result = self.client.read_holding_registers(address=self.LOOP_GAP_TIME_ADDRESSES[loop_num], count=1, device_id=1)
                        waste_result = self.client.read_holding_registers(address=self.LOOP_WASTE_TIME_ADDRESSES[loop_num], count=1, device_id=1)
                    
                    if not gap_result.isError():
                        self.window.after(0, lambda l=loop_num, v=gap_result.registers[0]:
                                         self.loop_status_widgets[l]["gap_pv"].set(str(v)))
                    
                    if not waste_result.isError():
                        self.window.after(0, lambda l=loop_num, v=waste_result.registers[0]:
                                         self.loop_status_widgets[l]["waste_pv"].set(str(v)))
            except Exception as e:
                logging.warning(f"خطا در بارگذاری وضعیت لوپ‌ها: {e}")
            finally:
                try: self._loop_status_loading = False
                except Exception: pass

        threading.Thread(target=_load, daemon=True).start()
    
    def _update_loop_light(self, loop_num, light_type, color):
        if loop_num in self.loop_status_widgets:
            if light_type in self.loop_status_widgets[loop_num]:
                canvas, light_id = self.loop_status_widgets[loop_num][light_type]
                canvas.itemconfig(light_id, fill=color)
    
    def _auto_load_loop_status_loop(self):
        if not self.loop_status_page_auto_load_running:
            return
        if self.selected_option != 5:
            self._schedule_after("loop_status", 1500, self._auto_load_loop_status_loop)
            return
        if getattr(self, '_loop_status_loading', False):
            self._schedule_after("loop_status", 1500, self._auto_load_loop_status_loop)
            return
        if self.is_connected and self.client:
            self._loop_status_loading = True
            try:
                self._load_loop_status()
            except Exception as e:
                logging.warning(f"loop_status auto load: {e}")
                self._loop_status_loading = False
            else:
                # _load_loop_status is async thread — clear after a bit
                self.window.after(1200, lambda: setattr(self, '_loop_status_loading', False))
                self._schedule_after("loop_status", 1500, self._auto_load_loop_status_loop)
                return
        self._schedule_after("loop_status", 1500, self._auto_load_loop_status_loop)
    
    def build_ip_time_page(self):
        page = tk.Frame(self.content_frame, bg=Theme.BG_TABLE_HEAD)
        
        ip_section = tk.Frame(page, bg=Theme.BG_TABLE_HEAD)
        ip_section.pack(side="left", padx=30, pady=30, anchor="n")
        
        tk.Label(ip_section, text="تنظیمات IP", bg=Theme.BG_TABLE_HEAD, fg="white",
                font=("Arial", 18, "bold")).pack(pady=20)
        
        ip_frame = tk.Frame(ip_section, bg=Theme.BG_TABLE_HEAD)
        ip_frame.pack(fill="x", pady=10)
        
        tk.Label(ip_frame, text="IP Address", bg=Theme.BG_TABLE_HEAD, fg="white",
                font=("Arial", 12, "bold"), width=12, anchor="w").pack(side="left", padx=5)
        
        self.ip_octets = []
        for i in range(4):
            entry = tk.Entry(ip_frame, width=4, font=("Arial", 11), justify="center")
            entry.pack(side="left", padx=2)
            self.ip_octets.append(entry)
        
        netmask_frame = tk.Frame(ip_section, bg=Theme.BG_TABLE_HEAD)
        netmask_frame.pack(fill="x", pady=10)
        
        tk.Label(netmask_frame, text="Netmask", bg=Theme.BG_TABLE_HEAD, fg="white",
                font=("Arial", 12, "bold"), width=12, anchor="w").pack(side="left", padx=5)
        
        self.netmask_octets = []
        for i in range(4):
            entry = tk.Entry(netmask_frame, width=4, font=("Arial", 11), justify="center")
            entry.pack(side="left", padx=2)
            self.netmask_octets.append(entry)
        
        gateway_frame = tk.Frame(ip_section, bg=Theme.BG_TABLE_HEAD)
        gateway_frame.pack(fill="x", pady=10)
        
        tk.Label(gateway_frame, text="Gateway", bg=Theme.BG_TABLE_HEAD, fg="white",
                font=("Arial", 12, "bold"), width=12, anchor="w").pack(side="left", padx=5)
        
        self.gateway_octets = []
        for i in range(4):
            entry = tk.Entry(gateway_frame, width=4, font=("Arial", 11), justify="center")
            entry.pack(side="left", padx=2)
            self.gateway_octets.append(entry)
        
        refresh_ip_btn = tk.Button(ip_section, text="Refresh", bg="#4CAF50", fg="white",
                                    font=("Arial", 12, "bold"), width=10,
                                    command=self._refresh_ip_settings)
        refresh_ip_btn.pack(pady=20)
        
        set_ip_btn = tk.Button(ip_section, text="Set New IP", bg="#2196F3", fg="white",
                                font=("Arial", 12, "bold"), width=12,
                                command=self._set_new_ip)
        set_ip_btn.pack(pady=10)
        
        time_section = tk.Frame(page, bg=Theme.BG_TABLE_HEAD)
        time_section.pack(side="right", padx=30, pady=30, anchor="n")
        
        today_frame = tk.Frame(time_section, bg=Theme.BG_TABLE_HEAD)
        today_frame.pack(fill="x", pady=20)
        
        tk.Label(today_frame, text="امروز", bg=Theme.BG_TABLE_HEAD, fg="white",
                font=("Arial", 18, "bold")).pack(pady=10)
        
        day_frame = tk.Frame(today_frame, bg=Theme.BG_TABLE_HEAD)
        day_frame.pack(fill="x", pady=5)
        
        self.today_day_var = tk.StringVar(value="چهارشنبه")
        today_day_combo = ttk.Combobox(day_frame, textvariable=self.today_day_var,
                                        values=self.day_names,
                                        state="readonly", width=12,
                                        font=("Arial", 11), justify="center")
        today_day_combo.pack(side="left", padx=5)
        
        # ساعت و دو تاریخ زیر هم — عمودی
        time_frame = tk.Frame(today_frame, bg=Theme.BG_TABLE_HEAD)
        time_frame.pack(fill="x", pady=5)
        tk.Label(time_frame, text="ساعت", bg=Theme.BG_TABLE_HEAD, fg="white",
                font=("Arial", 12, "bold"), width=12, anchor="center").pack()
        time_row = tk.Frame(time_frame, bg=Theme.BG_TABLE_HEAD)
        time_row.pack(pady=2)
        self.today_hour = tk.Entry(time_row, width=4, font=("Arial", 11), justify="center",
                                    state="readonly", readonlybackground="#FF9800")
        self.today_hour.pack(side="left", padx=2)
        self.today_minute = tk.Entry(time_row, width=4, font=("Arial", 11), justify="center",
                                      state="readonly", readonlybackground="#FF9800")
        self.today_minute.pack(side="left", padx=2)
        self.today_second = tk.Entry(time_row, width=4, font=("Arial", 11), justify="center",
                                      state="readonly", readonlybackground="#FF9800")
        self.today_second.pack(side="left", padx=2)

        gregorian_frame = tk.Frame(today_frame, bg=Theme.BG_TABLE_HEAD)
        gregorian_frame.pack(fill="x", pady=5)
        tk.Label(gregorian_frame, text="تاریخ میلادی", bg=Theme.BG_TABLE_HEAD, fg="white",
                font=("Arial", 12, "bold"), width=12, anchor="center").pack()
        greg_row = tk.Frame(gregorian_frame, bg=Theme.BG_TABLE_HEAD)
        greg_row.pack(pady=2)
        self.today_g_year = tk.Entry(greg_row, width=5, font=("Arial", 11), justify="center",
                                      state="readonly", readonlybackground="#FF9800")
        self.today_g_year.pack(side="left", padx=2)
        self.today_g_month = tk.Entry(greg_row, width=3, font=("Arial", 11), justify="center",
                                       state="readonly", readonlybackground="#FF9800")
        self.today_g_month.pack(side="left", padx=2)
        self.today_g_day = tk.Entry(greg_row, width=3, font=("Arial", 11), justify="center",
                                     state="readonly", readonlybackground="#FF9800")
        self.today_g_day.pack(side="left", padx=2)

        shamsi_frame = tk.Frame(today_frame, bg=Theme.BG_TABLE_HEAD)
        shamsi_frame.pack(fill="x", pady=5)
        tk.Label(shamsi_frame, text="تاریخ شمسی", bg=Theme.BG_TABLE_HEAD, fg="white",
                font=("Arial", 12, "bold"), width=12, anchor="center").pack()
        shamsi_row = tk.Frame(shamsi_frame, bg=Theme.BG_TABLE_HEAD)
        shamsi_row.pack(pady=2)
        self.today_s_year = tk.Entry(shamsi_row, width=5, font=("Arial", 11), justify="center",
                                      state="readonly", readonlybackground="#FF9800")
        self.today_s_year.pack(side="left", padx=2)
        self.today_s_month = tk.Entry(shamsi_row, width=3, font=("Arial", 11), justify="center",
                                       state="readonly", readonlybackground="#FF9800")
        self.today_s_month.pack(side="left", padx=2)
        self.today_s_day = tk.Entry(shamsi_row, width=3, font=("Arial", 11), justify="center",
                                     state="readonly", readonlybackground="#FF9800")
        self.today_s_day.pack(side="left", padx=2)
        
        set_time_frame = tk.Frame(time_section, bg=Theme.BG_TABLE_HEAD)
        set_time_frame.pack(fill="x", pady=20)
        
        tk.Label(set_time_frame, text="تنظیم زمان", bg=Theme.BG_TABLE_HEAD, fg="white",
                font=("Arial", 18, "bold")).pack(pady=10)
        btn_row = tk.Frame(set_time_frame, bg=Theme.BG_TABLE_HEAD)
        btn_row.pack(fill="x", pady=10)
        refresh_time_btn = tk.Button(btn_row, text="Refresh", bg="#4CAF50", fg="white",
                                      font=("Arial", 12, "bold"), width=12, height=2,
                                      bd=1, relief="raised", cursor="hand2",
                                      command=self._refresh_time_settings)
        try:
            refresh_time_btn.configure(ipady=6, ipadx=8)
        except Exception:
            pass
        refresh_time_btn.pack(side="left", padx=6, expand=True, fill="x")
        set_time_btn = tk.Button(btn_row, text="SET", bg="#2563EB", fg="white",
                                  font=("Arial", 13, "bold"), width=14, height=2,
                                  bd=1, relief="raised", cursor="hand2",
                                  command=self._set_time)
        try:
            set_time_btn.configure(ipady=8, ipadx=10)
        except Exception:
            pass
        set_time_btn.pack(side="left", padx=6, expand=True, fill="x")
        
        set_day_frame = tk.Frame(set_time_frame, bg=Theme.BG_TABLE_HEAD)
        set_day_frame.pack(fill="x", pady=5)
        
        self.set_day_var = tk.StringVar(value="چهارشنبه")
        set_day_combo = ttk.Combobox(set_day_frame, textvariable=self.set_day_var,
                                      values=self.day_names,
                                      state="readonly", width=12,
                                      font=("Arial", 11), justify="center")
        set_day_combo.pack(side="left", padx=5)
        
        set_time_input_frame = tk.Frame(set_time_frame, bg=Theme.BG_TABLE_HEAD)
        set_time_input_frame.pack(fill="x", pady=5)
        tk.Label(set_time_input_frame, text="ساعت", bg=Theme.BG_TABLE_HEAD, fg="white",
                font=("Arial", 12, "bold"), width=12, anchor="center").pack()
        set_time_row = tk.Frame(set_time_input_frame, bg=Theme.BG_TABLE_HEAD)
        set_time_row.pack(pady=2)
        self.set_hour = tk.Entry(set_time_row, width=4, font=("Arial", 11), justify="center",
                                  bg="#F44336", fg="white")
        self.set_hour.pack(side="left", padx=2)
        self.set_minute = tk.Entry(set_time_row, width=4, font=("Arial", 11), justify="center",
                                    bg="#F44336", fg="white")
        self.set_minute.pack(side="left", padx=2)
        self.set_second = tk.Entry(set_time_row, width=4, font=("Arial", 11), justify="center",
                                    bg="#F44336", fg="white")
        self.set_second.pack(side="left", padx=2)

        set_gregorian_frame = tk.Frame(set_time_frame, bg=Theme.BG_TABLE_HEAD)
        set_gregorian_frame.pack(fill="x", pady=5)
        tk.Label(set_gregorian_frame, text="تاریخ میلادی", bg=Theme.BG_TABLE_HEAD, fg="white",
                font=("Arial", 12, "bold"), width=12, anchor="center").pack()
        set_greg_row = tk.Frame(set_gregorian_frame, bg=Theme.BG_TABLE_HEAD)
        set_greg_row.pack(pady=2)
        self.set_g_year = tk.Entry(set_greg_row, width=5, font=("Arial", 11), justify="center",
                                    bg="#F44336", fg="white")
        self.set_g_year.pack(side="left", padx=2)
        self.set_g_month = tk.Entry(set_greg_row, width=3, font=("Arial", 11), justify="center",
                                     bg="#F44336", fg="white")
        self.set_g_month.pack(side="left", padx=2)
        self.set_g_day = tk.Entry(set_greg_row, width=3, font=("Arial", 11), justify="center",
                                   bg="#F44336", fg="white")
        self.set_g_day.pack(side="left", padx=2)
        
        dst_frame = tk.Frame(set_time_frame, bg=Theme.BG_TABLE_HEAD)
        dst_frame.pack(fill="x", pady=10)
        self.dst_var = tk.StringVar(value="اول فروردین و آخر شهریور تغییر ساعت اعمال گردد")
        def _dst_colors(val):
            return ("#66BB6A", "black") if val == "اول فروردین و آخر شهریور تغییر ساعت اعمال گردد" else ("#EF5350", "white")
        _dbg, _dfg = _dst_colors(self.dst_var.get())
        self.dst_btn = tk.Button(dst_frame, textvariable=self.dst_var, bg=_dbg, fg=_dfg,
                                 activebackground=_dbg, activeforeground=_dfg,
                                 font=("Arial", 10, "bold"), wraplength=420, justify="center",
                                 bd=1, relief="raised", cursor="hand2", width=52,
                                 command=lambda: self._toggle_dst())
        try:
            self.dst_btn.configure(anchor="center")
        except Exception:
            pass
        self.dst_btn.pack(side="left", padx=5, pady=5, ipady=6, anchor="w")
        self.dst_var.trace_add("write", lambda *_a, b=self.dst_btn: b.configure(
            bg=_dst_colors(self.dst_var.get())[0], fg=_dst_colors(self.dst_var.get())[1],
            activebackground=_dst_colors(self.dst_var.get())[0], activeforeground=_dst_colors(self.dst_var.get())[1]))
        try:
            # مقدار اولیه از PLC اگر قبلا خوانده شده، رنگ را هماهنگ کن
            self.window.after(300, lambda: self.dst_var.set(self.dst_var.get()))
        except Exception:
            pass
        
        # دکمه SET به کنار Refresh منتقل شد — این یکی حذف شد
        
        self.pages[6] = page
    
    def _update_octet(self, octets_list, index, value):
        try:
            octets_list[index].delete(0, "end")
            octets_list[index].insert(0, value)
        except:
            pass
    
    def _set_entry_text(self, entry, text):
        try:
            entry.configure(state="normal")
            entry.delete(0, "end")
            entry.insert(0, text)
            if entry.cget("state") == "readonly":
                entry.configure(state="readonly")
        except:
            pass
    
    def _start_ip_time_live(self):
        if getattr(self, '_ip_time_live_running', False):
            return
        self._ip_time_live_running = True
        def _loop():
            while getattr(self, '_ip_time_live_running', False) and self.is_connected and self.client and getattr(self, 'selected_option', None) == 6:
                try:
                    self._refresh_ip_settings(silent=True, live_today=True)
                    self._refresh_time_settings(silent=True, live_today=True)
                except Exception:
                    pass
                import time as _t
                _t.sleep(2)
            self._ip_time_live_running = False
        import threading as _th
        _th.Thread(target=_loop, daemon=True).start()

    def _stop_ip_time_live(self):
        self._ip_time_live_running = False

    def _refresh_ip_settings(self, silent=False, live_today=False):
        if not self.is_connected or not self.client:
            if not silent:
                messagebox.showwarning("هشدار", "ابتدا به PLC متصل شوید!")
            return
        
        def _load():
            try:
                with self.plc_lock:
                    self.client.write_coil(address=self.IP_REFRESH_COIL, value=True, device_id=1)
                time.sleep(0.5)
                with self.plc_lock:
                    self.client.write_coil(address=self.IP_REFRESH_COIL, value=False, device_id=1)
                time.sleep(0.5)
                
                with self.plc_lock:
                    ip_result = self.client.read_holding_registers(address=4702, count=4, device_id=1)
                
                if not ip_result.isError():
                    values = list(reversed(ip_result.registers))
                    for i in range(4):
                        val = values[i]
                        self.window.after(0, self._update_octet, self.ip_octets, i, str(val))
                
                with self.plc_lock:
                    netmask_result = self.client.read_holding_registers(address=4706, count=4, device_id=1)
                
                if not netmask_result.isError():
                    values = list(reversed(netmask_result.registers))
                    for i in range(4):
                        val = values[i]
                        self.window.after(0, self._update_octet, self.netmask_octets, i, str(val))
                
                with self.plc_lock:
                    gateway_result = self.client.read_holding_registers(address=4710, count=4, device_id=1)
                
                if not gateway_result.isError():
                    values = list(reversed(gateway_result.registers))
                    for i in range(4):
                        val = values[i]
                        self.window.after(0, self._update_octet, self.gateway_octets, i, str(val))
                
                if not silent:
                    self.window.after(0, lambda: messagebox.showinfo("موفق", "تنظیمات IP بارگذاری شد!"))
            except Exception as e:
                logging.warning(f"خطا در بارگذاری IP: {e}")
                if not silent:
                    self._handle_connection_error()
        
        threading.Thread(target=_load, daemon=True).start()
        # امروز باید زنده باشد حتی اگر IP جدا باشد — حلقه live را روشن کن
        if live_today:
            self._start_ip_time_live()
    
    def _set_new_ip(self):
        if not self.is_connected or not self.client:
            messagebox.showwarning("هشدار", "ابتدا به PLC متصل شوید!")
            return
        
        def _save():
            try:
                ip_values = list(reversed([int(octet.get()) for octet in self.ip_octets]))
                netmask_values = list(reversed([int(octet.get()) for octet in self.netmask_octets]))
                gateway_values = list(reversed([int(octet.get()) for octet in self.gateway_octets]))
                
                with self.plc_lock:
                    self.client.write_registers(address=4702, values=ip_values, device_id=1)
                    self.client.write_registers(address=4706, values=netmask_values, device_id=1)
                    self.client.write_registers(address=4710, values=gateway_values, device_id=1)
                
                time.sleep(0.3)
                with self.plc_lock:
                    self.client.write_coil(address=self.IP_SET_COIL, value=True, device_id=1)
                time.sleep(0.5)
                with self.plc_lock:
                    self.client.write_coil(address=self.IP_SET_COIL, value=False, device_id=1)
                
                self.window.after(0, lambda: messagebox.showinfo("موفق", "IP جدید ذخیره و اعمال شد!"))
            except Exception as e:
                logging.warning(f"خطا در ذخیره IP: {e}")
                self._handle_connection_error()
        
        threading.Thread(target=_save, daemon=True).start()
    
    def _refresh_time_settings(self, silent=False, live_today=False):
        if not self.is_connected or not self.client:
            if not silent:
                messagebox.showwarning("هشدار", "ابتدا به PLC متصل شوید!")
            return
        
        def _load():
            try:
                # اگر auto live است و کاربر دارد دستی می‌نویسد، فیلدهای SET را نخوان تا نپرد
                is_live = bool(live_today)
                editing_set = False
                try:
                    focused = self.window.focus_get()
                    editing_set = focused in (getattr(self, 'set_hour', None), getattr(self, 'set_minute', None),
                                              getattr(self, 'set_second', None), getattr(self, 'set_g_year', None),
                                              getattr(self, 'set_g_month', None), getattr(self, 'set_g_day', None))
                except Exception:
                    pass
                with self.plc_lock:
                    time_result = self.client.read_holding_registers(address=5409, count=3, device_id=1)
                
                if not time_result.isError():
                    sec = time_result.registers[0]
                    minute = time_result.registers[1]
                    hour = time_result.registers[2]
                    
                    self.window.after(0, self._set_entry_text, self.today_second, f"{sec:02d}")
                    self.window.after(0, self._set_entry_text, self.today_minute, f"{minute:02d}")
                    self.window.after(0, self._set_entry_text, self.today_hour, f"{hour:02d}")
                    
                    if not (is_live and editing_set):
                        self.window.after(0, self._set_entry_text, self.set_second, f"{sec:02d}")
                        self.window.after(0, self._set_entry_text, self.set_minute, f"{minute:02d}")
                        self.window.after(0, self._set_entry_text, self.set_hour, f"{hour:02d}")
                
                with self.plc_lock:
                    year_result = self.client.read_holding_registers(address=4193, count=1, device_id=1)
                    month_result = self.client.read_holding_registers(address=4206, count=1, device_id=1)
                    day_result = self.client.read_holding_registers(address=4208, count=1, device_id=1)
                
                if not year_result.isError() and not month_result.isError() and not day_result.isError():
                    y = year_result.registers[0]
                    mo = month_result.registers[0]
                    d = day_result.registers[0]
                    
                    self.window.after(0, self._set_entry_text, self.today_s_year, str(y))
                    self.window.after(0, self._set_entry_text, self.today_s_month, str(mo))
                    self.window.after(0, self._set_entry_text, self.today_s_day, str(d))
                
                with self.plc_lock:
                    g_year_result = self.client.read_holding_registers(address=4246, count=1, device_id=1)
                    g_month_result = self.client.read_holding_registers(address=4248, count=1, device_id=1)
                    g_day_result = self.client.read_holding_registers(address=4249, count=1, device_id=1)
                    day_of_week_result = self.client.read_holding_registers(address=4247, count=1, device_id=1)
                
                if not g_year_result.isError() and not g_month_result.isError() and not g_day_result.isError():
                    gy = g_year_result.registers[0]
                    gmo = g_month_result.registers[0]
                    gd = g_day_result.registers[0]
                    
                    self.window.after(0, self._set_entry_text, self.today_g_year, f"{gy:04d}")
                    self.window.after(0, self._set_entry_text, self.today_g_month, f"{gmo:02d}")
                    self.window.after(0, self._set_entry_text, self.today_g_day, f"{gd:02d}")
                    
                    if not (is_live and editing_set):
                        self.window.after(0, self._set_entry_text, self.set_g_year, f"{gy:04d}")
                        self.window.after(0, self._set_entry_text, self.set_g_month, f"{gmo:02d}")
                        self.window.after(0, self._set_entry_text, self.set_g_day, f"{gd:02d}")
                    
                    if not day_of_week_result.isError():
                        raw = day_of_week_result.registers[0]
                        if 1 <= raw <= 7:
                            v = raw - 1
                        elif raw == 0:
                            v = 6
                        else:
                            v = (raw - 1) % 7
                        if 0 <= v < len(self.WEEKDAY_4247_NAMES):
                            self.window.after(0, lambda: self.today_day_var.set(self.WEEKDAY_4247_NAMES[v]))
                            if not (is_live and editing_set):
                                self.window.after(0, lambda: self.set_day_var.set(self.WEEKDAY_4247_NAMES[v]))
                
                with self.plc_lock:
                    dst_result = self.client.read_holding_registers(address=self.DST_ADDRESS, count=1, device_id=1)
                
                if not dst_result.isError():
                    dst_value = dst_result.registers[0]
                    if dst_value == 0:
                        self.window.after(0, lambda: self.dst_var.set("اول فروردین و آخر شهریور تغییر ساعت اعمال گردد"))
                    else:
                        self.window.after(0, lambda: self.dst_var.set("تغییری در زمان صورت نگیرد"))
                
                if not silent:
                    self.window.after(0, lambda: messagebox.showinfo("موفق", "زمان بارگذاری شد!"))
            except Exception as e:
                logging.warning(f"خطا در بارگذاری زمان: {e}")
                self._handle_connection_error()
        
        threading.Thread(target=_load, daemon=True).start()
    
    def _toggle_dst(self):
        if not self.is_connected or not self.client:
            messagebox.showwarning("هشدار", "ابتدا به PLC متصل شوید!")
            return
        cur = self.dst_var.get()
        nxt = "تغییری در زمان صورت نگیرد" if cur == "اول فروردین و آخر شهریور تغییر ساعت اعمال گردد" else "اول فروردین و آخر شهریور تغییر ساعت اعمال گردد"
        self.dst_var.set(nxt)
        dst_value = 0 if nxt == "اول فروردین و آخر شهریور تغییر ساعت اعمال گردد" else 1
        def _save():
            try:
                with self.plc_lock:
                    r = self.client.write_register(address=self.DST_ADDRESS, value=dst_value, device_id=1)
                    if hasattr(r, 'isError') and r.isError():
                        raise RuntimeError(f"DST write error {r}")
                logging.info(f"DST 7496 <- {dst_value} ({nxt})")
            except Exception as e:
                logging.warning(f"DST toggle failed: {e}")
                self._handle_connection_error()
        import threading as _th
        _th.Thread(target=_save, daemon=True).start()

    def _set_time(self):
        if not self.is_connected or not self.client:
            messagebox.showwarning("هشدار", "ابتدا به PLC متصل شوید!")
            return
        
        def _save():
            try:
                hour = int(self.set_hour.get())
                minute = int(self.set_minute.get())
                second = int(self.set_second.get())
                
                year = int(self.set_g_year.get())
                month = int(self.set_g_month.get())
                day = int(self.set_g_day.get())
                
                try:
                    sel = self.set_day_var.get().strip()
                    if sel in self.day_names:
                        day_of_week = self.day_names.index(sel) + 1
                    else:
                        raise ValueError()
                except Exception:
                    from datetime import datetime as _dt2
                    dt = _dt2(year, month, day)
                    w = dt.weekday()
                    day_of_week = (w + 1) if w < 6 else 7
                
                with self.plc_lock:
                    self.client.write_register(address=4246, value=year, device_id=1)
                    self.client.write_register(address=4247, value=day_of_week, device_id=1)
                    self.client.write_register(address=4248, value=month, device_id=1)
                    self.client.write_register(address=4249, value=day, device_id=1)
                    self.client.write_register(address=4250, value=hour, device_id=1)
                    self.client.write_register(address=4251, value=minute, device_id=1)
                    self.client.write_register(address=4252, value=second, device_id=1)
                
                time.sleep(0.3)
                with self.plc_lock:
                    self.client.write_coil(address=self.TIME_SET_COIL, value=True, device_id=1)
                time.sleep(0.5)
                with self.plc_lock:
                    self.client.write_coil(address=self.TIME_SET_COIL, value=False, device_id=1)
                
                self.window.after(0, lambda: messagebox.showinfo("موفق", "زمان با موفقیت تنظیم شد!"))
            except Exception as e:
                logging.warning(f"خطا در ذخیره زمان: {e}")
                self._handle_connection_error()
                self.window.after(0, lambda: messagebox.showerror("خطا", f"خطا در ذخیره زمان: {e}"))
        
        threading.Thread(target=_save, daemon=True).start()
    
    def build_lamp_test_page(self):
        page = tk.Frame(self.content_frame, bg=Theme.BG_TABLE_HEAD)
        
        title_frame = tk.Frame(page, bg=Theme.BG_TABLE_HEAD)
        title_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(title_frame, text="تست لامپ‌ها", bg=Theme.BG_TABLE_HEAD, fg="white",
                font=("Arial", 20, "bold")).pack()
        
        main_frame = tk.Frame(page, bg=Theme.BG_TABLE_HEAD)
        main_frame.pack(fill="both", expand=True, padx=20, pady=10)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=0)
        main_frame.grid_rowconfigure(0, weight=1)

        canvas_wrap = tk.Frame(main_frame, bg=Theme.BG_TABLE_HEAD)
        canvas_wrap.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.lamp_test_canvas = tk.Canvas(canvas_wrap, width=700, height=500,
                                           bg=Theme.BG_TABLE_HEAD, highlightthickness=0)
        self.lamp_test_canvas.pack(expand=True)

        control_frame = tk.Frame(main_frame, bg=Theme.BG_TABLE_HEAD, width=260)
        control_frame.grid(row=0, column=1, sticky="ns", padx=(10, 0), pady=10)
        control_frame.pack_propagate(False)
        control_frame.grid_propagate(False)
        
        tk.Label(control_frame, text="حالت تست لامپ:", bg=Theme.BG_TABLE_HEAD, fg="white",
                font=("Arial", 12, "bold")).pack(pady=10)
        
        self.lamp_test_enabled_var = tk.IntVar(value=0)
        self.lamp_test_toggle_btn = tk.Button(control_frame,
                                               text="فعال کردن حالت تست",
                                               bg="#4CAF50", fg="white",
                                               font=("Arial", 12, "bold"), width=18, height=2,
                                               bd=1, relief="raised", cursor="hand2",
                                               command=self._toggle_lamp_test_mode)
        try:
            self.lamp_test_toggle_btn.configure(ipady=10, ipadx=8)
        except Exception:
            pass
        self.lamp_test_toggle_btn.pack(pady=10, fill="x", padx=10)

        self.lamp_test_status_label = tk.Label(control_frame, text="وضعیت: غیرفعال (PLC)",
                                                bg="#78909C", fg="white",
                                                font=("Arial", 11, "bold"), width=20, height=2, bd=1, relief="groove")
        try:
            self.lamp_test_status_label.configure(ipady=6)
        except Exception:
            pass
        self.lamp_test_status_label.pack(pady=10, fill="x", padx=10)

        self.LAMP_TEST_MODE_PASSWORD = "er161720"
        self.lamp_test_momentary_var = tk.StringVar(value="لحظه‌ای")
        self._prev_lamp_test_mode = "لحظه‌ای"
        tk.Label(control_frame, text="حالت چراغ:", bg=Theme.BG_TABLE_HEAD, fg="white",
                font=("Arial", 10, "bold")).pack(pady=(6, 2))
        self.lamp_test_mode_combo = ttk.Combobox(control_frame, textvariable=self.lamp_test_momentary_var,
                                                  values=["لحظه‌ای", "دائمی"],
                                                  state="readonly", width=12, justify="center")
        self.lamp_test_mode_combo.pack(pady=2)
        try:
            self.lamp_test_mode_combo.selection_clear()
        except Exception:
            pass
        self.lamp_test_mode_combo.bind("<<ComboboxSelected>>", self._on_lamp_test_mode_select)
        
        tk.Label(control_frame, text="کنترل پارت‌ها:", bg=Theme.BG_TABLE_HEAD, fg="white",
                font=("Arial", 12, "bold")).pack(pady=10)
        
        all_on_btn = tk.Button(control_frame, text="روشن کردن همه", 
                               bg="#4CAF50", fg="white",
                               font=("Arial", 11, "bold"), width=15,
                               command=lambda: self._set_all_lamps(True))
        all_on_btn.pack(pady=5)
        
        all_off_btn = tk.Button(control_frame, text="خاموش کردن همه", 
                                bg="#F44336", fg="white",
                                font=("Arial", 11, "bold"), width=15,
                                command=lambda: self._set_all_lamps(False))
        all_off_btn.pack(pady=5)
        
        self._draw_lamp_test_lights()
        
        self.lamp_test_running = False
        self.lamp_test_lights_colors = {}
        self.lamp_test_keepalive_running = False

        self.pages[7] = page

    def _on_lamp_test_mode_select(self, event=None):
        new_val = self.lamp_test_momentary_var.get()
        if new_val == getattr(self, '_prev_lamp_test_mode', "لحظه‌ای"):
            try:
                self.lamp_test_mode_combo.selection_clear()
                self.window.focus_set()
            except Exception:
                pass
            return
        pwd = None
        try:
            pwd = tk.simpledialog.askstring("رمز حالت چراغ", "رمز را وارد کنید:", show="*", parent=self.window)
        except Exception:
            try:
                import tkinter.simpledialog as _sd
                pwd = _sd.askstring("رمز حالت چراغ", "رمز را وارد کنید:", show="*", parent=self.window)
            except Exception:
                pwd = None
        if pwd is None:
            self.lamp_test_momentary_var.set(self._prev_lamp_test_mode)
            try:
                self.lamp_test_mode_combo.selection_clear()
            except Exception:
                pass
            return
        if pwd.strip() != getattr(self, 'LAMP_TEST_MODE_PASSWORD', "er161720"):
            messagebox.showerror("رمز اشتباه", "رمز نادرست است — حالت تغییر نکرد.", parent=self.window)
            self.lamp_test_momentary_var.set(self._prev_lamp_test_mode)
            try:
                self.lamp_test_mode_combo.selection_clear()
            except Exception:
                pass
            return
        self._prev_lamp_test_mode = new_val
        self._rebind_lamp_test_lights()
        try:
            self.lamp_test_mode_combo.selection_clear()
            self.window.focus_set()
        except Exception:
            pass
    
    def _refresh_lamp_test_info(self):
        try:
            name = (self.name_var.get() or "").strip() if hasattr(self, 'name_var') else ""
            ip = ""
            port = ""
            try:
                ip = self.ip_entry.get().strip() if hasattr(self, 'ip_entry') else ""
                port = self.port_entry.get().strip() if hasattr(self, 'port_entry') else ""
            except Exception:
                pass
            if not name and hasattr(self, 'load_json'):
                try:
                    data = self.load_json()
                    for it in data:
                        if it.get("ip", "").strip() == ip and ip:
                            name = it.get("name", "")
                            break
                except Exception:
                    pass
            if not name:
                name = "—"
            if not ip:
                ip = "—"
            else:
                if port and port != "502":
                    ip = f"{ip}:{port}"
            self.sidebar_conn_name.configure(text=name)
            self.sidebar_conn_ip.configure(text=ip)
        except Exception:
            pass

    def _draw_lamp_test_lights(self):
        canvas = self.lamp_test_canvas
        canvas.delete("all")

        # ── دقیقا همسان با draw_intersection_map — پالت مطابق عکس ──
        W, H = 700, 500
        PAPER    = "#7EC87E"
        SIDEWALK = "#D8D2C4"
        ROAD     = "#404040"
        CURB     = "#B8B0A0"
        canvas.create_rectangle(0, 0, W, H, fill=PAPER, outline="")
        canvas.create_rectangle(245, 0, 455, H, fill=SIDEWALK, outline="")
        canvas.create_rectangle(0, 145, W, 355, fill=SIDEWALK, outline="")
        for cx, cy in [(245, 145), (455, 145), (245, 355), (455, 355)]:
            canvas.create_oval(cx-18, cy-18, cx+18, cy+18, fill=SIDEWALK, outline=CURB, width=1)
        canvas.create_rectangle(260, 0, 440, H, fill=ROAD, outline="")
        canvas.create_rectangle(0, 160, W, 340, fill=ROAD, outline="")

        for y in range(0, 160, 25):
            canvas.create_line(350, y, 350, y+12, fill="white", width=3)
        for y in range(340, H, 25):
            canvas.create_line(350, y, 350, y+12, fill="white", width=3)
        for x in range(0, 280, 25):
            canvas.create_line(x, 250, x+12, 250, fill="white", width=3)
        for x in range(420, W, 25):
            canvas.create_line(x, 250, x+12, 250, fill="white", width=3)
        canvas.create_line(335, 0, 335, 145, fill="white", width=1)
        canvas.create_line(365, 0, 365, 145, fill="white", width=1)
        canvas.create_line(335, 355, 335, H, fill="white", width=1)
        canvas.create_line(365, 355, 365, H, fill="white", width=1)
        canvas.create_line(0, 235, 245, 235, fill="white", width=1)
        canvas.create_line(0, 265, 245, 265, fill="white", width=1)
        canvas.create_line(455, 235, W, 235, fill="white", width=1)
        canvas.create_line(455, 265, W, 265, fill="white", width=1)

        for i in range(0, 180, 15):
            canvas.create_line(260+i, 160, 260+i+7, 160, fill="white", width=8)
            canvas.create_line(260+i, 340, 260+i+7, 340, fill="white", width=8)
        for i in range(0, 180, 15):
            canvas.create_line(260, 160+i, 260, 160+i+7, fill="white", width=8)
            canvas.create_line(440, 160+i, 440, 160+i+7, fill="white", width=8)
        canvas.create_line(260, 152, 440, 152, fill="white", width=3)
        canvas.create_line(260, 348, 440, 348, fill="white", width=3)
        canvas.create_line(252, 160, 252, 340, fill="white", width=3)
        canvas.create_line(448, 160, 448, 340, fill="white", width=3)
        for pts in [
            [(245, 145), (260, 145), (245, 160)],
            [(455, 145), (440, 145), (455, 160)],
            [(245, 355), (260, 355), (245, 340)],
            [(455, 355), (440, 355), (455, 340)],
        ]:
            canvas.create_polygon(pts, fill=SIDEWALK, outline=CURB, width=1)

        canvas.create_line(285, 100, 285, 145, fill="white", width=4, arrow=tk.LAST)
        canvas.create_line(325, 100, 325, 145, fill="white", width=4, arrow=tk.LAST)
        canvas.create_line(375, 400, 375, 355, fill="white", width=4, arrow=tk.LAST)
        canvas.create_line(415, 400, 415, 355, fill="white", width=4, arrow=tk.LAST)
        canvas.create_line(560, 175, 455, 175, fill="white", width=4, arrow=tk.LAST)
        canvas.create_line(560, 215, 455, 215, fill="white", width=4, arrow=tk.LAST)
        canvas.create_line(140, 285, 245, 285, fill="white", width=4, arrow=tk.LAST)
        canvas.create_line(140, 325, 245, 325, fill="white", width=4, arrow=tk.LAST)

        # مکان گروه‌ها — شمال چپ، غرب پایین، شرق بالا + جابجایی 7/8↔3/4 + جابجایی 1↔2 در تست
        CX, CY = 350, 250
        parts_layout = [
            (285, 72,  1, "V"),
            (325, 72,  2, "V"),
            (585, 175, 3, "H"),
            (585, 215, 4, "H"),
            (375, 428, 5, "V"),
            (415, 428, 6, "V"),
            (105, 285, 8, "H"),
            (105, 325, 7, "H"),
        ]

        def _is_north(y): return y < CY
        def _is_east(x):  return x > CX

        # لیبل PART خارج چهارراه — هماهنگ با جفت‌های نزدیک و جابجایی‌ها
        label_pos = {
            1: (325, 18),  2: (285, 18),
            3: (640, 175), 4: (640, 215),
            5: (375, 482), 6: (415, 482),
            7: (55,  325), 8: (55,  285),
        }

        self.lamp_test_lights = {}
        self.lamp_test_lights_colors = {}
        base = self.LAMP_TEST_BASE_ADDRESS

        for x, y, part_num, orient in parts_layout:

            if orient == "V":
                canvas.create_rectangle(x-14, y-38, x+14, y+38, fill="#1a1a1a", outline="#555", width=2)
                if _is_north(y):
                    positions = [
                        ("green",  "#00FF00", base + (part_num-1)*3 + 2, x, y-22),
                        ("yellow", "#FFFF00", base + (part_num-1)*3 + 1, x, y),
                        ("red",    "#FF0000", base + (part_num-1)*3,     x, y+22),
                    ]
                else:
                    positions = [
                        ("red",    "#FF0000", base + (part_num-1)*3,     x, y-22),
                        ("yellow", "#FFFF00", base + (part_num-1)*3 + 1, x, y),
                        ("green",  "#00FF00", base + (part_num-1)*3 + 2, x, y+22),
                    ]
            else:
                canvas.create_rectangle(x-38, y-14, x+38, y+14, fill="#1a1a1a", outline="#555", width=2)
                if _is_east(x):
                    positions = [
                        ("red",    "#FF0000", base + (part_num-1)*3,     x-22, y),
                        ("yellow", "#FFFF00", base + (part_num-1)*3 + 1, x,    y),
                        ("green",  "#00FF00", base + (part_num-1)*3 + 2, x+22, y),
                    ]
                else:
                    positions = [
                        ("green",  "#00FF00", base + (part_num-1)*3 + 2, x-22, y),
                        ("yellow", "#FFFF00", base + (part_num-1)*3 + 1, x,    y),
                        ("red",    "#FF0000", base + (part_num-1)*3,     x+22, y),
                    ]

            for light_name, color, addr, lx2, ly2 in positions:
                light_id = canvas.create_oval(lx2-10, ly2-10, lx2+10, ly2+10,
                                              fill="#333333", outline="black", width=2)
                key = f"part{part_num}_{light_name}"
                is_momentary = (getattr(self, 'lamp_test_momentary_var', None).get() == "لحظه‌ای" if getattr(self, 'lamp_test_momentary_var', None) else True)
                self.lamp_test_lights[key] = {"id": light_id, "address": addr, "color": color, "state": False}
                self.lamp_test_lights_colors[light_id] = color
                if is_momentary:
                    canvas.tag_bind(light_id, "<ButtonPress-1>", lambda e, k=key: self._lamp_press(k))
                    canvas.tag_bind(light_id, "<ButtonRelease-1>", lambda e, k=key: self._lamp_release(k))
                    canvas.tag_bind(light_id, "<Leave>", lambda e, k=key: self._lamp_release(k))
                else:
                    canvas.tag_bind(light_id, "<Button-1>", lambda e, k=key: self._toggle_lamp(k))

        self.lamp_test_positions = [(x, y, f"PART {p}", p) for x, y, p, _ in parts_layout]
    
    def _toggle_lamp_test_mode(self):
        if not self.is_connected or not self.client:
            messagebox.showwarning("هشدار", "ابتدا به PLC متصل شوید!")
            return
        import time as _t_guard
        now = _t_guard.time()
        if now - getattr(self, '_last_lamp_test_toggle', 0) < 1.5:
            return
        self._last_lamp_test_toggle = now
        
        current_value = self.lamp_test_enabled_var.get()
        new_value = 1 - current_value
        if new_value == 1:
            if not messagebox.askyesno("تایید حالت تست",
                                       "تمام لامپ ها خاموش میشوند !!"):
                return
            try:
                self.lamp_test_toggle_btn.configure(state="disabled")
                self.window.after(1500, lambda: self.lamp_test_toggle_btn.configure(state="normal"))
            except Exception:
                pass
        
        def _write():
            try:
                with self.plc_lock:
                    self.client.write_register(address=self.LAMP_TEST_MODE_ADDRESS, value=new_value, device_id=1)
                
                self.lamp_test_enabled_var.set(new_value)
                
                if new_value == 1:
                    self.window.after(0, lambda: self.lamp_test_toggle_btn.configure(
                        text="غیرفعال کردن حالت تست", bg="#F44336"))
                    self.window.after(0, lambda: self.lamp_test_status_label.configure(
                        text="وضعیت: فعال (PLC)", bg="#4CAF50"))
                    self.window.after(0, self._start_lamp_test_keepalive)
                else:
                    self._stop_lamp_test_keepalive()
                    try:
                        with self.plc_lock:
                            for _info in list(self.lamp_test_lights.values()):
                                try:
                                    self.client.write_coil(address=_info["address"], value=False, device_id=1)
                                except Exception:
                                    pass
                                _info["state"] = False
                    except Exception:
                        pass
                    self.window.after(0, lambda: self.lamp_test_toggle_btn.configure(
                        text="فعال کردن حالت تست", bg="#4CAF50"))
                    self.window.after(0, lambda: self.lamp_test_status_label.configure(
                        text="وضعیت: غیرفعال (PLC)", bg="#78909C"))
                    self.window.after(0, lambda: self._set_all_lamps_visual(False))
            
            except Exception as e:
                logging.warning(f"خطا در تغییر حالت تست: {e}")
                self._handle_connection_error()
        
        threading.Thread(target=_write, daemon=True).start()

    def _start_lamp_test_keepalive(self):
        if self.lamp_test_keepalive_running:
            return
        self.lamp_test_keepalive_running = True
        def _loop():
            while self.lamp_test_keepalive_running and self.is_connected and self.client:
                try:
                    if self.lamp_test_enabled_var and self.lamp_test_enabled_var.get() == 1:
                        with self.plc_lock:
                            self.client.write_register(address=self.LAMP_TEST_MODE_ADDRESS, value=1, device_id=1)
                        # دائمی: دوباره True نگه دار؛ لحظه‌ای: چیزی را زنده نگه ندار (با رها شدن خودش 0 می‌شود)
                        if not self._lamp_is_momentary():
                            on_coils = [(info["address"], info["id"], info["color"])
                                        for info in self.lamp_test_lights.values() if info.get("state")]
                            for addr, _lid, _col in on_coils:
                                try:
                                    with self.plc_lock:
                                        self.client.write_coil(address=addr, value=True, device_id=1)
                                except Exception:
                                    break
                    else:
                        break
                except Exception:
                    break
                time.sleep(0.5)
            self.lamp_test_keepalive_running = False
        threading.Thread(target=_loop, daemon=True).start()

    def _stop_lamp_test_keepalive(self):
        self.lamp_test_keepalive_running = False

    def _exit_lamp_test_mode(self):
        self._stop_lamp_test_keepalive()
        if not self.is_connected or not self.client:
            return
        def _write():
            try:
                with self.plc_lock:
                    self.client.write_register(address=self.LAMP_TEST_MODE_ADDRESS, value=0, device_id=1)
                    # همه کویل‌های تست را یک‌بار 0 کن تا چراغ روشن نماند
                    for _info in list(self.lamp_test_lights.values()):
                        try:
                            self.client.write_coil(address=_info["address"], value=False, device_id=1)
                        except Exception:
                            pass
                        _info["state"] = False
            except Exception:
                pass
            self.window.after(0, lambda: self.lamp_test_enabled_var.set(0) if self.lamp_test_enabled_var else None)
            self.window.after(0, lambda: self.lamp_test_toggle_btn.configure(text="فعال کردن حالت تست", bg="#4CAF50") if hasattr(self, 'lamp_test_toggle_btn') else None)
            self.window.after(0, lambda: self.lamp_test_status_label.configure(text="وضعیت: غیرفعال (PLC)", bg="#78909C") if hasattr(self, 'lamp_test_status_label') else None)
            self.window.after(0, lambda: self._set_all_lamps_visual(False))
        threading.Thread(target=_write, daemon=True).start()

    def _on_window_close(self):
        try:
            self._stop_lamp_test_keepalive()
        except Exception:
            pass
        try:
            self._stop_police_alive()
        except Exception:
            pass
        if self.is_connected and self.client and getattr(self, "lamp_test_enabled_var", None) is not None:
            try:
                if self.lamp_test_enabled_var.get() == 1:
                    try:
                        with self.plc_lock:
                            try:
                                self.client.write_register(address=self.LAMP_TEST_MODE_ADDRESS, value=0, device_id=1)
                            except Exception:
                                pass
                            for _info in list(getattr(self, "lamp_test_lights", {}).values()):
                                try:
                                    self.client.write_coil(address=_info["address"], value=False, device_id=1)
                                except Exception:
                                    pass
                    except Exception:
                        pass
            except Exception:
                pass
        try:
            self.window.destroy()
        except Exception:
            pass

    def _lamp_is_momentary(self):
        try:
            return (self.lamp_test_momentary_var.get() == "لحظه‌ای")
        except Exception:
            return True

    def _rebind_lamp_test_lights(self):
        try:
            is_m = self._lamp_is_momentary()
            for key, info in list(getattr(self, 'lamp_test_lights', {}).items()):
                lid = info["id"]
                try:
                    self.lamp_test_canvas.tag_unbind(lid, "<Button-1>")
                    self.lamp_test_canvas.tag_unbind(lid, "<ButtonPress-1>")
                    self.lamp_test_canvas.tag_unbind(lid, "<ButtonRelease-1>")
                    self.lamp_test_canvas.tag_unbind(lid, "<Leave>")
                except Exception:
                    pass
                if is_m:
                    self.lamp_test_canvas.tag_bind(lid, "<ButtonPress-1>", lambda e, k=key: self._lamp_press(k))
                    self.lamp_test_canvas.tag_bind(lid, "<ButtonRelease-1>", lambda e, k=key: self._lamp_release(k))
                    self.lamp_test_canvas.tag_bind(lid, "<Leave>", lambda e, k=key: self._lamp_release(k))
                else:
                    self.lamp_test_canvas.tag_bind(lid, "<Button-1>", lambda e, k=key: self._toggle_lamp(k))
        except Exception:
            pass

    def _lamp_press(self, key):
        if not self.is_connected or not self.client:
            messagebox.showwarning("هشدار", "ابتدا به PLC متصل شوید!")
            return
        if self.lamp_test_enabled_var.get() == 0:
            messagebox.showinfo("اطلاع", "ابتدا حالت تست را فعال کنید!")
            return
        if not self._lamp_is_momentary():
            return self._toggle_lamp(key)
        lamp_info = self.lamp_test_lights[key]
        def _write():
            try:
                with self.plc_lock:
                    self.client.write_coil(address=lamp_info["address"], value=True, device_id=1)
                lamp_info["state"] = True
                self.window.after(0, lambda: self.lamp_test_canvas.itemconfig(lamp_info["id"], fill=lamp_info["color"]))
            except Exception as e:
                logging.warning(f"press lamp {key}: {e}")
                self._handle_connection_error()
        import threading as _th
        _th.Thread(target=_write, daemon=True).start()

    def _lamp_release(self, key):
        if not self.is_connected or not self.client:
            return
        if self.lamp_test_enabled_var.get() == 0:
            return
        if not self._lamp_is_momentary():
            return
        lamp_info = self.lamp_test_lights.get(key)
        if not lamp_info:
            return
        def _write():
            try:
                with self.plc_lock:
                    self.client.write_coil(address=lamp_info["address"], value=False, device_id=1)
                lamp_info["state"] = False
                self.window.after(0, lambda: self.lamp_test_canvas.itemconfig(lamp_info["id"], fill="#333333"))
            except Exception as e:
                logging.warning(f"release lamp {key}: {e}")
                self._handle_connection_error()
        import threading as _th
        _th.Thread(target=_write, daemon=True).start()

    def _toggle_lamp(self, key):
        if not self.is_connected or not self.client:
            messagebox.showwarning("هشدار", "ابتدا به PLC متصل شوید!")
            return
        
        if self.lamp_test_enabled_var.get() == 0:
            messagebox.showinfo("اطلاع", "ابتدا حالت تست را فعال کنید!")
            return
        
        if self._lamp_is_momentary():
            return self._lamp_press(key)
        
        lamp_info = self.lamp_test_lights[key]
        new_state = not lamp_info["state"]
        
        def _write():
            try:
                with self.plc_lock:
                    self.client.write_coil(address=lamp_info["address"], 
                                          value=new_state, device_id=1)
                
                lamp_info["state"] = new_state
                
                if new_state:
                    self.window.after(0, lambda: self.lamp_test_canvas.itemconfig(
                        lamp_info["id"], fill=lamp_info["color"]))
                else:
                    self.window.after(0, lambda: self.lamp_test_canvas.itemconfig(
                        lamp_info["id"], fill="#333333"))
            
            except Exception as e:
                logging.warning(f"خطا در تغییر وضعیت چراغ: {e}")
                self._handle_connection_error()
        
        threading.Thread(target=_write, daemon=True).start()
    
    def _set_all_lamps(self, state):
        if not self.is_connected or not self.client:
            messagebox.showwarning("هشدار", "ابتدا به PLC متصل شوید!")
            return
        
        if self.lamp_test_enabled_var.get() == 0:
            messagebox.showinfo("اطلاع", "ابتدا حالت تست را فعال کنید!")
            return
        if self._lamp_is_momentary() and state:
            messagebox.showinfo("اطلاع", "در حالت لحظه‌ای، روشن کردن دائمی ممکن نیست.\nحالت را به «دائمی» تغییر دهید.")
            return
        
        def _write():
            try:
                with self.plc_lock:
                    for key, lamp_info in self.lamp_test_lights.items():
                        self.client.write_coil(address=lamp_info["address"], 
                                              value=state, device_id=1)
                        lamp_info["state"] = state
                
                for key, lamp_info in self.lamp_test_lights.items():
                    if state:
                        self.window.after(0, lambda lid=lamp_info["id"], 
                                         c=lamp_info["color"]: 
                                         self.lamp_test_canvas.itemconfig(lid, fill=c))
                    else:
                        self.window.after(0, lambda lid=lamp_info["id"]: 
                                         self.lamp_test_canvas.itemconfig(lid, fill="#333333"))
            
            except Exception as e:
                logging.warning(f"خطا در تغییر وضعیت همه چراغ‌ها: {e}")
                self._handle_connection_error()
        
        threading.Thread(target=_write, daemon=True).start()
    
    def _set_all_lamps_visual(self, state):
        for key, lamp_info in self.lamp_test_lights.items():
            lamp_info["state"] = state
            if state:
                self.lamp_test_canvas.itemconfig(lamp_info["id"], fill=lamp_info["color"])
            else:
                self.lamp_test_canvas.itemconfig(lamp_info["id"], fill="#333333")
    
    def update_lamp_on_canvas(self, canvas, lamp_id, color):
        if lamp_id not in self.map_lights:
            return
        
        lights = self.map_lights[lamp_id]
        
        bright_colors = {"red": "#FF0000", "yellow": "#FFFF00", "green": "#00FF00"}
        dim_colors = {"red": "#330000", "yellow": "#333300", "green": "#003300"}
        
        for c in ["red", "yellow", "green"]:
            if c == color:
                fill = bright_colors[c]
            else:
                fill = dim_colors[c]
            canvas.itemconfig(lights[c], fill=fill)
    
    def _read_lamp_color(self, addresses):
        with self.plc_lock:
            green_result = self.client.read_coils(address=addresses["green"], count=1, device_id=1)
            green_on = not green_result.isError() and green_result.bits[0]
            
            yellow_result = self.client.read_coils(address=addresses["yellow"], count=1, device_id=1)
            yellow_on = not yellow_result.isError() and yellow_result.bits[0]
            
            red_result = self.client.read_coils(address=addresses["red"], count=1, device_id=1)
            red_on = not red_result.isError() and red_result.bits[0]
        
        if green_on:
            color = "green"
        elif yellow_on:
            color = "yellow"
        elif red_on:
            color = "red"
        else:
            color = "off"
        
        return {
            "color": color,
            "status": {"green": green_on, "yellow": yellow_on, "red": red_on}
        }
    
    def _read_register(self, address, count=1):
        with self.plc_lock:
            result = self.client.read_holding_registers(address=address, count=count, device_id=1)
        return result
    
    def _read_coil(self, address):
        with self.plc_lock:
            result = self.client.read_coils(address=address, count=1, device_id=1)
        return result
    
    def update_lights_from_plc(self):
        if not hasattr(self, 'map_lights'):
            return
        
        if self.demo_mode and not self.is_connected:
            self.current_phase = (self.current_phase % 8) + 1
            for phase_num in range(1, 9):
                if phase_num == self.current_phase:
                    color = "green"
                elif phase_num == (self.current_phase % 8) + 1:
                    color = "yellow"
                else:
                    color = "red"
                
                if phase_num in self.phase_light_canvases:
                    self._set_phase_light(self.phase_light_canvases[phase_num], color)
                if phase_num in self.map_lights:
                    self.update_lamp_on_canvas(self.traffic_canvas, phase_num, color)
            return
        
        if not self.is_connected or not self.client:
            return
        
        for phase_num, addresses in self.lamp_mapping.items():
            try:
                result = self._read_lamp_color(addresses)
                self.lamp_status[phase_num] = result["status"]
                self.window.after(0, self.update_lamp_on_canvas,
                                   self.traffic_canvas, phase_num, result["color"])
            except Exception as e:
                logging.warning(f"خطا نقشه فاز {phase_num}: {e}")
        
        for phase_num, addresses in self.phase_lamp_mapping.items():
            try:
                result = self._read_lamp_color(addresses)
                if phase_num in self.phase_light_canvases:
                    self.window.after(0, self._set_phase_light,
                                       self.phase_light_canvases[phase_num], result["color"])
            except Exception as e:
                logging.warning(f"خطا چراغ بالای فاز {phase_num}: {e}")
    
    def _set_phase_light(self, light_dict, color):
        colors = {"red": "#FF0000", "yellow": "#FFFF00", "green": "#00FF00"}
        dim = {"red": "#550000", "yellow": "#555500", "green": "#005500"}
        
        canvas = light_dict.get("canvas")
        for c in ["red", "yellow", "green"]:
            fill = colors[c] if c == color else dim[c]
            canvas.itemconfig(light_dict[c], fill=fill)
    
    def _on_entry_submit(self, address, entry, row_key=None):
        if not self.is_connected:
            return
        
        value_str = entry.get().strip()
        
        if not value_str:
            return
        
        try:
            value = int(value_str)
            
            if row_key == "yellow":
                if value > 5:
                    value = 5
                    entry.delete(0, "end")
                    entry.insert(0, "5")
            
            if value < 0 or value > 65535:
                raise ValueError("خارج از محدوده")
        except:
            entry.configure(bg="#FFCDD2")
            self.window.after(1000, lambda: entry.configure(bg=Theme.BG))
            return
        
        def _write():
            try:
                with self.plc_lock:
                    self.client.write_register(address=address, value=value, device_id=1)
                
                self.window.after(0, lambda: self._clear_entry(entry))
                self.window.after(0, lambda: self.settings_status.configure(
                    text="✓ اعمال شد", fg="green"))
            except Exception as e:
                self.window.after(0, lambda: self.settings_status.configure(
                    text=f"❌ خطا: {str(e)}", fg="red"))
                entry.configure(bg="#FFCDD2")
                self._handle_connection_error()
        
        threading.Thread(target=_write, daemon=True).start()
    
    def _clear_entry(self, entry):
        try:
            entry.delete(0, "end")
            entry.configure(bg=Theme.BG)
        except:
            pass
    
    def _on_settings_change(self, setting_name):
        if not self.is_connected:
            return
        
        self.is_editing_settings = True
        
        def _write():
            try:
                if setting_name == "sensors":
                    value = 1 if self.sensors_var.get() == "فعال" else 0
                elif setting_name == "green_time":
                    value = 1 if self.green_time_var.get() == "دستی" else 0
                elif setting_name == "control_mode":
                    control_map = {"اتوماتیک": 0, "پلیس": 1, "دائمی فلش": 2}
                    value = control_map.get(self.control_var.get(), 0)
                
                address = self.SETTINGS_ADDRESSES[setting_name]["address"]
                with self.plc_lock:
                    self.client.write_register(address=address, value=value, device_id=1)
                
                self.window.after(0, lambda: self.settings_status.configure(
                    text="✓ اعمال شد", fg="green"))
                self.window.after(2200, lambda: setattr(self, 'is_editing_settings', False))
                
                if setting_name == "control_mode":
                    self.window.after(300, self._update_police_button)
                    # پلیس — اعلام زنده بودن به PLC
                    try:
                        if self.control_var.get() == "\u067e\u0644\u06cc\u0633":
                            self.window.after(100, self._police_alive_pulse_once)
                            self.window.after(200, self._start_police_alive)
                        else:
                            self._stop_police_alive()
                    except Exception:
                        pass
            except Exception as e:
                self.window.after(0, lambda: self.settings_status.configure(
                    text=f" خطا: {str(e)}", fg="red"))
                self.window.after(2200, lambda: setattr(self, 'is_editing_settings', False))
                self._handle_connection_error()
        
        threading.Thread(target=_write, daemon=True).start()
    
    def _update_police_button(self):
        if hasattr(self, 'control_var'):
            if self.control_var.get() == "پلیس":
                self.next_phase_btn.pack(side="right", padx=10, pady=10)
            else:
                self.next_phase_btn.pack_forget()
    
    def _handle_connection_error(self):
        if not self.connection_lost:
            self.connection_lost = True
            self.window.after(0, self._show_reconnect_dialog)
    
    def _show_reconnect_dialog(self):
        if messagebox.askretrycancel("خطای اتصال", 
                                      "ارتباط با PLC قطع شد!\nآیا می‌خواهید دوباره متصل شوید؟"):
            self._reconnect()
        else:
            self.go_back()
    
    def _reconnect(self):
        ip = self.ip_entry.get()
        port_str = self.port_entry.get()
        
        try:
            port = int(port_str) if port_str else 502
        except:
            port = 502
        
        try:
            self.client = ModbusTcpClient(ip, port=port, timeout=3)
            if self.client.connect():
                self.is_connected = True
                self.connection_lost = False
                self.status_label.configure(text="✓ متصل", fg="green")
                self.connect_btn.configure(text="قطع اتصال", bg="red")
                self.update_tree_status(ip, "متصل")
                self.start_keep_alive()
                self.window.after(500, self.enter_control_page)
            else:
                self._show_reconnect_dialog()
        except:
            self._show_reconnect_dialog()
    
    def reset_light_card(self):
        if not self.is_connected:
            messagebox.showwarning("هشدار", "ابتدا به PLC متصل شوید!")
            return
        
        if messagebox.askyesno("تایید ریست", "آیا از ریست کارت چراغ ها مطمئن هستید؟"):
            self.write_coil(2101, True)
            self.window.after(1000, lambda: self.write_coil(2101, False))
    
    def write_coil(self, address, value):
        if not self.is_connected or not self.client:
            return
        
        def _write():
            try:
                with self.plc_lock:
                    self.client.write_coil(address=address, value=value, device_id=1)
            except Exception as e:
                logging.warning(f"خطا نوشتن Coil {address}: {e}")
                self._handle_connection_error()
        
        threading.Thread(target=_write, daemon=True).start()
    
    def start_auto_update(self):
        if not self.auto_update_running:
            self.auto_update_running = True
            threading.Thread(target=self._fast_lights_loop, daemon=True).start()
            self._auto_update_loop()
            self.start_phase_count_update()
    
    def stop_auto_update(self):
        self.auto_update_running = False
        self.stop_phase_count_update()
    
    def _fast_lights_loop(self):
        while self.auto_update_running:
            if self.is_connected and self.client and self.selected_option == 0:
                try:
                    for phase_num, addresses in self.lamp_mapping.items():
                        result = self._read_lamp_color(addresses)
                        self.lamp_status[phase_num] = result["status"]
                        self.window.after(0, self.update_lamp_on_canvas,
                                         self.traffic_canvas, phase_num, result["color"])
                    
                    for phase_num, addresses in self.phase_lamp_mapping.items():
                        result = self._read_lamp_color(addresses)
                        if phase_num in self.phase_light_canvases:
                            self.window.after(0, self._set_phase_light,
                                             self.phase_light_canvases[phase_num], result["color"])
                except:
                    pass
            
            time.sleep(0.1)
    
    def _auto_update_loop(self):
        if not self.auto_update_running:
            return
        if self.selected_option == 0 and self.is_connected and self.client:
            threading.Thread(target=self._full_refresh, daemon=True).start()
        self._schedule_after("main_auto", 900, self._auto_update_loop)
    
    def _full_refresh(self):
        try:
            result = self._read_register(4535, 1)
            if not result.isError():
                self.work_mode = result.registers[0]
                mode_text = "هوشمند" if self.work_mode == 1 else "نرمال"
                self.window.after(0, lambda: self.mode_label_table.configure(text=mode_text))
            
            result = self._read_register(4505, 1)
            if not result.isError():
                self.current_phase = result.registers[0]
            
            result = self._read_register(5409, 3)
            if not result.isError():
                second = result.registers[0]
                minute = result.registers[1]
                hour = result.registers[2]
                time_str = f"{hour:02d}:{minute:02d}:{second:02d}"
                self.window.after(0, lambda: self.time_big_label.configure(text=time_str))
            
            year_result = self._read_register(4193, 1)
            month_result = self._read_register(4206, 1)
            day_result = self._read_register(4208, 1)
            
            if not year_result.isError() and not month_result.isError() and not day_result.isError():
                y = year_result.registers[0]
                mo = month_result.registers[0]
                d = day_result.registers[0]
                
                shamsi_str = f"{y}/{mo:02d}/{d:02d}"
                miladi_str = self._jalali_to_gregorian(y, mo, d)
                
                self.window.after(0, lambda: self.shamsi_big_label.configure(text=shamsi_str))
                self.window.after(0, lambda: self.miladi_big_label.configure(text=miladi_str))

                # روز هفته صفحه اصلی فقط نمایش — از 5414 (1=دوشنبه .. 7=یکشنبه)، فقط خواندن
                try:
                    wd_main = self._read_register(self.WEEKDAY_5414_ADDRESS, 1)
                    if not wd_main.isError():
                        raw = wd_main.registers[0]
                        if 1 <= raw <= 7:
                            v = raw - 1
                        elif raw == 0:
                            v = 6
                        else:
                            v = (raw - 1) % 7
                        if 0 <= v < len(self.day_names):
                            self.window.after(0, lambda n=self.day_names[v]: self.day_label.configure(text=n))
                except Exception:
                    pass
            
            self._read_phase_table_values()
            
            if not self.is_editing_settings:
                self._read_settings_values()
            
            self.window.after(0, self._update_police_button)
        except Exception as e:
            logging.warning(f"خطا در _full_refresh: {e}")
            self._handle_connection_error()
    
    def _read_phase_table_values(self):
        try:
            for key in ["green", "yellow", "red", "all_red", "min", "max"]:
                addresses = self.PHASE_ADDRESSES[key]
                if addresses[0] == 0:
                    continue
                result = self._read_register(addresses[0], 8)
                if not result.isError():
                    for i in range(8):
                        phase_num = i + 1
                        value = result.registers[i]
                        entry_dict = self.phase_entries.get((key, phase_num))
                        if entry_dict:
                            target = entry_dict.get("entry") or entry_dict.get("readonly")
                            if target is None:
                                continue
                            # اگر کاربر روی همین فیلد فوکوس دارد، نخوان تا نپرد
                            try:
                                focused = self.window.focus_get()
                            except Exception:
                                focused = None
                            if focused is target or getattr(self, '_focused_phase_entry', None) is target:
                                continue
                            self.window.after(0, lambda e=target, v=value: self._safe_set_readonly(e, str(v)))
        except Exception as e:
            logging.warning(f"خطا در خواندن جدول فازها: {e}")
    
    def _read_settings_values(self):
        try:
            # اگر کاربر دارد ویرایش می‌کند، اصلا نخوان تا نپرد (2 ثانیه نگهبان)
            if getattr(self, 'is_editing_settings', False):
                return
            try:
                # اگر کامبویی فوکوس دارد، آن را هم نخوان
                focused = self.window.focus_get()
                if focused in (getattr(self, 'sensors_combo', None), getattr(self, 'green_time_combo', None), getattr(self, 'control_combo', None)):
                    return
            except Exception:
                pass
            sensors_result = self._read_register(self.SETTINGS_ADDRESSES["sensors"]["address"], 1)
            if not sensors_result.isError():
                sensors_value = "فعال" if sensors_result.registers[0] == 1 else "غیر فعال"
                if self.sensors_var.get() != sensors_value:
                    self.window.after(0, lambda v=sensors_value: (self.sensors_var.set(v), self.window.after(30, self._apply_main_settings_colors)))
            
            green_result = self._read_register(self.SETTINGS_ADDRESSES["green_time"]["address"], 1)
            if not green_result.isError():
                green_value = "دستی" if green_result.registers[0] == 1 else "اتوماتیک"
                if self.green_time_var.get() != green_value:
                    self.window.after(0, lambda v=green_value: (self.green_time_var.set(v), self.window.after(30, self._apply_main_settings_colors)))
            
            control_result = self._read_register(self.SETTINGS_ADDRESSES["control_mode"]["address"], 1)
            if not control_result.isError():
                control_map = {0: "اتوماتیک", 1: "پلیس", 2: "دائمی فلش"}
                control_value = control_map.get(control_result.registers[0], "اتوماتیک")
                if self.control_var.get() != control_value:
                    self.window.after(0, lambda v=control_value: (self.control_var.set(v), self.window.after(30, self._apply_main_settings_colors)))
                else:
                    self.window.after(0, self._apply_main_settings_colors)
        except Exception as e:
            logging.warning(f"خطا در خواندن تنظیمات: {e}")
    
    def _safe_set_readonly(self, entry, value):
        try:
            try:
                focused = self.window.focus_get()
            except Exception:
                focused = None
            if focused is entry or getattr(self, '_focused_phase_entry', None) is entry:
                return
            # اگر entry قابل ویرایش (تک‌فیلدی) است، state را readonly نکن
            try:
                is_editable = False
                for _d in self.phase_entries.values():
                    if _d.get("entry") is entry and _d.get("is_editable"):
                        is_editable = True
                        break
                if is_editable:
                    entry.delete(0, "end")
                    entry.insert(0, value)
                    return
            except Exception:
                pass
            entry.configure(state="normal")
            entry.delete(0, "end")
            entry.insert(0, value)
            entry.configure(state="readonly")
        except:
            pass

    def _on_phase_entry_focus_in(self, entry):
        try:
            self._focused_phase_entry = entry
            self.is_editing_table = True
            try:
                entry.selection_range(0, "end")
            except Exception:
                pass
        except Exception:
            pass

    def _on_phase_entry_focus_out(self, entry, address, row_key):
        try:
            self._on_phase_entry_submit(entry, address, row_key)
        finally:
            try:
                self._focused_phase_entry = None
            except Exception:
                pass
            # کمی تاخیر تا _read دوباره شروع شود
            try:
                self.window.after(300, lambda: setattr(self, 'is_editing_table', False))
            except Exception:
                self.is_editing_table = False

    def _on_phase_entry_submit(self, entry, address, row_key):
        if not self.is_connected or not self.client:
            try:
                self._focused_phase_entry = None
                self.is_editing_table = False
            except Exception:
                pass
            # در حالت دمو بدون PLC هم مقدار را نگه دار تا کاربر ببیند
            try:
                if getattr(self, 'demo_mode', False):
                    v = entry.get().strip()
                    if v:
                        entry.delete(0, "end")
                        entry.insert(0, v)
                    self._restore_phase_entry_bg(entry)
                    self.settings_status.configure(text="✓ (دمو) ثبت شد", fg="green")
            except Exception:
                pass
            return
        try:
            value_str = entry.get().strip()
            if not value_str:
                try:
                    self._focused_phase_entry = None
                    self.is_editing_table = False
                except Exception:
                    pass
                return
            try:
                value = int(value_str)
            except Exception:
                entry.configure(bg="#FFCDD2")
                self.window.after(900, lambda: self._restore_phase_entry_bg(entry))
                return
            if row_key == "yellow" and value > 5:
                value = 5
                entry.delete(0, "end")
                entry.insert(0, "5")
            if value < 0 or value > 65535:
                raise ValueError("range")
        except Exception:
            try:
                entry.configure(bg="#FFCDD2")
                self.window.after(900, lambda: self._restore_phase_entry_bg(entry))
            except Exception:
                pass
            return
        def _write():
            try:
                # اگر سطر سبز است و حالت اتوماتیک است، اول به دستی سوییچ کن تا PLC بپذیرد
                if row_key == "green":
                    try:
                        if hasattr(self, 'green_time_var') and self.green_time_var.get() == "\u0627\u062a\u0648\u0645\u0627\u062a\u06cc\u06a9":
                            with self.plc_lock:
                                res = self.client.write_register(address=self.SETTINGS_ADDRESSES["green_time"]["address"], value=1, device_id=1)
                            self.window.after(0, lambda: self.green_time_var.set("\u062f\u0633\u062a\u06cc"))
                            self.window.after(0, lambda: self.settings_status.configure(text="زمان سبزها به دستی تغییر کرد", fg="orange"))
                            import time as _t
                            _t.sleep(0.15)
                    except Exception as _e:
                        logging.warning(f"auto switch green_time failed: {_e}")
                with self.plc_lock:
                    result = self.client.write_register(address=address, value=value, device_id=1)
                # بررسی خطای مودباس
                try:
                    if hasattr(result, 'isError') and result.isError():
                        raise RuntimeError(f"PLC error at {address}")
                except Exception as _ie:
                    # اگر isError خودش خطا داد، نادیده بگیر
                    pass
                logging.info(f"write {row_key} addr {address} <- {value}")
                self.window.after(0, lambda: self.settings_status.configure(text="✓ اعمال شد", fg="green"))
                # مقدار نوشته شده را نگه دار — تا رفرش بعدی آن را رونویسی نکند
                self.window.after(0, lambda: self._restore_phase_entry_bg(entry))
                self.window.after(0, lambda e=entry, v=str(value): (e.delete(0, "end"), e.insert(0, v)))
            except Exception as e:
                logging.warning(f"write failed {row_key} @{address}={value}: {e}")
                self.window.after(0, lambda: self.settings_status.configure(text=f"❌ خطا: {str(e)}", fg="red"))
                try:
                    self.window.after(0, lambda: entry.configure(bg="#FFCDD2"))
                    self.window.after(0, lambda: self.window.after(900, lambda: self._restore_phase_entry_bg(entry)))
                except Exception:
                    pass
                try:
                    self._handle_connection_error()
                except Exception:
                    pass
            finally:
                try:
                    self.window.after(0, lambda: setattr(self, '_focused_phase_entry', None))
                    self.window.after(800, lambda: setattr(self, 'is_editing_table', False))
                except Exception:
                    pass
        import threading as _th
        _th.Thread(target=_write, daemon=True).start()

    def _restore_phase_entry_bg(self, entry):
        try:
            for _d in self.phase_entries.values():
                if _d.get("entry") is entry:
                    entry.configure(bg=_d.get("color", entry.cget("bg")))
                    return
            entry.configure(bg=entry.cget("bg"))
        except Exception:
            pass
    
    def _jalali_to_gregorian(self, jy, jm, jd):
        try:
            gy = jy + 621
            if jm <= 6:
                day_of_year = (jm - 1) * 31 + jd
            else:
                day_of_year = 186 + (jm - 7) * 30 + jd
            
            if (gy % 4 == 0 and gy % 100 != 0) or (gy % 400 == 0):
                start_day = 80
            else:
                start_day = 79
            
            total_day = start_day + day_of_year - 1
            days_in_year = 366 if ((gy % 4 == 0 and gy % 100 != 0) or (gy % 400 == 0)) else 365
            
            if total_day < days_in_year:
                gm, gd = self._day_to_month_day(total_day, days_in_year == 366)
                return f"{gy}/{gm:02d}/{gd:02d}"
            else:
                total_day -= days_in_year
                gy += 1
                if (gy % 4 == 0 and gy % 100 != 0) or (gy % 400 == 0):
                    days_in_next_year = 366
                else:
                    days_in_next_year = 365
                gm, gd = self._day_to_month_day(total_day, days_in_next_year == 366)
                return f"{gy}/{gm:02d}/{gd:02d}"
        except:
            return "----/--/--"
    
    def _day_to_month_day(self, day_of_year, is_leap):
        days_in_months = [31, 29 if is_leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        month = 1
        for days_in_month in days_in_months:
            if day_of_year < days_in_month:
                return month, day_of_year + 1
            day_of_year -= days_in_month
            month += 1
        return 12, 31
    
    def show_page(self, idx):
        # خروج خودکار از حالت تست هنگام ترک تب 7
        if getattr(self, 'selected_option', None) == 7 and idx != 7:
            if getattr(self, 'lamp_test_enabled_var', None) and self.lamp_test_enabled_var.get() == 1:
                self._exit_lamp_test_mode()

        for widget in self.content_frame.winfo_children():
            widget.pack_forget()

        for i, btn in enumerate(self.option_buttons):
            if i == idx:
                btn.configure(relief="sunken", bd=3)
            else:
                btn.configure(relief="raised", bd=1)

        self.selected_option = idx
        
        if idx == 0:
            if 0 not in self.pages:
                self.build_main_page()
            self.pages[0].pack(fill="both", expand=True)
            self.start_auto_update()
        elif idx == 1:
            if 1 not in self.pages:
                self.build_timing_page()
            self.pages[1].pack(fill="both", expand=True)
            self.stop_auto_update()
            if not self.timing_page_auto_load_running:
                self.timing_page_auto_load_running = True
                self._auto_load_timing_loop()
        elif idx == 2:
            if 2 not in self.pages:
                self.build_blink_page()
            self.pages[2].pack(fill="both", expand=True)
            self.stop_auto_update()
            if not self.blink_page_auto_load_running:
                self.blink_page_auto_load_running = True
                self._auto_load_blink_loop()
        elif idx == 3:
            if 3 not in self.pages:
                self.build_part_settings_page()
            self.pages[3].pack(fill="both", expand=True)
            self.stop_auto_update()
            if not self.part_settings_page_auto_load_running:
                self.part_settings_page_auto_load_running = True
                self._auto_load_part_settings_loop()
        elif idx == 4:
            if 4 not in self.pages:
                self.build_loop_settings_page()
            self.pages[4].pack(fill="both", expand=True)
            self.stop_auto_update()
            if not self.loop_settings_page_auto_load_running:
                self.loop_settings_page_auto_load_running = True
                self._auto_load_loop_loop()
        elif idx == 5:
            if 5 not in self.pages:
                self.build_loop_status_page()
            self.pages[5].pack(fill="both", expand=True)
            self.stop_auto_update()
            if not self.loop_status_page_auto_load_running:
                self.loop_status_page_auto_load_running = True
                self._auto_load_loop_status_loop()
        elif idx == 6:
            if 6 not in self.pages:
                self.build_ip_time_page()
            self.pages[6].pack(fill="both", expand=True)
            self.stop_auto_update()
            if self.is_connected and self.client:
                try:
                    self.window.after(250, lambda: self._refresh_ip_settings(silent=True, live_today=True))
                    self.window.after(600, lambda: self._refresh_time_settings(silent=True, live_today=True))
                    self._start_ip_time_live()
                except Exception:
                    pass
        elif idx == 7:
            if 7 not in self.pages:
                self.build_lamp_test_page()
            self.pages[7].pack(fill="both", expand=True)
            self.stop_auto_update()
            try:
                self.window.after(300, self._poll_lamp_test_status)
            except Exception:
                pass
            try:
                self._refresh_lamp_test_info()
                self.window.after(200, self._refresh_lamp_test_info)
            except Exception:
                pass
            try:
                self._stop_ip_time_live()
            except Exception:
                pass
        else:
            try:
                self._stop_ip_time_live()
            except Exception:
                pass
            self.stop_auto_update()
            self.timing_page_auto_load_running = False
            self.blink_page_auto_load_running = False
            self.part_settings_page_auto_load_running = False
            self.loop_settings_page_auto_load_running = False
            self.loop_status_page_auto_load_running = False
            placeholder = tk.Frame(self.content_frame, bg=Theme.BG)
            placeholder.pack(fill="both", expand=True)
            tk.Label(placeholder, text=f"گزینه {idx+1}", bg=Theme.BG, font=("Arial", 20, "bold")).pack(pady=50)
            tk.Label(placeholder, text="به زودی پیاده‌سازی می‌شود...", bg=Theme.BG, font=("Arial", 14)).pack()
    
    def go_back(self):
        # خروج از تست قبل از قطع
        if getattr(self, 'lamp_test_enabled_var', None) and self.lamp_test_enabled_var.get() == 1:
            self._exit_lamp_test_mode()
        self._stop_lamp_test_keepalive()
        self.stop_auto_update()
        self.timing_page_auto_load_running = False
        self.blink_page_auto_load_running = False
        self.part_settings_page_auto_load_running = False
        self.loop_settings_page_auto_load_running = False
        self.loop_status_page_auto_load_running = False
        self.user_is_editing_timing = False
        self.user_is_editing_blink = False
        self.user_is_editing_part_settings = False
        self.user_is_editing_loops = False
        self.stop_keep_alive()
        self._stop_police_alive()  # disconnect
        if self.is_connected:
            self.disconnect()
        self.control_frame.pack_forget()
        self.login_frame.pack(fill="both", expand=True)
        self.current_page = "login"
    
    def open_another_intersection(self):
        # هر تقاطع یک پروسه جدا — هیچ تداخلی در plc_lock / اتصال / حلقه‌ها نیست
        try:
            # اگر در حالت تست هستیم، قبل از باز کردن پنجره جدید تست را خاموش کن تا لامپ روشن نماند
            if getattr(self, 'lamp_test_enabled_var', None) and self.lamp_test_enabled_var.get() == 1:
                try:
                    self._exit_lamp_test_mode()
                except Exception:
                    pass
            path = pathlib.Path(__file__).resolve() if "__file__" in globals() else pathlib.Path("gui_controller_modern.py").resolve()
            # همان پایتون فعلی با همان فایل
            subprocess.Popen([sys.executable, str(path)], cwd=str(path.parent),
                             creationflags=getattr(subprocess, 'DETACHED_PROCESS', 0) | getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0) if os.name == 'nt' else 0)
            self.status_label if hasattr(self, 'status_label') else None
            try:
                messagebox.showinfo("پنجره جدید", "یک پنجره جدید برای تقاطع دیگر باز شد.\nهر پنجره اتصال و تب‌های خودش را دارد — با هم تداخل ندارند.")
            except Exception:
                pass
        except Exception as e:
            logging.warning(f"open_another failed: {e}")
            try:
                messagebox.showerror("خطا", f"باز کردن پنجره جدید ممکن نشد:\n{e}")
            except Exception:
                pass

    def enter_control_page(self):
        self.current_page = "control"
        self.login_frame.pack_forget()
        self.control_frame.pack(fill="both", expand=True)
        self.current_page = "main"
        self.demo_mode = False
        try:
            self._refresh_lamp_test_info()
        except Exception:
            pass
        self.show_page(0)
        try:
            self.window.after(300, self._refresh_lamp_test_info)
        except Exception:
            pass
    
    def add_intersection(self):
        try:
            name = self.new_name_entry.get().strip()
            ip = self.new_ip_entry.get().strip()
            port = self.new_port_entry.get().strip()
            desc = self.new_desc_entry.get().strip()
            
            if not name or not ip:
                self.status_label.configure(text="❌ نام و IP الزامی است!", fg="red")
                return
            
            if not port:
                port = "502"
            
            data = self.load_json()
            for item in data:
                if item.get("name") == name:
                    self.status_label.configure(text="❌ تکراری!", fg="red")
                    return
            
            data.append({"name": name, "ip": ip, "port": port, "desc": desc, "status": "قطع"})
            self.save_json(data)
            
            self.new_name_entry.delete(0, "end")
            self.new_ip_entry.delete(0, "end")
            self.new_ip_entry.insert(0, "192.168.1.")
            self.new_port_entry.delete(0, "end")
            self.new_port_entry.insert(0, "502")
            self.new_desc_entry.delete(0, "end")
            
            self.status_label.configure(text=f"✓ '{name}' ثبت شد!", fg="green")
            self.window.after(100, self.load_data)
        except Exception as e:
            self.status_label.configure(text=f" {str(e)}", fg="red")
    
    def delete_intersection(self):
        try:
            name = self.name_var.get()
            if not name:
                self.status_label.configure(text=" انتخاب کنید!", fg="red")
                return
            if self.is_connected:
                self.disconnect()
            data = self.load_json()
            data = [item for item in data if item.get("name") != name]
            self.save_json(data)
            self.status_label.configure(text=f"✓ '{name}' حذف شد", fg="orange")
            self.window.after(100, self.load_data)
        except Exception as e:
            self.status_label.configure(text=f" {str(e)}", fg="red")
    
    def load_data(self):
        try:
            self.is_updating = True
            for item in self.tree.get_children():
                self.tree.delete(item)
            data = self.load_json()
            names = []
            for item in data:
                self.tree.insert("", "end", values=(
                    item.get("name", ""), item.get("ip", ""), item.get("port", "502"),
                    item.get("desc", ""), item.get("status", "قطع")))
                names.append(item.get("name", ""))
            self.name_combo['values'] = names
            if names and not self.name_var.get():
                self.name_var.set(names[0])
                self.update_fields(names[0])
            self.is_updating = False
        except Exception as e:
            logging.warning(f"خطا: {e}")
            self.is_updating = False
    
    def on_name_selected(self, event):
        if self.is_updating:
            return
        name = self.name_var.get()
        if name:
            self.update_fields(name)
    
    def on_tree_click(self, event):
        if self.is_updating:
            return
        try:
            selected = self.tree.selection()
            if selected:
                name = self.tree.item(selected[0], "values")[0]
                self.is_updating = True
                self.name_var.set(name)
                self.update_fields(name)
                self.is_updating = False
        except Exception as e:
            logging.warning(f"خطا: {e}")
            self.is_updating = False
    
    def update_fields(self, name):
        try:
            data = self.load_json()
            for item in data:
                if item.get("name") == name:
                    self.ip_entry.configure(state="normal")
                    self.ip_entry.delete(0, "end")
                    self.ip_entry.insert(0, item.get("ip", ""))
                    self.ip_entry.configure(state="readonly")
                    self.port_entry.configure(state="normal")
                    self.port_entry.delete(0, "end")
                    self.port_entry.insert(0, item.get("port", "502"))
                    self.port_entry.configure(state="readonly")
                    break
        except Exception as e:
            logging.warning(f"خطا: {e}")
    
    def _on_bulk_ip_click(self):
        def _show_panel():
            try:
                # قبل از جدول اصلی قرار بگیرد تا دیده شود — نه ته صفحه
                self.bulk_ip_frame.pack(fill="x", padx=10, pady=6, before=self.table_frame)
                self.bulk_ip_frame.lift()
            except Exception:
                try:
                    self.bulk_ip_frame.pack(fill="x", padx=10, pady=6)
                    self.bulk_ip_frame.lift()
                except Exception:
                    pass
            try:
                self._build_bulk_rows()
            except Exception as e:
                logging.warning(f"bulk build: {e}")
                try:
                    import traceback as _tb2
                    logging.warning("".join(_tb2.format_exc().splitlines()[-4:]))
                except Exception:
                    pass
            try:
                self._ping_all_bulk()
            except Exception as e:
                logging.warning(f"bulk ping: {e}")
        if getattr(self, 'bulk_ip_unlocked', False):
            _show_panel()
            return
        try:
            import tkinter.simpledialog as _sd
            pwd = _sd.askstring("رمز تنظیم IP گروهی", "رمز را وارد کنید:", show="*", parent=self.window)
        except Exception:
            pwd = None
        if pwd is None:
            return
        if pwd.strip() != "er161720":
            try:
                messagebox.showerror("رمز اشتباه", "رمز نادرست است.", parent=self.window)
            except Exception:
                pass
            return
        self.bulk_ip_unlocked = True
        _show_panel()


    def _build_bulk_rows(self):
        try:
            for w in list(self.bulk_list_frame.winfo_children()):
                try:
                    info = w.grid_info()
                    if info and str(info.get('row')) == '0':
                        continue
                except Exception:
                    pass
                try:
                    w.destroy()
                except Exception:
                    pass
            has_hdr = False
            for w in self.bulk_list_frame.winfo_children():
                try:
                    if str(w.grid_info().get('row')) == '0':
                        has_hdr = True
                        break
                except Exception:
                    pass
            if not has_hdr:
                hdr = tk.Frame(self.bulk_list_frame, bg="#37474F")
                hdr.grid(row=0, column=0, columnspan=9, sticky="ew", padx=2, pady=2)
                for ci, txt in enumerate(["تقاطع", "IP فعلی", "وضعیت", "IP جدید", "Netmask", "Gateway", "", "", "اکسل"]):
                    tk.Label(hdr, text=txt, bg="#37474F", fg="white", font=("Arial", 8, "bold"), width=10 if ci > 2 else 12).grid(row=0, column=ci, padx=1, pady=2)
            data = self.load_json()
            self.bulk_ip_rows = {}
            row_idx = 1
            for item in data:
                name = item.get("name", "")
                ip = item.get("ip", "")
                port = str(item.get("port", "502"))
                row = tk.Frame(self.bulk_list_frame, bg="#263238", highlightbackground="#455A64", highlightthickness=1)
                row.grid(row=row_idx, column=0, columnspan=9, sticky="ew", padx=2, pady=2)
                for c in range(9):
                    row.grid_columnconfigure(c, weight=1)
                tk.Label(row, text=name, bg="#263238", fg="white", font=("Arial", 9, "bold"), width=14, anchor="center", justify="center").grid(row=0, column=0, padx=2, pady=3)
                cur_ip_lbl = tk.Label(row, text=ip, bg="#263238", fg="#B0BEC5", font=("Consolas", 9), width=14, anchor="center", justify="center")
                cur_ip_lbl.grid(row=0, column=1, padx=2, pady=3)
                status_lbl = tk.Label(row, text="در حال تست...", bg="#263238", fg="#FFCA28", font=("Arial", 8, "bold"), width=10, anchor="center", justify="center")
                status_lbl.grid(row=0, column=2, padx=2, pady=3)
                new_ip_var = tk.StringVar(value=ip)
                new_nm_var = tk.StringVar(value="255.255.255.0")
                new_gw_var = tk.StringVar(value="192.168.1.1")
                e_ip = tk.Entry(row, textvariable=new_ip_var, width=14, font=("Consolas", 9), justify="center")
                e_ip.grid(row=0, column=3, padx=2, pady=2)
                e_nm = tk.Entry(row, textvariable=new_nm_var, width=14, font=("Consolas", 9), justify="center")
                e_nm.grid(row=0, column=4, padx=2, pady=2)
                e_gw = tk.Entry(row, textvariable=new_gw_var, width=14, font=("Consolas", 9), justify="center")
                e_gw.grid(row=0, column=5, padx=2, pady=2)
                set_btn = tk.Button(row, text="ست", bg="#4CAF50", fg="white", font=("Arial", 9, "bold"), width=6, command=lambda n=name, ip0=ip, pt=port, v1=new_ip_var, v2=new_nm_var, v3=new_gw_var, lbl=status_lbl: self._set_bulk_ip(n, ip0, pt, v1, v2, v3, lbl))
                set_btn.grid(row=0, column=6, padx=2, pady=2)
                read_btn = tk.Button(row, text="خواندن", bg="#607D8B", fg="white", font=("Arial", 8, "bold"), width=7, command=lambda n=name, ip0=ip, pt=port, v1=new_ip_var, v2=new_nm_var, v3=new_gw_var, lbl=status_lbl: self._read_bulk_ip(n, ip0, pt, v1, v2, v3, lbl))
                read_btn.grid(row=0, column=7, padx=2, pady=2)
                excel_btn = tk.Button(row, text="اکسل", bg="#1E88E5", fg="white", font=("Arial", 8, "bold"), width=6, command=lambda n=name, ip0=ip, pt=port, lbl=status_lbl: self._export_single_bulk_excel(n, ip0, pt, lbl))
                excel_btn.grid(row=0, column=8, padx=2, pady=2)
                self.bulk_ip_rows[name] = {"row": row, "cur_lbl": cur_ip_lbl, "status": status_lbl, "ip": ip, "port": port, "new_ip": new_ip_var, "nm": new_nm_var, "gw": new_gw_var}
                row_idx += 1
            if row_idx == 1:
                tk.Label(self.bulk_list_frame, text="هیچ تقاطعی ثبت نشده", bg="#263238", fg="#B0BEC5", font=("Arial", 10)).grid(row=1, column=0, columnspan=8, pady=10)
        except Exception as e:
            logging.warning(f"build bulk rows: {e}")

    def _ping_all_bulk(self):
        if getattr(self, '_bulk_pinging', False):
            return
        self._bulk_pinging = True
        try:
            self.bulk_ping_status.configure(text="در حال پینگ همه...")
        except Exception:
            pass
        def _do():
            try:
                import socket
                data = self.load_json()
                for item in data:
                    name = item.get("name", "")
                    ip = item.get("ip", "").strip()
                    port = int(str(item.get("port", "502")).strip() or 502)
                    status = "قطع"
                    color = "#FF5252"
                    try:
                        sock = socket.create_connection((ip, port), timeout=1.2)
                        sock.close()
                        status = "فعال"
                        color = "#66BB6A"
                    except Exception:
                        status = "قطع"
                        color = "#FF5252"
                    try:
                        self.window.after(0, lambda n=name, ip0=ip, st=status, c=color: self._apply_bulk_ping_result(n, ip0, st, c))
                    except Exception:
                        pass
            except Exception as e:
                logging.warning(f"ping bulk: {e}")
            finally:
                self._bulk_pinging = False
                try:
                    self.window.after(0, lambda: self.bulk_ping_status.configure(text="پینگ تمام شد"))
                    self.window.after(2000, lambda: self.bulk_ping_status.configure(text=""))
                except Exception:
                    pass
        import threading as _th
        _th.Thread(target=_do, daemon=True).start()

    def _apply_bulk_ping_result(self, name, ip, status, color):
        try:
            for iid in self.tree.get_children():
                vals = list(self.tree.item(iid, "values"))
                if len(vals) >= 2 and vals[1] == ip:
                    vals[4] = status
                    self.tree.item(iid, values=vals)
                    try:
                        self.tree.item(iid, tags=(status,))
                        self.tree.tag_configure("فعال", foreground="#2E7D32")
                        self.tree.tag_configure("قطع", foreground="#B0BEC5")
                    except Exception:
                        pass
                    break
        except Exception:
            pass
        try:
            info = self.bulk_ip_rows.get(name)
            if info:
                lbl = info.get("status")
                if lbl and lbl.winfo_exists():
                    lbl.configure(text=status, fg=color, bg="#263238")
                    try:
                        row = info.get("row")
                        if status == "فعال":
                            row.configure(highlightbackground="#66BB6A")
                        else:
                            row.configure(highlightbackground="#455A64")
                    except Exception:
                        pass
        except Exception:
            pass

    def _collect_intersection_log(self, ip, port):
        client = ModbusTcpClient(ip, port=int(port or 502), timeout=3)
        if not client.connect():
            raise RuntimeError(f"اتصال به {ip}:{port} برقرار نشد")
        try:
            def _rh(addr, cnt):
                r = client.read_holding_registers(address=addr, count=cnt, device_id=1)
                if r.isError():
                    raise RuntimeError(f"read {addr} error")
                return r.registers
            phase_count = _rh(self.MAIN_PHASE_COUNT_READ_ADDRESS, 1)[0]
            # جدول فاز — سبز/زرد/قرمز/ALL_RED/Min/Max هر کدام 8 تا، میانگین بگیر
            phase_rows = {}
            for key, addrs in self.PHASE_ADDRESSES.items():
                try:
                    regs = _rh(addrs[0], 8)
                    phase_rows[key] = regs
                except Exception:
                    phase_rows[key] = [0]*8
            # IP فعلی
            try:
                ip_regs = _rh(4702, 4)
                cur_ip = ".".join(str(x) for x in reversed(ip_regs))
            except Exception:
                cur_ip = ip
            # زمان PLC
            try:
                tr = _rh(5409, 3)
                sec, minute, hour = tr[0], tr[1], tr[2]
                time_str = f"{hour:02d}:{minute:02d}:{sec:02d}"
            except Exception:
                time_str = ""
            return {"phase_count": phase_count, "phase_rows": phase_rows, "cur_ip": cur_ip, "time_str": time_str}
        finally:
            try:
                client.close()
            except Exception:
                pass

    def _build_excel_for_log(self, name, ip, port, log, filepath):
        import openpyxl as _xl
        from openpyxl.styles import Font as _Font, PatternFill as _Fill, Alignment as _Align, Border as _Border, Side as _Side
        wb = _xl.Workbook()
        ws = wb.active
        ws.title = name[:31] if name else "Log"
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.sheet_properties.pageSetUpPr.orientation = "landscape"
        thin = _Side(style="thin", color="B0BEC5")
        border = _Border(left=thin, right=thin, top=thin, bottom=thin)
        hdr_fill = _Fill(start_color="1E3A5F", end_color="1E3A5F", fill_type="solid")
        hdr_font = _Font(color="FFFFFF", bold=True, size=10)
        title_font = _Font(color="0F172A", bold=True, size=14)
        center = _Align(horizontal="center", vertical="center", wrap_text=True)
        ws.merge_cells("A1:I1")
        c = ws["A1"]
        c.value = f"گزارش تقاطع  {name}  —  IP {log.get('cur_ip', ip)}  —  {log.get('time_str','')}"
        c.font = title_font
        c.alignment = _Align(horizontal="center", vertical="center")
        ws.row_dimensions[1].height = 22
        ws["A2"] = f"تعداد فاز: {log.get('phase_count','')}"
        ws["A2"].font = _Font(bold=True, size=11)
        ws["A2"].alignment = center
        ws.merge_cells("A2:I2")
        headers = ["پارامتر", "فاز 1", "فاز 2", "فاز 3", "فاز 4", "فاز 5", "فاز 6", "فاز 7", "فاز 8"]
        row_labels = [("سبز", "green"), ("زرد", "yellow"), ("قرمز", "red"), ("ALL RED", "all_red"), ("Min هوشمند", "min"), ("Max هوشمند", "max")]
        fills = {"green": _Fill(start_color="C8E6C9", end_color="C8E6C9", fill_type="solid"),
                 "yellow": _Fill(start_color="FFF9C4", end_color="FFF9C4", fill_type="solid"),
                 "red": _Fill(start_color="FFCDD2", end_color="FFCDD2", fill_type="solid"),
                 "all_red": _Fill(start_color="F8BBD0", end_color="F8BBD0", fill_type="solid"),
                 "min": _Fill(start_color="DCEDC8", end_color="DCEDC8", fill_type="solid"),
                 "max": _Fill(start_color="FFE0B2", end_color="FFE0B2", fill_type="solid")}
        # هدر
        for ci, h in enumerate(headers, 1):
            cell = ws.cell(row=3, column=ci, value=h)
            cell.font = hdr_font
            cell.fill = hdr_fill
            cell.alignment = center
            cell.border = border
        ws.row_dimensions[3].height = 18
        pr = log.get("phase_rows", {})
        for ri, (label, key) in enumerate(row_labels, 4):
            c0 = ws.cell(row=ri, column=1, value=label)
            c0.font = _Font(bold=True, size=10)
            c0.fill = fills.get(key, _Fill(fill_type=None))
            c0.alignment = center
            c0.border = border
            vals = pr.get(key, [0]*8)
            for ci in range(8):
                v = vals[ci] if ci < len(vals) else ""
                cell2 = ws.cell(row=ri, column=2+ci, value=v)
                cell2.font = _Font(size=10)
                cell2.fill = fills.get(key, _Fill(fill_type=None))
                cell2.alignment = center
                cell2.border = border
            ws.row_dimensions[ri].height = 16
        # عرض ستون‌ها
        ws.column_dimensions["A"].width = 16
        for col in "BCDEFGHI":
            ws.column_dimensions[col].width = 10
        ws.freeze_panes = "B4"
        ws.print_title_rows = "3:3"
        wb.save(filepath)

    def _sanitize_filename(self, s):
        bad = '<>:"/\\|?*'
        for ch in bad:
            s = s.replace(ch, "_")
        s = s.strip()
        return s or "intersection"

    def _export_single_bulk_excel(self, name, ip, port, lbl):
        try:
            lbl.configure(text="اکسل...", fg="#FFCA28")
        except Exception:
            pass
        def _do():
            try:
                log = self._collect_intersection_log(ip, port)
                # پوشه کنار addresses.json یا دسکتاپ
                base_dir = str(pathlib.Path(self.address_file).parent) if getattr(self, 'address_file', None) else str(pathlib.Path.home() / "Desktop")
                safe = self._sanitize_filename(name)
                path = str(pathlib.Path(base_dir) / f"{safe}.xlsx")
                # اگر تکراری بود، شماره بگذار
                if pathlib.Path(path).exists():
                    for k in range(2, 100):
                        cand = str(pathlib.Path(base_dir) / f"{safe}_{k}.xlsx")
                        if not pathlib.Path(cand).exists():
                            path = cand
                            break
                self._build_excel_for_log(name, ip, port, log, path)
                self.window.after(0, lambda: lbl.configure(text="اکسل شد", fg="#66BB6A"))
                self.window.after(0, lambda: messagebox.showinfo("اکسل", f"فایل ساخته شد:\n{path}", parent=self.window))
                try:
                    os.startfile(path)
                except Exception:
                    pass
            except Exception as e:
                logging.warning(f"excel single {name}: {e}")
                self.window.after(0, lambda: lbl.configure(text="خطا", fg="#FF5252"))
                self.window.after(0, lambda: messagebox.showerror("خطا", f"{name}: {e}", parent=self.window))
        import threading as _th
        _th.Thread(target=_do, daemon=True).start()

    def _export_all_bulk_excel(self):
        data = self.load_json()
        if not data:
            try:
                messagebox.showwarning("اکسل", "هیچ تقاطعی ثبت نشده", parent=self.window)
            except Exception:
                pass
            return
        # فعال‌ها را فقط لیست کن
        active = []
        for it in data:
            # اگر پنل باز است و وضعیت خوانده شده، فقط فعال‌ها
            name = it.get("name","")
            info = getattr(self, 'bulk_ip_rows', {}).get(name)
            st = ""
            try:
                st = info.get("status").cget("text") if info and info.get("status") else ""
            except Exception:
                st = ""
            if st == "فعال" or not info:
                active.append(it)
        if not active:
            active = data
        try:
            import tkinter.filedialog as _fd
            folder = _fd.askdirectory(title="پوشه ذخیره اکسل همه تقاطع‌ها", parent=self.window)
        except Exception:
            folder = None
        if not folder:
            return
        # اگر کاربر یک فایل انتخاب کرد، پوشه‌اش را بگیر
        try:
            if pathlib.Path(folder).is_file():
                folder = str(pathlib.Path(folder).parent)
        except Exception:
            pass
        def _do_all():
            ok, fail = 0, 0
            fails = []
            for it in active:
                name = it.get("name","")
                ip = it.get("ip","")
                port = str(it.get("port","502"))
                try:
                    log = self._collect_intersection_log(ip, port)
                    safe = self._sanitize_filename(name) or self._sanitize_filename(ip)
                    path = str(pathlib.Path(folder) / f"{safe}.xlsx")
                    if pathlib.Path(path).exists():
                        for k in range(2, 100):
                            cand = str(pathlib.Path(folder) / f"{safe}_{k}.xlsx")
                            if not pathlib.Path(cand).exists():
                                path = cand
                                break
                    self._build_excel_for_log(name, ip, port, log, path)
                    ok += 1
                    try:
                        self.window.after(0, lambda n=name: self.bulk_ping_status.configure(text=f"اکسل {n} شد"))
                    except Exception:
                        pass
                except Exception as e:
                    fail += 1
                    fails.append(f"{name} ({ip}): {e}")
                    logging.warning(f"excel all {name}: {e}")
            def _done():
                try:
                    self.bulk_ping_status.configure(text=f"تمام: {ok} موفق، {fail} خطا")
                except Exception:
                    pass
                msg = f"{ok} فایل در {folder} ساخته شد"
                if fails:
                    msg += "\n\nخطاها:\n" + "\n".join(fails[:8])
                try:
                    if fail == 0:
                        messagebox.showinfo("اکسل همه", msg, parent=self.window)
                    else:
                        messagebox.showwarning("اکسل همه", msg, parent=self.window)
                except Exception:
                    pass
                try:
                    os.startfile(folder)
                except Exception:
                    pass
            self.window.after(0, _done)
        import threading as _th2
        _th2.Thread(target=_do_all, daemon=True).start()

    def _parse_ip(self, s):
        s = str(s)
        parts = s.strip().split(".")
        if len(parts) != 4:
            raise ValueError("IP باید 4 بخش داشته باشد")
        vals = []
        for p in parts:
            v = int(p.strip())
            if not 0 <= v <= 255:
                raise ValueError("بخش IP خارج از 0..255")
            vals.append(v)
        return vals

    def _read_bulk_ip(self, name, cur_ip, port, v_ip, v_nm, v_gw, lbl):
        if not cur_ip:
            return
        try:
            lbl.configure(text="خواندن...", fg="#FFCA28")
        except Exception:
            pass
        def _do():
            try:
                client = ModbusTcpClient(cur_ip, port=int(port or 502), timeout=3)
                if not client.connect():
                    self.window.after(0, lambda: lbl.configure(text="قطع", fg="#FF5252"))
                    return
                try:
                    client.write_coil(address=self.IP_REFRESH_COIL, value=True, device_id=1)
                    time.sleep(0.5)
                    client.write_coil(address=self.IP_REFRESH_COIL, value=False, device_id=1)
                    time.sleep(0.5)
                except Exception:
                    pass
                ip_r = client.read_holding_registers(address=4702, count=4, device_id=1)
                nm_r = client.read_holding_registers(address=4706, count=4, device_id=1)
                gw_r = client.read_holding_registers(address=4710, count=4, device_id=1)
                try:
                    client.close()
                except Exception:
                    pass
                if not ip_r.isError():
                    vals = list(reversed(ip_r.registers))
                    ip_str = ".".join(str(x) for x in vals)
                    self.window.after(0, lambda: v_ip.set(ip_str))
                if not nm_r.isError():
                    vals = list(reversed(nm_r.registers))
                    nm_str = ".".join(str(x) for x in vals)
                    self.window.after(0, lambda: v_nm.set(nm_str))
                if not gw_r.isError():
                    vals = list(reversed(gw_r.registers))
                    gw_str = ".".join(str(x) for x in vals)
                    self.window.after(0, lambda: v_gw.set(gw_str))
                self.window.after(0, lambda: lbl.configure(text="خوانده شد", fg="#66BB6A"))
                self.window.after(1500, lambda: lbl.configure(text="فعال", fg="#66BB6A"))
            except Exception as e:
                logging.warning(f"read bulk {name}: {e}")
                self.window.after(0, lambda: lbl.configure(text="خطا", fg="#FF5252"))
        import threading as _th2
        _th2.Thread(target=_do, daemon=True).start()

    def _sync_ip_change_to_connection_page(self, name, new_ip):
        try:
            for iid in self.tree.get_children():
                vals = list(self.tree.item(iid, "values"))
                if len(vals) >= 1 and vals[0] == name:
                    vals[1] = new_ip
                    self.tree.item(iid, values=vals)
                    break
        except Exception:
            pass
        try:
            if self.name_var.get() == name:
                self.ip_entry.configure(state="normal")
                self.ip_entry.delete(0, "end")
                self.ip_entry.insert(0, new_ip)
                self.ip_entry.configure(state="readonly")
        except Exception:
            pass
        try:
            info = self.bulk_ip_rows.get(name)
            if info and info.get("cur_lbl") and info["cur_lbl"].winfo_exists():
                info["cur_lbl"].configure(text=new_ip)
                info["ip"] = new_ip
        except Exception:
            pass

    def _set_bulk_ip(self, name, cur_ip, port, v_ip, v_nm, v_gw, lbl):
        if not cur_ip:
            return
        try:
            new_ip_s = v_ip.get().strip()
            new_nm_s = v_nm.get().strip()
            new_gw_s = v_gw.get().strip()
            ip_vals = self._parse_ip(new_ip_s)
            nm_vals = self._parse_ip(new_nm_s)
            gw_vals = self._parse_ip(new_gw_s)
        except Exception as e:
            try:
                messagebox.showerror("IP نامعتبر", str(e), parent=self.window)
            except Exception:
                pass
            return
        if not messagebox.askyesno("تایید ست IP", f"{name} ({cur_ip})\nبه\nIP: {new_ip_s}\nNetmask: {new_nm_s}\nGateway: {new_gw_s}\nتغییر کند؟", parent=self.window):
            return
        try:
            lbl.configure(text="در حال ست...", fg="#FFCA28")
        except Exception:
            pass
        def _do():
            try:
                ip_regs = list(reversed(ip_vals))
                nm_regs = list(reversed(nm_vals))
                gw_regs = list(reversed(gw_vals))
                client = ModbusTcpClient(cur_ip, port=int(port or 502), timeout=3)
                if not client.connect():
                    self.window.after(0, lambda: lbl.configure(text="قطع", fg="#FF5252"))
                    return
                # بعد از ارسال، تعویض انجام‌شده فرض کن — حتی اگر تایید خواندن فعلا نرسد
                try:
                    client.write_registers(address=4702, values=ip_regs, device_id=1)
                except Exception:
                    pass
                time.sleep(0.05)
                try:
                    client.write_registers(address=4706, values=nm_regs, device_id=1)
                except Exception:
                    pass
                time.sleep(0.05)
                try:
                    client.write_registers(address=4710, values=gw_regs, device_id=1)
                except Exception:
                    pass
                time.sleep(0.3)
                try:
                    client.write_coil(address=self.IP_SET_COIL, value=True, device_id=1)
                except Exception:
                    pass
                time.sleep(0.5)
                try:
                    client.write_coil(address=self.IP_SET_COIL, value=False, device_id=1)
                except Exception:
                    pass
                time.sleep(0.5)
                try:
                    client.close()
                except Exception:
                    pass
                self.window.after(0, lambda: lbl.configure(text="ست شد", fg="#66BB6A"))
                try:
                    data = self.load_json()
                    for it in data:
                        if it.get("name") == name:
                            it["ip"] = new_ip_s
                            break
                    self.save_json(data)
                    self.window.after(0, lambda: self._sync_ip_change_to_connection_page(name, new_ip_s))
                    self.window.after(300, self.load_data)
                    self.window.after(500, self._build_bulk_rows)
                    self.window.after(900, self._ping_all_bulk)
                except Exception:
                    pass
            except Exception as e:
                logging.warning(f"set bulk {name}: {e}")
                self.window.after(0, lambda: lbl.configure(text="خطا", fg="#FF5252"))
        import threading as _th3
        _th3.Thread(target=_do, daemon=True).start()

    # ── تست زنده وضعیت تقاطع‌ها در صفحه لاگین — هر 2 ثانیه ──
    def _start_live_status_probe(self):
        if self.live_status_running:
            return
        self.live_status_running = True
        self._live_status_loop()

    def _live_status_loop(self):
        if not self.live_status_running:
            return
        if self.current_page == "login":
            try:
                data = self.load_json()
                if data:
                    import threading as _th
                    _th.Thread(target=self._probe_all_statuses, args=(data,), daemon=True).start()
            except Exception:
                pass
        self._schedule_after("live_status", 2000, self._live_status_loop)

    def _probe_all_statuses(self, data):
        import socket
        for item in data:
            ip = (item.get("ip") or "").strip()
            port = int(item.get("port") or 502)
            if not ip:
                continue
            status = "قطع"
            try:
                sock = socket.create_connection((ip, port), timeout=1.2)
                sock.close()
                status = "متصل"
            except Exception:
                status = "قطع"
            # ستون وضعیت همان ip (async به Tk)
            _ip, _st = ip, status
            try:
                self.window.after(0, lambda ip=_ip, st=_st: self._apply_live_status(ip, st))
            except Exception:
                pass

    def _apply_live_status(self, ip, status):
        # روی TreeView ستون status را متصل/قطع بگذار (رنگ همان متن)
        try:
            for iid in self.tree.get_children():
                vals = list(self.tree.item(iid, "values"))
                if len(vals) >= 2 and vals[1] == ip:
                    vals[4] = status
                    self.tree.item(iid, values=vals)
                    # تگ رنگی اختیاری
                    try:
                        self.tree.item(iid, tags=(status,))
                        self.tree.tag_configure("متصل", foreground="#0a7a2e")
                        self.tree.tag_configure("قطع", foreground="#a0a0a0")
                    except Exception:
                        pass
                    break
        except Exception:
            pass
        # اگر همین ip انتخاب فعلی لاگین است، لیبل وضعیت بالای صفحه را هم هماهنگ کن
        try:
            cur_ip = self.ip_entry.get().strip()
            if cur_ip == ip:
                if status == "متصل":
                    self.status_label.configure(text="وضعیت: متصل", fg="green")
                else:
                    # اگر الان خودمان وصلِ فعال به همین PLC نیستیم، قطع نشان بده
                    if not self.is_connected:
                        self.status_label.configure(text="وضعیت: قطع", fg="gray")
        except Exception:
            pass

    def toggle_connection(self):
        if self.is_connected:
            self.disconnect()
        else:
            self.status_label.configure(text="⏳ در حال اتصال...", fg="blue")
            self.connect_btn.configure(state="disabled")
            thread = threading.Thread(target=self.connect_thread, daemon=True)
            thread.start()
    
    def connect_thread(self):
        ip = self.ip_entry.get()
        port_str = self.port_entry.get()
        try:
            port = int(port_str) if port_str else 502
        except:
            port = 502
        try:
            self.client = ModbusTcpClient(ip, port=port, timeout=3)
            if self.client.connect():
                self.is_connected = True
                self.connection_lost = False
                self.window.after(0, self.on_connect_success, ip)
            else:
                self.window.after(0, self.on_connect_failed, "خطا در اتصال")
        except Exception as e:
            self.window.after(0, self.on_connect_failed, str(e))
    
    def on_connect_success(self, ip):
        self.connect_btn.configure(state="normal", text="قطع اتصال", bg="red")
        self.status_label.configure(text="✓ متصل", fg="green")
        self.update_tree_status(ip, "متصل")
        self.start_keep_alive()
        try:
            if hasattr(self, 'control_var') and self.control_var.get() == "\u067e\u0644\u06cc\u0633":
                self._start_police_alive()
        except Exception:
            pass
        self.window.after(500, self.enter_control_page)
    
    def on_connect_failed(self, error_msg):
        self.connect_btn.configure(state="normal")
        self.status_label.configure(text=f" {error_msg}", fg="red")
    
    def disconnect(self):
        if self.client:
            try:
                self.client.close()
            except:
                pass
        self.is_connected = False
        self.connect_btn.configure(text="اتصال به PLC", bg="green")
        self.status_label.configure(text="وضعیت: قطع", fg="gray")
        ip = self.ip_entry.get()
        self.update_tree_status(ip, "قطع")
        self.stop_keep_alive()
    
    def update_tree_status(self, ip, status):
        try:
            for item in self.tree.get_children():
                if self.tree.item(item, "values")[1] == ip:
                    values = list(self.tree.item(item, "values"))
                    values[4] = status
                    self.tree.item(item, values=values)
                    break
        except:
            pass
    
    def load_json(self):
        try:
            if os.path.exists(self.address_file):
                with open(self.address_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        return []
    
    def save_json(self, data):
        try:
            with open(self.address_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.warning(f"خطا: {e}")
    
    def run(self):
        self.window.mainloop()

if __name__ == "__main__":
    app = TrafficControllerApp()
    app.run()
