import pathlib
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import webbrowser
import json
from license_helper import get_hwid, verify_license_lic

LICENSE_FILE = "license.lic"


def show_license_dialog(parent):
    try:
        from gui_controller_modern import Theme, FONT_SMALL, FONT_MONO  # type: ignore
    except Exception:
        Theme = None
        FONT_SMALL = ("Segoe UI", 9)
        FONT_MONO = ("Consolas", 10, "bold")

    hwid = get_hwid()

    # If parent is the root window, hide it while dialog is open handled by caller
    win = tk.Toplevel(parent)
    win.title("فعال‌سازی B30 Controller")
    win.geometry("560x440")
    win.transient(parent)
    win.grab_set()
    if Theme:
        try:
            win.configure(bg=Theme.BG)
        except Exception:
            pass

    frm = ttk.Frame(win, padding=18)
    frm.pack(fill="both", expand=True)

    ttk.Label(frm, text="کد دستگاه شما:", font=FONT_SMALL).pack(anchor="e")
    h_lbl = ttk.Label(frm, text=hwid, font=FONT_MONO, foreground="#2563EB" if not Theme else Theme.BG_PRIMARY)
    h_lbl.pack(anchor="e", pady=(2, 10))

    ttk.Label(frm, text="پلن را انتخاب کنید:", font=FONT_SMALL).pack(anchor="e", pady=(6, 4))
    plan_var = tk.StringVar(value="base")
    plans = [
        ("پایه — 1 تقاطع / 6 ماهه — 1.5م تومان", "base"),
        ("حرفه‌ای — 5 تقاطع / 1 ساله — 4.5م تومان", "pro"),
        ("نامحدود — دائمی — 9م تومان", "unlimited"),
    ]
    for label, val in plans:
        ttk.Radiobutton(frm, text=label, variable=plan_var, value=val).pack(anchor="e")

    ttk.Label(frm, text="ایمیل (برای دریافت لایسنس):", font=FONT_SMALL).pack(anchor="e", pady=(10, 2))
    email_var = tk.StringVar()
    ent = ttk.Entry(frm, textvariable=email_var, width=38, justify="center")
    ent.pack(anchor="e")
    ent.focus_set()

    info = "پس از پرداخت، فایل license.lic کنار فایل exe قرار می‌گیرد و برنامه فعال می‌شود."
    ttk.Label(frm, text=info, font=FONT_SMALL, foreground="#64748B" if not Theme else Theme.TEXT_MUTED, wraplength=500, justify="right").pack(anchor="e", pady=(10, 6))

    def _open_site():
        email = email_var.get().strip()
        if not email or "@" not in email:
            messagebox.showwarning("ایمیل", "ایمیل معتبر وارد کنید.", parent=win)
            return
        plan = plan_var.get()
        price_map = {"base": 1500000, "pro": 4500000, "unlimited": 9000000}
        amount = price_map.get(plan, 1500000)
        url = f"https://SIM1617.github.io/B30-Controller/?email={email}&plan={plan}&hwid={hwid}&amount={amount}"
        try:
            webbrowser.open(url)
        except Exception:
            pass
        try:
            win.clipboard_clear()
            win.clipboard_append(f"HWID:{hwid} | Email:{email} | Plan:{plan}")
        except Exception:
            pass
        messagebox.showinfo("کپی شد", f"لینک پرداخت در مرورگر باز شد.\nHWID کپی شد: {hwid}\nاگر مرورگر باز نشد، این آدرس را دستی باز کنید:\n{url}", parent=win)

    def _pick_file():
        p = filedialog.askopenfilename(title="انتخاب فایل license.lic", filetypes=[("License", "*.lic"), ("All", "*.*")])
        if not p:
            return
        try:
            data = pathlib.Path(p).read_bytes()
            dest = pathlib.Path(LICENSE_FILE)
            dest.write_bytes(data)
            ok, msg = verify_license_lic(dest)
            if ok:
                messagebox.showinfo("لایسنس", f"فعال شد: {msg}", parent=win)
                try:
                    win.destroy()
                except Exception:
                    pass
                try:
                    parent.deiconify()
                except Exception:
                    pass
            else:
                messagebox.showerror("لایسنس", f"نامعتبر: {msg}", parent=win)
        except Exception as e:
            messagebox.showerror("خطا", str(e), parent=win)

    btn_row = ttk.Frame(frm)
    btn_row.pack(fill="x", pady=(14, 0))
    ttk.Button(btn_row, text="باز کردن صفحه پرداخت", command=_open_site).pack(side="left")
    ttk.Button(btn_row, text="انتخاب فایل license.lic", command=_pick_file).pack(side="left", padx=(8, 0))
    ttk.Button(btn_row, text="خروج", command=lambda: (win.destroy(), parent.destroy())).pack(side="right")

    win.bind("<Return>", lambda _e: _open_site())
    # keep modal
    parent.wait_window(win)


def activate_with_file_dialog(parent):
    p = filedialog.askopenfilename(title="انتخاب فایل license.lic", filetypes=[("License", "*.lic"), ("All", "*.*")])
    if not p:
        return
    try:
        data = pathlib.Path(p).read_bytes()
        dest = pathlib.Path(LICENSE_FILE)
        dest.write_bytes(data)
        ok, msg = verify_license_lic(dest)
        if ok:
            messagebox.showinfo("لایسنس", f"فعال شد: {msg}", parent=parent)
        else:
            messagebox.showerror("لایسنس", f"نامعتبر: {msg}", parent=parent)
    except Exception as e:
        messagebox.showerror("خطا", str(e), parent=parent)

