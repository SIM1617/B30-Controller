import tkinter as tk
from tkinter import ttk, messagebox
from pymodbus.client import ModbusTcpClient
import json
import os
import threading
import time
from datetime import datetime

class TrafficControllerApp:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("B30 Controller")
        self.window.geometry("1500x900")
        self.window.configure(bg="white")
        
        self.client = None
        self.is_connected = False
        self.address_file = "addresses.json"
        self.is_updating = False
        self.current_page = "login"
        self.selected_option = None
        self.auto_update_running = False
        self.connection_lost = False
        self.keep_alive_running = False
        self.timing_page_auto_load_running = False
        self.blink_page_auto_load_running = False
        self.phase_count_update_running = False
        self.part_settings_page_auto_load_running = False
        self.loop_settings_page_auto_load_running = False
        self.loop_status_page_auto_load_running = False
        
        self.focused_timing_entry = None
        self.focused_timing_field = None
        self.focused_timing_prog = None
        self.user_is_editing_timing = False
        self.user_is_editing_blink = False
        self.user_is_editing_part_settings = False
        self.user_is_editing_loops = False
        
        self.plc_lock = threading.Lock()
        self.is_editing_settings = False
        self.is_editing_table = False
        
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
        
        self.PHASE_COUNT_ADDRESS = 4684
        
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
        
        self.LAMP_TEST_MODE_ADDRESS = 4506
        self.LAMP_TEST_BASE_ADDRESS = 2649
        
        self.day_names = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه"]
        
        self.blink_vars = {}
        self.blink_status_labels = {}
        
        self.part_settings_combos = {}
        self.current_part_table = 1
        
        self.loop_combos = {}
        self.current_loop_table = 1
        
        self.card_error_lights = {}
        self.card_reset_buttons = {}
        self.loop_status_widgets = {}
        
        self.lamp_test_lights = {}
        self.lamp_test_lights_colors = {}
        self.lamp_test_running = False
        self.lamp_test_enabled_var = None
        
        self.setup_ui()
        self.load_data()
        
    def setup_ui(self):
        self.login_frame = tk.Frame(self.window, bg="white")
        self.login_frame.pack(fill="both", expand=True)
        
        add_frame = tk.LabelFrame(self.login_frame, text=" افزودن تقاطع جدید", 
                                  bg="#e0e0e0", font=("Arial", 12, "bold"), padx=10, pady=10)
        add_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(add_frame, text="نام:", bg="#e0e0e0", font=("Arial", 10)).pack(side="right", padx=5)
        self.new_name_entry = tk.Entry(add_frame, width=15, font=("Arial", 10))
        self.new_name_entry.pack(side="right", padx=5)
        
        tk.Label(add_frame, text="IP:", bg="#e0e0e0", font=("Arial", 10)).pack(side="right", padx=5)
        self.new_ip_entry = tk.Entry(add_frame, width=15, font=("Arial", 10))
        self.new_ip_entry.pack(side="right", padx=5)
        self.new_ip_entry.insert(0, "192.168.1.")
        
        tk.Label(add_frame, text="Port:", bg="#e0e0e0", font=("Arial", 10)).pack(side="right", padx=5)
        self.new_port_entry = tk.Entry(add_frame, width=8, font=("Arial", 10))
        self.new_port_entry.pack(side="right", padx=5)
        self.new_port_entry.insert(0, "502")
        
        tk.Label(add_frame, text="توضیحات:", bg="#e0e0e0", font=("Arial", 10)).pack(side="right", padx=5)
        self.new_desc_entry = tk.Entry(add_frame, width=30, font=("Arial", 10))
        self.new_desc_entry.pack(side="right", padx=5)
        
        add_btn = tk.Button(add_frame, text="✓ ثبت تقاطع", command=self.add_intersection,
                           bg="green", fg="white", font=("Arial", 10, "bold"), width=15)
        add_btn.pack(side="right", padx=10)
        
        select_frame = tk.Frame(self.login_frame, bg="#e0e0e0", pady=10)
        select_frame.pack(fill="x", padx=10)
        
        tk.Label(select_frame, text="نام تقاطع:", bg="#e0e0e0", font=("Arial", 11, "bold")).pack(side="right", padx=10)
        self.name_var = tk.StringVar()
        self.name_combo = ttk.Combobox(select_frame, textvariable=self.name_var, width=20, state="readonly")
        self.name_combo.pack(side="right", padx=5)
        self.name_combo.bind("<<ComboboxSelected>>", self.on_name_selected)
        
        tk.Label(select_frame, text="IP:", bg="#e0e0e0", font=("Arial", 11, "bold")).pack(side="right", padx=10)
        self.ip_entry = tk.Entry(select_frame, width=15, state="readonly", font=("Arial", 11))
        self.ip_entry.pack(side="right", padx=5)
        
        tk.Label(select_frame, text="Port:", bg="#e0e0e0", font=("Arial", 11, "bold")).pack(side="right", padx=10)
        self.port_entry = tk.Entry(select_frame, width=8, state="readonly", font=("Arial", 11))
        self.port_entry.pack(side="right", padx=5)
        
        self.connect_btn = tk.Button(select_frame, text="اتصال به PLC", command=self.toggle_connection,
                                     bg="green", fg="white", font=("Arial", 11, "bold"), width=15)
        self.connect_btn.pack(side="right", padx=10)
        
        del_btn = tk.Button(select_frame, text="🗑️ حذف", command=self.delete_intersection,
                           bg="red", fg="white", font=("Arial", 11, "bold"), width=10)
        del_btn.pack(side="right", padx=10)
        
        self.status_label = tk.Label(select_frame, text="وضعیت: قطع", bg="#e0e0e0", 
                                     font=("Arial", 11), fg="gray")
        self.status_label.pack(side="right", padx=20)
        
        table_frame = tk.Frame(self.login_frame, bg="white")
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
        
        self.control_frame = tk.Frame(self.window, bg="white")
        
        self.sidebar = tk.Frame(self.control_frame, bg="#0d47a1", width=200)
        self.sidebar.pack(side="right", fill="y")
        self.sidebar.pack_propagate(False)
        
        back_btn = tk.Button(self.sidebar, text="↩ بازگشت", command=self.go_back,
                            bg="#f44336", fg="white", font=("Arial", 12, "bold"), height=2)
        back_btn.pack(fill="x", pady=10, padx=10)
        
        tk.Label(self.sidebar, text="منوی تنظیمات", bg="#0d47a1", fg="white",
                font=("Arial", 14, "bold")).pack(pady=10)
        
        self.option_buttons = []
        options = [
            ("1️⃣ صفحه اصلی", "#2196F3"),
            ("2️⃣ زمان‌بندی", "#4CAF50"),
            ("3️ تنظیمات چشمک زن", "#FF9800"),
            ("4️⃣ تنظیم پارت ها", "#9C27B0"),
            ("5️⃣ تنظیم لوپ ها", "#00BCD4"),
            ("6️⃣ وضعیت لوپ ها", "#E91E63"),
            ("7️⃣ تنظیم IP و زمان", "#795548"),
            ("8️ تست لامپ ها", "#FF5722"),
        ]
        
        for i, (text, color) in enumerate(options):
            btn = tk.Button(self.sidebar, text=text, bg=color, fg="white",
                           font=("Arial", 11, "bold"), height=2,
                           command=lambda idx=i: self.show_page(idx))
            btn.pack(fill="x", pady=3, padx=10)
            self.option_buttons.append(btn)
        
        self.content_frame = tk.Frame(self.control_frame, bg="white")
        self.content_frame.pack(side="right", fill="both", expand=True)
        
        self.pages = {}
        self.build_main_page()
    
    def build_main_page(self):
        page = tk.Frame(self.content_frame, bg="white")
        
        header_frame = tk.Frame(page, bg="white", height=60)
        header_frame.pack(fill="x", padx=10, pady=5)
        header_frame.pack_propagate(False)
        
        self.reset_card_btn = tk.Button(header_frame, text="خطر: ریست کارت چراغ ها",
                                        bg="darkred", fg="white", font=("Arial", 11, "bold"),
                                        command=self.reset_light_card)
        self.reset_card_btn.pack(side="right", padx=10, pady=10)
        
        self.next_phase_btn = tk.Button(header_frame, text="➡ فاز بعد",
                                        bg="#FF9800", fg="white", font=("Arial", 11, "bold"),
                                        command=self.next_phase)
        self.next_phase_btn.pack(side="right", padx=10, pady=10)
        self.next_phase_btn.pack_forget()
        
        tk.Label(header_frame, text="تعداد فاز", bg="white", 
                font=("Arial", 12, "bold")).pack(side="right", padx=10)
        self.phase_count_display = tk.Label(header_frame, text="2", bg="#FF69B4", fg="white",
                                            font=("Arial", 18, "bold"), width=3)
        self.phase_count_display.pack(side="right", padx=5)
        
        phase_table_frame = tk.Frame(page, bg="#1565C0")
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
        
        self.mode_label_table = tk.Label(phase_table_frame, text="نرمال", bg="white", 
                                         fg="black", font=("Arial", 10, "bold"), width=12)
        self.mode_label_table.grid(row=4, column=0, padx=2, pady=1)
        
        for r, (key, name, color, editable) in enumerate(all_rows):
            tk.Label(phase_table_frame, text=name, bg=color, fg="black",
                    font=("Arial", 9, "bold"), width=12).grid(row=r+2, column=0, padx=2, pady=1)
        
        for col in range(8):
            phase_num = col + 1
            grid_col = col + 1
            
            light_canvas = tk.Canvas(phase_table_frame, width=30, height=60, bg="#1565C0", highlightthickness=0)
            light_canvas.grid(row=0, column=grid_col, padx=2, pady=2)
            
            red = light_canvas.create_oval(5, 2, 25, 20, fill="#550000", outline="black")
            yellow = light_canvas.create_oval(5, 21, 25, 39, fill="#555500", outline="black")
            green = light_canvas.create_oval(5, 40, 25, 58, fill="#005500", outline="black")
            
            self.phase_light_canvases[phase_num] = {
                "canvas": light_canvas, "red": red, "yellow": yellow, "green": green
            }
            
            tk.Label(phase_table_frame, text=f"فاز {phase_num}", bg="white",
                    font=("Arial", 12, "bold")).grid(row=1, column=grid_col, padx=2, pady=2)
            
            for r, (key, name, color, editable) in enumerate(all_rows):
                cell_frame = tk.Frame(phase_table_frame, bg="#1565C0")
                cell_frame.grid(row=r+2, column=grid_col, padx=1, pady=1)
                
                address = self.PHASE_ADDRESSES[key][col]
                
                if editable:
                    e_editable = tk.Entry(cell_frame, width=4, font=("Arial", 9),
                                          justify="center", bg="white", fg="black")
                    e_editable.pack(side="right", padx=1)
                    
                    e_readonly = tk.Entry(cell_frame, width=4, font=("Arial", 9, "bold"),
                                          justify="center", bg=color, fg="black",
                                          state="readonly", readonlybackground=color)
                    e_readonly.pack(side="right", padx=1)
                    e_readonly.insert(0, "0")
                    
                    e_editable.bind("<Return>", lambda event, addr=address, entry=e_editable, row=key: 
                                    self._on_entry_submit(addr, entry, row))
                    e_editable.bind("<FocusOut>", lambda event, addr=address, entry=e_editable, row=key: 
                                    self._on_entry_submit(addr, entry, row))
                    
                    self.phase_entries[(key, phase_num)] = {
                        "readonly": e_readonly,
                        "editable": e_editable,
                        "address": address
                    }
                else:
                    e_readonly = tk.Entry(cell_frame, width=4, font=("Arial", 9, "bold"),
                                          justify="center", bg=color, fg="black",
                                          state="readonly", readonlybackground=color)
                    e_readonly.pack(side="right", padx=1)
                    e_readonly.insert(0, "0")
                    
                    self.phase_entries[(key, phase_num)] = {
                        "readonly": e_readonly,
                        "editable": None,
                        "address": address
                    }
        
        main_content = tk.Frame(page, bg="white")
        main_content.pack(fill="both", expand=True, padx=10, pady=5)
        
        map_frame = tk.Frame(main_content, bg="white")
        map_frame.pack(side="right", fill="both", expand=True)
        
        self.traffic_canvas = tk.Canvas(map_frame, width=700, height=500, bg="#90EE90", 
                                        highlightthickness=2, highlightbackground="#333")
        self.traffic_canvas.pack(pady=5)
        
        left_panel = tk.Frame(main_content, bg="white", width=220)
        left_panel.pack(side="right", fill="y", padx=5)
        left_panel.pack_propagate(False)
        
        self.day_label = tk.Label(left_panel, text="چهارشنبه", bg="#FF69B4", fg="white",
                                  font=("Arial", 13, "bold"))
        self.day_label.pack(fill="x", pady=5)
        
        tk.Label(left_panel, text="ساعت", bg="white", font=("Arial", 12, "bold")).pack()
        self.time_big_label = tk.Label(left_panel, text="--:--:--", bg="#FF8C00", fg="white",
                                       font=("Arial", 24, "bold"))
        self.time_big_label.pack(pady=5)
        
        tk.Label(left_panel, text="تاریخ شمسی", bg="white", font=("Arial", 11, "bold")).pack()
        self.shamsi_big_label = tk.Label(left_panel, text="----/--/--", bg="white", fg="#006400",
                                         font=("Arial", 16, "bold"))
        self.shamsi_big_label.pack(pady=2)
        
        tk.Label(left_panel, text="تاریخ میلادی", bg="white", font=("Arial", 11, "bold")).pack()
        self.miladi_big_label = tk.Label(left_panel, text="----/--/--", bg="white", fg="#00008B",
                                         font=("Arial", 14, "bold"))
        self.miladi_big_label.pack(pady=2)
        
        tk.Label(left_panel, text="3", bg="#0000CD", fg="white", 
                font=("Arial", 11, "bold"), width=12).pack(fill="x", pady=2)
        tk.Label(left_panel, text="4", bg="#0000CD", fg="white", 
                font=("Arial", 11, "bold"), width=12).pack(fill="x", pady=2)
        
        settings_frame = tk.Frame(left_panel, bg="white", relief="groove", bd=2)
        settings_frame.pack(fill="x", pady=10, padx=5)
        
        row1 = tk.Frame(settings_frame, bg="white")
        row1.pack(fill="x", pady=5, padx=5)
        
        tk.Label(row1, text="سنسورها:", bg="white", font=("Arial", 9, "bold"), width=10, anchor="w").pack(side="right", padx=2)
        self.sensors_var = tk.StringVar(value="غیر فعال")
        self.sensors_combo = ttk.Combobox(row1, textvariable=self.sensors_var,
                                          values=["غیر فعال", "فعال"],
                                          state="readonly", width=12)
        self.sensors_combo.pack(side="right", padx=2)
        self.sensors_combo.bind("<<ComboboxSelected>>", lambda e: self._on_settings_change("sensors"))
        
        row2 = tk.Frame(settings_frame, bg="white")
        row2.pack(fill="x", pady=5, padx=5)
        
        tk.Label(row2, text="زمان سبزها:", bg="white", font=("Arial", 9, "bold"), width=10, anchor="w").pack(side="right", padx=2)
        self.green_time_var = tk.StringVar(value="اتوماتیک")
        self.green_time_combo = ttk.Combobox(row2, textvariable=self.green_time_var,
                                             values=["اتوماتیک", "دستی"],
                                             state="readonly", width=12)
        self.green_time_combo.pack(side="right", padx=2)
        self.green_time_combo.bind("<<ComboboxSelected>>", lambda e: self._on_settings_change("green_time"))
        
        row3 = tk.Frame(settings_frame, bg="white")
        row3.pack(fill="x", pady=5, padx=5)
        
        tk.Label(row3, text="کنترل:", bg="white", font=("Arial", 9, "bold"), width=10, anchor="w").pack(side="right", padx=2)
        self.control_var = tk.StringVar(value="اتوماتیک")
        self.control_combo = ttk.Combobox(row3, textvariable=self.control_var,
                                          values=["اتوماتیک", "پلیس", "دائمی فلش"],
                                          state="readonly", width=12)
        self.control_combo.pack(side="right", padx=2)
        self.control_combo.bind("<<ComboboxSelected>>", lambda e: self._on_settings_change("control_mode"))
        
        self.settings_status = tk.Label(settings_frame, text="", bg="white",
                                        font=("Arial", 9), fg="gray")
        self.settings_status.pack(pady=5)
        
        bottom_route = tk.Frame(page, bg="white")
        bottom_route.pack(fill="x", padx=10)
        
        tk.Label(bottom_route, text="6", bg="white", font=("Arial", 14, "bold"), width=3).pack(side="right", padx=5)
        tk.Label(bottom_route, text="6", bg="#0000CD", fg="white", font=("Arial", 12, "bold"), width=15).pack(side="right", padx=2)
        tk.Label(bottom_route, text="5", bg="#0000CD", fg="white", font=("Arial", 12, "bold"), width=15).pack(side="right", padx=2)
        tk.Label(bottom_route, text="5", bg="white", font=("Arial", 14, "bold"), width=3).pack(side="right", padx=5)
        
        self.pages[0] = page
        self.draw_intersection_map()
    
    def draw_intersection_map(self):
        canvas = self.traffic_canvas
        canvas.delete("all")
        
        W, H = 700, 500
        
        canvas.create_rectangle(0, 0, W, H, fill="#90EE90")
        canvas.create_rectangle(280, 0, 420, H, fill="#404040")
        canvas.create_rectangle(0, 180, W, 320, fill="#404040")
        
        for y in range(0, 180, 25):
            canvas.create_line(350, y, 350, y+12, fill="white", width=3)
        for y in range(320, H, 25):
            canvas.create_line(350, y, 350, y+12, fill="white", width=3)
        for x in range(0, 280, 25):
            canvas.create_line(x, 250, x+12, 250, fill="white", width=3)
        for x in range(420, W, 25):
            canvas.create_line(x, 250, x+12, 250, fill="white", width=3)
        
        for i in range(0, 140, 15):
            canvas.create_line(280+i, 180, 280+i+7, 180, fill="white", width=8)
            canvas.create_line(280+i, 320, 280+i+7, 320, fill="white", width=8)
        for i in range(0, 140, 15):
            canvas.create_line(280, 180+i, 280, 180+i+7, fill="white", width=8)
            canvas.create_line(420, 180+i, 420, 180+i+7, fill="white", width=8)
        
        lights_positions = [
            (305, 60, 2),
            (365, 60, 1),
            (580, 200, 8),
            (580, 260, 7),
            (305, 420, 5),
            (365, 420, 6),
            (100, 200, 3),
            (100, 260, 4),
        ]
        
        self.map_lights = {}
        for x, y, phase_num in lights_positions:
            canvas.create_rectangle(x-25, y-35, x+25, y+35, fill="#1a1a1a", outline="#555", width=2)
            red = canvas.create_oval(x-18, y-30, x+18, y+5, fill="#330000", outline="black", width=2)
            yellow = canvas.create_oval(x-18, y-5, x+18, y+15, fill="#333300", outline="black", width=2)
            green = canvas.create_oval(x-18, y+15, x+18, y+30, fill="#003300", outline="black", width=2)
            
            self.map_lights[phase_num] = {
                "red": red, "yellow": yellow, "green": green,
                "x": x, "y": y
            }
        
        canvas.create_line(315, 100, 315, 160, fill="white", width=4, arrow=tk.LAST)
        canvas.create_line(385, 100, 385, 160, fill="white", width=4, arrow=tk.LAST)
        canvas.create_line(315, 400, 315, 340, fill="white", width=4, arrow=tk.LAST)
        canvas.create_line(385, 400, 385, 340, fill="white", width=4, arrow=tk.LAST)
        canvas.create_line(560, 215, 440, 215, fill="white", width=4, arrow=tk.LAST)
        canvas.create_line(560, 285, 440, 285, fill="white", width=4, arrow=tk.LAST)
        canvas.create_line(140, 215, 260, 215, fill="white", width=4, arrow=tk.LAST)
        canvas.create_line(140, 285, 260, 285, fill="white", width=4, arrow=tk.LAST)
    
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
                print(f"خطا در فاز بعد: {e}")
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
                    print(f"خطا در keep-alive: {e}")
                    self._handle_connection_error()
                    break
                time.sleep(10)
        
        self.keep_alive_running = True
        threading.Thread(target=_keep_alive_loop, daemon=True).start()
    
    def stop_keep_alive(self):
        self.keep_alive_running = False
    
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
                    result = self._read_register(self.PHASE_COUNT_ADDRESS, 1)
                    if not result.isError():
                        new_count = result.registers[0]
                        if new_count != self.phase_count:
                            self.phase_count = new_count
                            self.window.after(0, lambda: self.phase_count_display.configure(text=str(new_count)))
                except:
                    pass
            
            threading.Thread(target=_update, daemon=True).start()
        
        self.window.after(1000, self._phase_count_update_loop)
    
    def build_timing_page(self):
        page = tk.Frame(self.content_frame, bg="#1565C0")
        
        canvas = tk.Canvas(page, bg="#1565C0", highlightthickness=0)
        v_scrollbar = ttk.Scrollbar(page, orient="vertical", command=canvas.yview)
        
        scrollable_frame = tk.Frame(canvas, bg="#1565C0", width=1800)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=v_scrollbar.set)
        
        h_scrollbar = ttk.Scrollbar(page, orient="horizontal", command=canvas.xview)
        canvas.configure(xscrollcommand=h_scrollbar.set)
        
        canvas.pack(side="top", fill="both", expand=True)
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")
        
        datetime_frame = tk.Frame(scrollable_frame, bg="#1565C0")
        datetime_frame.pack(fill="x", padx=10, pady=10)
        
        hour_frame = tk.Frame(datetime_frame, bg="#1565C0")
        hour_frame.pack(side="right", padx=20)
        
        tk.Label(hour_frame, text="ساعت", bg="#1565C0", fg="white",
                font=("Arial", 14, "bold")).pack()
        
        self.timing_min_label = tk.Label(hour_frame, text="--", bg="#FF8C00", fg="white",
                                          font=("Arial", 24, "bold"), width=3)
        self.timing_min_label.pack(side="right", padx=2)
        
        tk.Label(hour_frame, text=":", bg="#1565C0", fg="white", font=("Arial", 24, "bold")).pack(side="right")
        
        self.timing_hour_label = tk.Label(hour_frame, text="--", bg="#FF8C00", fg="white",
                                           font=("Arial", 24, "bold"), width=3)
        self.timing_hour_label.pack(side="right", padx=2)
        
        date_frame = tk.Frame(datetime_frame, bg="#1565C0")
        date_frame.pack(side="right", padx=20)
        
        tk.Label(date_frame, text="امروز", bg="#1565C0", fg="white",
                font=("Arial", 14, "bold")).pack()
        
        self.timing_day_name_label = tk.Label(date_frame, text="------", bg="#FF69B4", fg="white",
                                               font=("Arial", 14, "bold"), width=10)
        self.timing_day_name_label.pack(pady=2)
        
        self.timing_shamsi_date_label = tk.Label(date_frame, text="----/--/--", bg="#FF8C00", fg="white",
                                                  font=("Arial", 16, "bold"))
        self.timing_shamsi_date_label.pack(pady=2)
        
        control_frame = tk.Frame(scrollable_frame, bg="#1565C0")
        control_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(control_frame, text="تعداد برنامه‌های فعال:", bg="#1565C0", fg="white",
                font=("Arial", 12, "bold")).pack(side="right", padx=10)
        
        self.visible_programs_var = tk.IntVar(value=9)
        
        btn_minus = tk.Button(control_frame, text="➖", bg="#f44336", fg="white",
                              font=("Arial", 14, "bold"), width=2,
                              command=self.decrease_visible_programs)
        btn_minus.pack(side="right", padx=5)
        
        tk.Label(control_frame, textvariable=self.visible_programs_var, bg="white", fg="black",
                font=("Arial", 16, "bold"), width=3).pack(side="right", padx=5)
        
        btn_plus = tk.Button(control_frame, text="➕", bg="#4CAF50", fg="white",
                             font=("Arial", 14, "bold"), width=2,
                             command=self.increase_visible_programs)
        btn_plus.pack(side="right", padx=5)
        
        self.timing_programs = {}
        self.program_frames = {}
        
        for prog_idx in range(27):
            base_addr = self.timing_base_addresses[prog_idx]
            
            prog_frame = tk.Frame(scrollable_frame, bg="#1565C0", 
                                  highlightbackground="#FF8C00", highlightthickness=1)
            prog_frame.pack(fill="x", padx=10, pady=3)
            
            header_frame = tk.Frame(prog_frame, bg="#FF8C00")
            header_frame.pack(fill="x")
            
            tk.Label(header_frame, text=f"برنامه {prog_idx + 1}", bg="#FF8C00", fg="white",
                    font=("Arial", 12, "bold")).pack(side="right", padx=10, pady=3)
            
            content_frame = tk.Frame(prog_frame, bg="#1565C0")
            content_frame.pack(fill="x", padx=5, pady=3)
            
            headers = ["وضعیت", "روزها", "حالت", "از", "تا",
                       "سبز1", "سبز2", "سبز3", "سبز4", "سبز5", "سبز6", "سبز7", "سبز8",
                       "فاز1", "فاز2", "فاز3", "فاز4", "فاز5", "فاز6", "فاز7", "فاز8",
                       "جدول پارت"]
            
            for col_idx, header in enumerate(headers):
                tk.Label(content_frame, text=header, bg="#1565C0", fg="white",
                        font=("Arial", 8, "bold"), width=5).grid(row=0, column=col_idx, padx=1, pady=1)
            
            self.timing_programs[prog_idx] = {
                "entries": {},
                "vars": {},
                "frame": prog_frame,
                "base_addr": base_addr
            }
            
            self._create_timing_program_row(content_frame, prog_idx, base_addr)
            self.program_frames[prog_idx] = prog_frame
            
            if prog_idx > 8:
                prog_frame.pack_forget()
        
        self.pages[1] = page
    
    def _create_timing_program_row(self, parent, prog_idx, base_addr):
        prog_data = self.timing_programs[prog_idx]
        
        status_var = tk.StringVar(value="فعال" if prog_idx < 9 else "غیر فعال")
        status_combo = ttk.Combobox(parent, textvariable=status_var,
                                     values=["فعال", "غیر فعال"],
                                     state="readonly", width=5)
        status_combo.grid(row=1, column=0, padx=1, pady=1)
        status_combo.bind("<<ComboboxSelected>>", 
                         lambda e, p=prog_idx: self._on_timing_change(p, "status"))
        prog_data["vars"]["status"] = (status_var, base_addr + 0)
        
        days_frame = tk.Frame(parent, bg="#1565C0")
        days_frame.grid(row=1, column=1, padx=1, pady=1)
        
        day_labels_frame = tk.Frame(days_frame, bg="#1565C0")
        day_labels_frame.pack(fill="x")
        
        day_checks_frame = tk.Frame(days_frame, bg="#1565C0")
        day_checks_frame.pack(fill="x")
        
        for day_col in range(7):
            day_name = self.day_names[day_col]
            tk.Label(day_labels_frame, text=day_name, bg="#1565C0", fg="white",
                    font=("Arial", 8, "bold"), width=7).pack(side="right", padx=1)
            
            day_var = tk.BooleanVar(value=(prog_idx == 0 and day_col == 0))
            check = tk.Checkbutton(day_checks_frame, variable=day_var, bg="#1565C0",
                                    selectcolor="white", activebackground="#1565C0",
                                    width=5, indicatoron=False,
                                    command=lambda p=prog_idx, d=day_col: self._on_timing_change(p, f"day_{d}"))
            check.pack(side="right", padx=1)
            prog_data["vars"][f"day_{day_col}"] = (day_var, base_addr + 1 + day_col)
        
        mode_var = tk.StringVar(value="زمان ثابت")
        mode_combo = ttk.Combobox(parent, textvariable=mode_var,
                                   values=["زمان ثابت", "هوشمند"],
                                   state="readonly", width=7)
        mode_combo.grid(row=1, column=2, padx=1, pady=1)
        mode_combo.bind("<<ComboboxSelected>>", 
                       lambda e, p=prog_idx: self._on_timing_change(p, "mode"))
        prog_data["vars"]["mode"] = (mode_var, base_addr + 31)
        
        from_frame = tk.Frame(parent, bg="#1565C0")
        from_frame.grid(row=1, column=3, padx=1, pady=1)
        
        for i, label in reversed(list(enumerate(["H", "M", "S"]))):
            e = tk.Entry(from_frame, width=2, font=("Arial", 8),
                         justify="center", bg="white", fg="black")
            e.pack(side="right", padx=1)
            e.insert(0, "0")
            e.bind("<FocusIn>", lambda event, p=prog_idx, f=f"from_{label}": self._on_timing_focus_in(p, f))
            e.bind("<FocusOut>", lambda event, p=prog_idx, f=f"from_{label}": self._on_timing_focus_out(p, f))
            e.bind("<Return>", lambda event, p=prog_idx, f=f"from_{label}": self._on_timing_enter(p, f))
            prog_data["entries"][f"from_{label}"] = (e, base_addr + 8 + i)
        
        to_frame = tk.Frame(parent, bg="#1565C0")
        to_frame.grid(row=1, column=4, padx=1, pady=1)
        
        for i, label in reversed(list(enumerate(["H", "M", "S"]))):
            e = tk.Entry(to_frame, width=2, font=("Arial", 8),
                         justify="center", bg="white", fg="black")
            e.pack(side="right", padx=1)
            e.insert(0, "0")
            e.bind("<FocusIn>", lambda event, p=prog_idx, f=f"to_{label}": self._on_timing_focus_in(p, f))
            e.bind("<FocusOut>", lambda event, p=prog_idx, f=f"to_{label}": self._on_timing_focus_out(p, f))
            e.bind("<Return>", lambda event, p=prog_idx, f=f"to_{label}": self._on_timing_enter(p, f))
            prog_data["entries"][f"to_{label}"] = (e, base_addr + 11 + i)
        
        for phase in range(8):
            e = tk.Entry(parent, width=4, font=("Arial", 8),
                         justify="center", bg="#00FF00", fg="black")
            e.grid(row=1, column=5+phase, padx=1, pady=1)
            e.insert(0, "0")
            e.bind("<FocusIn>", lambda event, p=prog_idx, f=f"green_{phase+1}": self._on_timing_focus_in(p, f))
            e.bind("<FocusOut>", lambda event, p=prog_idx, f=f"green_{phase+1}": self._on_timing_focus_out(p, f))
            e.bind("<Return>", lambda event, p=prog_idx, f=f"green_{phase+1}": self._on_timing_enter(p, f))
            prog_data["entries"][f"green_{phase+1}"] = (e, base_addr + 14 + phase)
        
        for phase in range(8):
            phase_var = tk.StringVar(value="------")
            phase_combo = ttk.Combobox(parent, textvariable=phase_var,
                                        values=["------", "زمان ثابت", "ماکزیمم"],
                                        state="readonly", width=7)
            phase_combo.grid(row=1, column=13+phase, padx=1, pady=1)
            phase_combo.bind("<<ComboboxSelected>>", 
                            lambda e, p=prog_idx, ph=phase: self._on_timing_change(p, f"phase_{ph+1}"))
            prog_data["vars"][f"phase_{phase+1}"] = (phase_var, base_addr + 22 + phase)
        
        part_var = tk.StringVar(value="جدول 1")
        part_combo = ttk.Combobox(parent, textvariable=part_var,
                                   values=["جدول 1", "جدول 2"],
                                   state="readonly", width=5)
        part_combo.grid(row=1, column=21, padx=1, pady=1)
        part_combo.bind("<<ComboboxSelected>>", 
                       lambda e, p=prog_idx: self._on_timing_change(p, "part"))
        prog_data["vars"]["part"] = (part_var, base_addr + 30)
    
    def _on_timing_focus_in(self, prog_idx, field_name):
        self.focused_timing_entry = prog_idx
        self.focused_timing_field = field_name
        self.focused_timing_prog = prog_idx
        self.user_is_editing_timing = True
    
    def _on_timing_focus_out(self, prog_idx, field_name):
        self._save_timing_entry(prog_idx, field_name)
    
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
            
            def _write():
                try:
                    with self.plc_lock:
                        self.client.write_register(address=addr, value=value, device_id=1)
                    self.window.after(0, lambda: setattr(self, 'user_is_editing_timing', False))
                except Exception as e:
                    print(f"خطا در ذخیره Entry {field_name}: {e}")
                    self._handle_connection_error()
                    self.window.after(0, lambda: setattr(self, 'user_is_editing_timing', False))
            
            threading.Thread(target=_write, daemon=True).start()
            self.window.after(5000, lambda: setattr(self, 'user_is_editing_timing', False))
        except Exception as e:
            print(f"خطا در _save_timing_entry: {e}")
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
        
        self.user_is_editing_timing = True
        
        def _save():
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
                    self.window.after(0, lambda: setattr(self, 'user_is_editing_timing', False))
                    return
                
                with self.plc_lock:
                    self.client.write_register(address=addr, value=value, device_id=1)
                
                self.window.after(0, lambda: setattr(self, 'user_is_editing_timing', False))
            except Exception as e:
                print(f"خطا در ذخیره {field_name}: {e}")
                self._handle_connection_error()
                self.window.after(0, lambda: setattr(self, 'user_is_editing_timing', False))
        
        threading.Thread(target=_save, daemon=True).start()
        self.window.after(5000, lambda: setattr(self, 'user_is_editing_timing', False))
    
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
                print(f"خطا در بارگذاری برنامه {prog_idx}: {e}")
        
        threading.Thread(target=_load, daemon=True).start()
    
    def _load_all_timing_programs(self):
        visible_count = self.visible_programs_var.get()
        for prog_idx in range(visible_count):
            self._load_timing_program(prog_idx)
            time.sleep(0.05)
    
    def _auto_load_timing_loop(self):
        if not self.timing_page_auto_load_running:
            return
        
        if self.is_connected and self.client and not self.user_is_editing_timing:
            self._load_all_timing_programs()
            self._load_timing_datetime()
        
        self.window.after(2000, self._auto_load_timing_loop)
    
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
                    
                    day_name = self._get_jalali_day_name(y, mo, d)
                    self.window.after(0, lambda: self.timing_day_name_label.configure(text=day_name))
            except Exception as e:
                print(f"خطا در بارگذاری ساعت/تاریخ: {e}")
        
        threading.Thread(target=_load, daemon=True).start()
    
    def _get_jalali_day_name(self, jy, jm, jd):
        try:
            gy, gm, gd = self._jalali_to_gregorian_date(jy, jm, jd)
            from datetime import datetime
            date = datetime(gy, gm, gd)
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
            self._set_program_status(new_count - 1, "فعال")
            self._on_timing_change(new_count - 1, "status")
    
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
    
    def build_blink_page(self):
        page = tk.Frame(self.content_frame, bg="#1565C0")
        
        title_frame = tk.Frame(page, bg="#1565C0")
        title_frame.pack(fill="x", padx=10, pady=15)
        
        tk.Label(title_frame, text="تنظیمات چشمک زن", bg="#1565C0", fg="white",
                font=("Arial", 20, "bold")).pack()
        
        parts_frame = tk.Frame(page, bg="#1565C0")
        parts_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(parts_frame, text="پارت‌ها:", bg="#1565C0", fg="white",
                font=("Arial", 14, "bold")).pack(anchor="w", pady=5)
        
        parts_row = tk.Frame(parts_frame, bg="#1565C0")
        parts_row.pack(fill="x")
        
        for key in list(self.blink_vars.keys()):
            if isinstance(key, int):
                del self.blink_vars[key]
        
        for part_num in range(1, 9):
            part_frame = tk.Frame(parts_row, bg="#FF9800", relief="raised", bd=2)
            part_frame.pack(side="right", padx=8, pady=5)
            
            tk.Label(part_frame, text=f"PART {part_num}", bg="#FF9800", fg="white",
                    font=("Arial", 11, "bold"), width=10).pack(pady=3)
            
            var = tk.StringVar(value="غیر فعال")
            combo = ttk.Combobox(part_frame, textvariable=var,
                                 values=["غیر فعال", "چشمک زن قرمز", "چشمک زن زرد"],
                                 state="readonly", width=13)
            combo.pack(pady=3)
            combo.bind("<<ComboboxSelected>>", 
                      lambda e, p=part_num, v=var: self._on_blink_change(p, v))
            
            address = self.PART_BLINK_ADDRESSES[part_num]
            self.blink_vars[part_num] = (var, address)
        
        pedestrian_frame = tk.Frame(page, bg="#1565C0")
        pedestrian_frame.pack(fill="x", padx=10, pady=20)
        
        tk.Label(pedestrian_frame, text="چشمک زن عابر:", bg="#1565C0", fg="white",
                font=("Arial", 14, "bold")).pack(anchor="w", pady=5)
        
        pedestrian_inner = tk.Frame(pedestrian_frame, bg="#00FF00", relief="raised", bd=2)
        pedestrian_inner.pack(side="right", padx=10, pady=5)
        
        tk.Label(pedestrian_inner, text="عابر پیاده", bg="#00FF00", fg="black",
                font=("Arial", 12, "bold"), width=15).pack(pady=3)
        
        pedestrian_var = tk.StringVar(value="چشمک زن سبز")
        pedestrian_combo = ttk.Combobox(pedestrian_inner, textvariable=pedestrian_var,
                                         values=["چشمک زن سبز", "چشمک زن قرمز"],
                                         state="readonly", width=13)
        pedestrian_combo.pack(pady=5)
        pedestrian_combo.bind("<<ComboboxSelected>>", 
                             lambda e, v=pedestrian_var: self._on_blink_change("pedestrian", v))
        
        self.blink_vars["pedestrian"] = (pedestrian_var, self.PEDESTRIAN_BLINK_ADDRESS)
        
        self.pages[2] = page
    
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
                print(f"خطا در ذخیره چشمک زن {key}: {e}")
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
                
                if "pedestrian" in self.blink_vars:
                    var, addr = self.blink_vars["pedestrian"]
                    result = self._read_register(addr, 1)
                    if not result.isError():
                        value = result.registers[0]
                        pedestrian_val_map = {0: "چشمک زن سبز", 1: "چشمک زن قرمز"}
                        text = pedestrian_val_map.get(value, "چشمک زن سبز")
                        self.window.after(0, lambda v=var, t=text: v.set(t))
            except Exception as e:
                print(f"خطا در بارگذاری چشمک زن: {e}")
        
        threading.Thread(target=_load, daemon=True).start()
    
    def _auto_load_blink_loop(self):
        if not self.blink_page_auto_load_running:
            return
        
        if self.is_connected and self.client and not self.user_is_editing_blink:
            self._load_blink_page()
        
        self.window.after(2000, self._auto_load_blink_loop)
    
    def build_part_settings_page(self):
        page = tk.Frame(self.content_frame, bg="#1565C0")
        
        header_frame = tk.Frame(page, bg="#1565C0")
        header_frame.pack(fill="x", padx=10, pady=10)
        
        phase_count_frame = tk.Frame(header_frame, bg="#1565C0")
        phase_count_frame.pack(side="right", padx=20)
        
        tk.Label(phase_count_frame, text="تعداد فازها", bg="#FF69B4", fg="white",
                font=("Arial", 14, "bold")).pack(side="right", padx=5)
        
        self.part_phase_count_var = tk.StringVar(value="2")
        phase_count_combo = ttk.Combobox(phase_count_frame, textvariable=self.part_phase_count_var,
                                          values=[str(i) for i in range(2, 9)],
                                          state="readonly", width=3, font=("Arial", 16, "bold"))
        phase_count_combo.pack(side="right", padx=5)
        phase_count_combo.bind("<<ComboboxSelected>>", lambda e: self._on_part_phase_count_change())
        
        tab_frame = tk.Frame(header_frame, bg="#1565C0")
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
        
        table_container = tk.Frame(page, bg="#1565C0")
        table_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        canvas = tk.Canvas(table_container, bg="#1565C0", highlightthickness=0)
        v_scrollbar = ttk.Scrollbar(table_container, orient="vertical", command=canvas.yview)
        h_scrollbar = ttk.Scrollbar(table_container, orient="horizontal", command=canvas.xview)
        
        self.part_table_frame = tk.Frame(canvas, bg="#1565C0")
        
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
        
        tk.Label(self.part_table_frame, text="", bg="#1565C0", width=10).grid(row=0, column=0, padx=2, pady=2)
        
        for phase in range(1, 9):
            tk.Label(self.part_table_frame, text=f"فاز {phase}", bg="#FF9800", fg="white",
                    font=("Arial", 12, "bold"), width=12).grid(row=0, column=phase, padx=2, pady=2)
        
        for part in range(1, 9):
            tk.Label(self.part_table_frame, text=f"PART {part}", bg="#FF9800", fg="white",
                    font=("Arial", 11, "bold"), width=10).grid(row=part, column=0, padx=2, pady=2)
            
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
                                      state="readonly", width=10)
                combo.grid(row=part, column=phase, padx=2, pady=2)
                
                combo.bind("<<ComboboxSelected>>", 
                          lambda e, p=part, ph=phase, v=var: self._on_part_setting_change(p, ph, v))
                
                self.part_settings_combos[part][phase] = (combo, var, address)
        
        self._on_part_phase_count_change()
    
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
                def _write():
                    try:
                        with self.plc_lock:
                            self.client.write_register(address=self.PHASE_COUNT_ADDRESS, 
                                                       value=phase_count, device_id=1)
                    except Exception as e:
                        print(f"خطا در نوشتن تعداد فازها: {e}")
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
        
        self.user_is_editing_part_settings = True
        
        def _save():
            try:
                value = self.part_values.get(var.get(), 0)
                
                if part in self.part_settings_combos and phase in self.part_settings_combos[part]:
                    _, _, address = self.part_settings_combos[part][phase]
                    
                    with self.plc_lock:
                        self.client.write_register(address=address, value=value, device_id=1)
                
                self.window.after(0, lambda: setattr(self, 'user_is_editing_part_settings', False))
            except Exception as e:
                print(f"خطا در ذخیره تنظیم پارت {part}/{phase}: {e}")
                self._handle_connection_error()
                self.window.after(0, lambda: setattr(self, 'user_is_editing_part_settings', False))
        
        threading.Thread(target=_save, daemon=True).start()
        self.window.after(5000, lambda: setattr(self, 'user_is_editing_part_settings', False))
    
    def _load_part_settings_table(self):
        if not self.is_connected or not self.client:
            return
        
        def _load():
            try:
                with self.plc_lock:
                    phase_result = self.client.read_holding_registers(
                        address=self.PHASE_COUNT_ADDRESS, count=1, device_id=1)
                
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
            except Exception as e:
                print(f"خطا در بارگذاری تنظیم پارت‌ها: {e}")
        
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
        
        if self.is_connected and self.client and not self.user_is_editing_part_settings:
            self._load_part_settings_table()
        
        self.window.after(2000, self._auto_load_part_settings_loop)
    
    def build_loop_settings_page(self):
        page = tk.Frame(self.content_frame, bg="#1565C0")
        
        header_frame = tk.Frame(page, bg="#1565C0")
        header_frame.pack(fill="x", padx=10, pady=10)
        
        tab_frame = tk.Frame(header_frame, bg="#1565C0")
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
        
        table_container = tk.Frame(page, bg="#1565C0")
        table_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        canvas = tk.Canvas(table_container, bg="#1565C0", highlightthickness=0)
        v_scrollbar = ttk.Scrollbar(table_container, orient="vertical", command=canvas.yview)
        h_scrollbar = ttk.Scrollbar(table_container, orient="horizontal", command=canvas.xview)
        
        self.loop_table_frame = tk.Frame(canvas, bg="#1565C0")
        
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
        
        self.pages[4] = page
    
    def _build_loop_table(self):
        for widget in self.loop_table_frame.winfo_children():
            widget.destroy()
        self.loop_combos = {}
        
        self.loop_options = ["غیر فعال", "فعال"]
        self.loop_values = {"غیر فعال": 0, "فعال": 1}
        
        if self.current_loop_table == 1:
            base_addr = self.LOOP_TABLE1_BASE
        else:
            base_addr = self.LOOP_TABLE2_BASE
        
        tk.Label(self.loop_table_frame, text="", bg="#1565C0", width=8).grid(row=0, column=0, padx=2, pady=2)
        
        for loop in range(1, 17):
            tk.Label(self.loop_table_frame, text=f"لوپ {loop}", bg="#FF9800", fg="white",
                    font=("Arial", 9, "bold"), width=7).grid(row=0, column=loop, padx=2, pady=2)
        
        for phase in range(1, 9):
            tk.Label(self.loop_table_frame, text=f"فاز {phase}", bg="#FF9800", fg="white",
                    font=("Arial", 11, "bold"), width=8).grid(row=phase, column=0, padx=2, pady=2)
            
            self.loop_combos[phase] = {}
            
            for loop in range(1, 17):
                address = base_addr + (phase - 1) * 16 + (loop - 1)
                
                var = tk.StringVar(value="غیر فعال")
                combo = ttk.Combobox(self.loop_table_frame, textvariable=var,
                                      values=self.loop_options,
                                      state="readonly", width=7)
                combo.grid(row=phase, column=loop, padx=2, pady=2)
                
                combo.bind("<<ComboboxSelected>>", 
                          lambda e, p=phase, l=loop, v=var: self._on_loop_setting_change(p, l, v))
                
                self.loop_combos[phase][loop] = (combo, var, address)
    
    def _switch_loop_table(self, table_num):
        if table_num == self.current_loop_table:
            return
        
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
        
        if self.is_connected and self.client:
            self._load_loop_table()
    
    def _on_loop_setting_change(self, phase, loop, var):
        if not self.is_connected or not self.client:
            self.user_is_editing_loops = False
            return
        
        self.user_is_editing_loops = True
        
        def _save():
            try:
                value = self.loop_values.get(var.get(), 0)
                
                if phase in self.loop_combos and loop in self.loop_combos[phase]:
                    _, _, address = self.loop_combos[phase][loop]
                    
                    with self.plc_lock:
                        self.client.write_register(address=address, value=value, device_id=1)
                
                self.window.after(0, lambda: setattr(self, 'user_is_editing_loops', False))
            except Exception as e:
                print(f"خطا در ذخیره لوپ فاز {phase} لوپ {loop}: {e}")
                self._handle_connection_error()
                self.window.after(0, lambda: setattr(self, 'user_is_editing_loops', False))
        
        threading.Thread(target=_save, daemon=True).start()
        self.window.after(5000, lambda: setattr(self, 'user_is_editing_loops', False))
    
    def _load_loop_table(self):
        if not self.is_connected or not self.client:
            return
        
        def _load():
            try:
                if self.current_loop_table == 1:
                    base_addr = self.LOOP_TABLE1_BASE
                else:
                    base_addr = self.LOOP_TABLE2_BASE
                
                val_to_text = {0: "غیر فعال", 1: "فعال"}
                
                for phase in range(1, 9):
                    phase_base = base_addr + (phase - 1) * 16
                    
                    with self.plc_lock:
                        result = self.client.read_holding_registers(
                            address=phase_base, count=16, device_id=1)
                    
                    if result.isError():
                        continue
                    
                    regs = result.registers
                    
                    for loop in range(1, 17):
                        idx = loop - 1
                        
                        if idx < len(regs) and phase in self.loop_combos and loop in self.loop_combos[phase]:
                            combo, var, addr = self.loop_combos[phase][loop]
                            value = regs[idx]
                            text = val_to_text.get(value, "غیر فعال")
                            
                            self.window.after(0, lambda v=var, t=text: v.set(t))
            except Exception as e:
                print(f"خطا در بارگذاری لوپ‌ها: {e}")
        
        threading.Thread(target=_load, daemon=True).start()
    
    def _auto_load_loop_loop(self):
        if not self.loop_settings_page_auto_load_running:
            return
        
        if self.is_connected and self.client and not self.user_is_editing_loops:
            self._load_loop_table()
        
        self.window.after(2000, self._auto_load_loop_loop)
    
    def build_loop_status_page(self):
        page = tk.Frame(self.content_frame, bg="#1565C0")
        
        top_section = tk.Frame(page, bg="#1565C0")
        top_section.pack(fill="x", padx=10, pady=10)
        
        reset_alarm_frame = tk.Frame(top_section, bg="#1565C0")
        reset_alarm_frame.pack(side="left", padx=10)
        
        reset_alarm_btn = tk.Button(reset_alarm_frame, text="ریست آلارم\nو دتکتورها",
                                     bg="#FF0000", fg="white",
                                     font=("Arial", 14, "bold"),
                                     width=12, height=4,
                                     command=self._reset_alarms_and_detectors)
        reset_alarm_btn.pack(pady=10)
        
        for card in range(1, 5):
            det_frame = tk.Frame(top_section, bg="#1565C0")
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
            
            error_canvas = tk.Canvas(det_frame, width=50, height=50, bg="#1565C0", highlightthickness=0)
            error_canvas.pack(pady=5)
            error_light = error_canvas.create_oval(5, 5, 45, 45, fill="#FF0000", outline="white", width=2)
            self.card_error_lights[card] = (error_canvas, error_light)
        
        bottom_section = tk.Frame(page, bg="#1565C0")
        bottom_section.pack(fill="both", expand=True, padx=10, pady=10)
        
        canvas = tk.Canvas(bottom_section, bg="#1565C0", highlightthickness=0)
        h_scrollbar = ttk.Scrollbar(bottom_section, orient="horizontal", command=canvas.xview)
        v_scrollbar = ttk.Scrollbar(bottom_section, orient="vertical", command=canvas.yview)
        
        scrollable_frame = tk.Frame(canvas, bg="#1565C0")
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set)
        
        canvas.pack(side="top", fill="both", expand=True)
        h_scrollbar.pack(side="bottom", fill="x")
        v_scrollbar.pack(side="right", fill="y")
        
        table_frame = tk.Frame(scrollable_frame, bg="#1565C0")
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
        
        tk.Label(table_frame, text="", bg="#1565C0", width=16).grid(row=0, column=0, columnspan=2, padx=3, pady=3)
        for row_idx, text in row_labels.items():
            lbl = tk.Label(table_frame, text=text, bg="#1565C0", fg="white",
                          font=("Arial", 9, "bold"), width=16, anchor="e",
                          justify="right")
            lbl.grid(row=row_idx, column=0, columnspan=2, padx=3, pady=3, sticky="nsew")
        
        tk.Label(table_frame, text="SET POINT\n(100ms)", bg="#C2185B", fg="white",
                 font=("Arial", 10, "bold"), width=10, justify="center").grid(
                 row=ROW_GAP_SP, column=0, rowspan=2, padx=3, pady=3, sticky="nsew")
        tk.Label(table_frame, text="Gap", bg="#1565C0", fg="white",
                 font=("Arial", 9, "bold"), width=6).grid(row=ROW_GAP_SP, column=1, padx=3, pady=3)
        tk.Label(table_frame, text="Waste", bg="#1565C0", fg="white",
                 font=("Arial", 9, "bold"), width=6).grid(row=ROW_WASTE_SP, column=1, padx=3, pady=3)
        
        tk.Label(table_frame, text="PROCESS\nVALUE\n(100ms)", bg="#C2185B", fg="white",
                 font=("Arial", 10, "bold"), width=10, justify="center").grid(
                 row=ROW_GAP_PV, column=0, rowspan=2, padx=3, pady=3, sticky="nsew")
        tk.Label(table_frame, text="Gap", bg="#1565C0", fg="white",
                 font=("Arial", 9, "bold"), width=6).grid(row=ROW_GAP_PV, column=1, padx=3, pady=3)
        tk.Label(table_frame, text="Waste", bg="#1565C0", fg="white",
                 font=("Arial", 9, "bold"), width=6).grid(row=ROW_WASTE_PV, column=1, padx=3, pady=3)
        
        self.loop_status_widgets = {}
        
        for loop_num in range(1, 17):
            col = loop_num + 1
            extra_left = 15 if (loop_num - 1) % 4 == 0 and loop_num > 1 else 0
            self.loop_status_widgets[loop_num] = {}
            
            tk.Label(table_frame, text=f"لوپ {loop_num}",
                    bg="#1565C0", fg="white",
                    font=("Arial", 10, "bold")).grid(
                    row=0, column=col, padx=(3 + extra_left, 3), pady=3)
            
            alarm_canvas = tk.Canvas(table_frame, width=35, height=35, bg="#1565C0", highlightthickness=0)
            alarm_light = alarm_canvas.create_oval(5, 5, 30, 30, fill="black", outline="white", width=2)
            alarm_canvas.grid(row=ROW_ALARM, column=col, padx=(3 + extra_left, 3), pady=3)
            self.loop_status_widgets[loop_num]["alarm"] = (alarm_canvas, alarm_light)
            
            sensor_canvas = tk.Canvas(table_frame, width=35, height=35, bg="#1565C0", highlightthickness=0)
            sensor_light = sensor_canvas.create_oval(5, 5, 30, 30, fill="black", outline="white", width=2)
            sensor_canvas.grid(row=ROW_SENSOR, column=col, padx=(3 + extra_left, 3), pady=3)
            self.loop_status_widgets[loop_num]["sensor"] = (sensor_canvas, sensor_light)
            
            car_canvas = tk.Canvas(table_frame, width=35, height=35, bg="#1565C0", highlightthickness=0)
            car_light = car_canvas.create_oval(5, 5, 30, 30, fill="black", outline="white", width=2)
            car_canvas.grid(row=ROW_CAR, column=col, padx=(3 + extra_left, 3), pady=3)
            self.loop_status_widgets[loop_num]["car"] = (car_canvas, car_light)
            
            gap_sp_var = tk.StringVar(value="20")
            gap_sp_entry = tk.Entry(table_frame, textvariable=gap_sp_var, width=5, font=("Arial", 10, "bold"))
            gap_sp_entry.grid(row=ROW_GAP_SP, column=col, padx=(3 + extra_left, 3), pady=3)
            gap_sp_entry.bind("<Return>", lambda e, l=loop_num: self._save_loop_setpoint(l))
            self.loop_status_widgets[loop_num]["gap_sp"] = gap_sp_var
            
            waste_sp_var = tk.StringVar(value="50")
            waste_sp_entry = tk.Entry(table_frame, textvariable=waste_sp_var, width=5, font=("Arial", 10, "bold"))
            waste_sp_entry.grid(row=ROW_WASTE_SP, column=col, padx=(3 + extra_left, 3), pady=3)
            waste_sp_entry.bind("<Return>", lambda e, l=loop_num: self._save_loop_setpoint(l))
            self.loop_status_widgets[loop_num]["waste_sp"] = waste_sp_var
            
            gap_pv_var = tk.StringVar(value="0")
            gap_pv_entry = tk.Entry(table_frame, textvariable=gap_pv_var, width=5,
                                    font=("Arial", 10, "bold"), state="readonly",
                                    readonlybackground="#E0E0E0")
            gap_pv_entry.grid(row=ROW_GAP_PV, column=col, padx=(3 + extra_left, 3), pady=3)
            self.loop_status_widgets[loop_num]["gap_pv"] = gap_pv_var
            
            waste_pv_var = tk.StringVar(value="0")
            waste_pv_entry = tk.Entry(table_frame, textvariable=waste_pv_var, width=5,
                                      font=("Arial", 10, "bold"), state="readonly",
                                      readonlybackground="#E0E0E0")
            waste_pv_entry.grid(row=ROW_WASTE_PV, column=col, padx=(3 + extra_left, 3), pady=3)
            self.loop_status_widgets[loop_num]["waste_pv"] = waste_pv_var
            
            time_canvas = tk.Canvas(table_frame, width=35, height=35, bg="#1565C0", highlightthickness=0)
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
                print(f"خطا در ریست آلارم: {e}")
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
                print(f"خطا در ریست کارت دتکتور {card}: {e}")
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
                print(f"خطا در قطع/وصل دتکتور {card}: {e}")
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
                print(f"خطا در ذخیره SET POINT لوپ {loop_num}: {e}")
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
                print(f"خطا در بارگذاری وضعیت لوپ‌ها: {e}")
        
        threading.Thread(target=_load, daemon=True).start()
    
    def _update_loop_light(self, loop_num, light_type, color):
        if loop_num in self.loop_status_widgets:
            if light_type in self.loop_status_widgets[loop_num]:
                canvas, light_id = self.loop_status_widgets[loop_num][light_type]
                canvas.itemconfig(light_id, fill=color)
    
    def _auto_load_loop_status_loop(self):
        if not self.loop_status_page_auto_load_running:
            return
        
        if self.is_connected and self.client:
            self._load_loop_status()
        
        self.window.after(1000, self._auto_load_loop_status_loop)
    
    def build_ip_time_page(self):
        page = tk.Frame(self.content_frame, bg="#1565C0")
        
        ip_section = tk.Frame(page, bg="#1565C0")
        ip_section.pack(side="left", padx=30, pady=30, anchor="n")
        
        tk.Label(ip_section, text="تنظیمات IP", bg="#1565C0", fg="white",
                font=("Arial", 18, "bold")).pack(pady=20)
        
        ip_frame = tk.Frame(ip_section, bg="#1565C0")
        ip_frame.pack(fill="x", pady=10)
        
        tk.Label(ip_frame, text="IP Address", bg="#1565C0", fg="white",
                font=("Arial", 12, "bold"), width=12, anchor="w").pack(side="left", padx=5)
        
        self.ip_octets = []
        for i in range(4):
            entry = tk.Entry(ip_frame, width=4, font=("Arial", 11), justify="center")
            entry.pack(side="left", padx=2)
            self.ip_octets.append(entry)
        
        netmask_frame = tk.Frame(ip_section, bg="#1565C0")
        netmask_frame.pack(fill="x", pady=10)
        
        tk.Label(netmask_frame, text="Netmask", bg="#1565C0", fg="white",
                font=("Arial", 12, "bold"), width=12, anchor="w").pack(side="left", padx=5)
        
        self.netmask_octets = []
        for i in range(4):
            entry = tk.Entry(netmask_frame, width=4, font=("Arial", 11), justify="center")
            entry.pack(side="left", padx=2)
            self.netmask_octets.append(entry)
        
        gateway_frame = tk.Frame(ip_section, bg="#1565C0")
        gateway_frame.pack(fill="x", pady=10)
        
        tk.Label(gateway_frame, text="Gateway", bg="#1565C0", fg="white",
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
        
        time_section = tk.Frame(page, bg="#1565C0")
        time_section.pack(side="right", padx=30, pady=30, anchor="n")
        
        today_frame = tk.Frame(time_section, bg="#1565C0")
        today_frame.pack(fill="x", pady=20)
        
        tk.Label(today_frame, text="امروز", bg="#1565C0", fg="white",
                font=("Arial", 18, "bold")).pack(pady=10)
        
        day_frame = tk.Frame(today_frame, bg="#1565C0")
        day_frame.pack(fill="x", pady=5)
        
        self.today_day_var = tk.StringVar(value="چهارشنبه")
        today_day_combo = ttk.Combobox(day_frame, textvariable=self.today_day_var,
                                        values=self.day_names,
                                        state="readonly", width=12,
                                        font=("Arial", 11))
        today_day_combo.pack(side="left", padx=5)
        
        time_frame = tk.Frame(today_frame, bg="#1565C0")
        time_frame.pack(fill="x", pady=5)
        
        tk.Label(time_frame, text="ساعت", bg="#1565C0", fg="white",
                font=("Arial", 12, "bold"), width=8, anchor="w").pack(side="left", padx=5)
        
        self.today_hour = tk.Entry(time_frame, width=4, font=("Arial", 11), justify="center",
                                    state="readonly", readonlybackground="#FF9800")
        self.today_hour.pack(side="left", padx=2)
        
        self.today_minute = tk.Entry(time_frame, width=4, font=("Arial", 11), justify="center",
                                      state="readonly", readonlybackground="#FF9800")
        self.today_minute.pack(side="left", padx=2)
        
        self.today_second = tk.Entry(time_frame, width=4, font=("Arial", 11), justify="center",
                                      state="readonly", readonlybackground="#FF9800")
        self.today_second.pack(side="left", padx=2)
        
        gregorian_frame = tk.Frame(today_frame, bg="#1565C0")
        gregorian_frame.pack(fill="x", pady=5)
        
        tk.Label(gregorian_frame, text="تاریخ میلادی", bg="#1565C0", fg="white",
                font=("Arial", 12, "bold"), width=12, anchor="w").pack(side="left", padx=5)
        
        self.today_g_year = tk.Entry(gregorian_frame, width=5, font=("Arial", 11), justify="center",
                                      state="readonly", readonlybackground="#FF9800")
        self.today_g_year.pack(side="left", padx=2)
        
        self.today_g_month = tk.Entry(gregorian_frame, width=3, font=("Arial", 11), justify="center",
                                       state="readonly", readonlybackground="#FF9800")
        self.today_g_month.pack(side="left", padx=2)
        
        self.today_g_day = tk.Entry(gregorian_frame, width=3, font=("Arial", 11), justify="center",
                                     state="readonly", readonlybackground="#FF9800")
        self.today_g_day.pack(side="left", padx=2)
        
        shamsi_frame = tk.Frame(today_frame, bg="#1565C0")
        shamsi_frame.pack(fill="x", pady=5)
        
        tk.Label(shamsi_frame, text="تاریخ شمسی", bg="#1565C0", fg="white",
                font=("Arial", 12, "bold"), width=12, anchor="w").pack(side="left", padx=5)
        
        self.today_s_year = tk.Entry(shamsi_frame, width=5, font=("Arial", 11), justify="center",
                                      state="readonly", readonlybackground="#FF9800")
        self.today_s_year.pack(side="left", padx=2)
        
        self.today_s_month = tk.Entry(shamsi_frame, width=3, font=("Arial", 11), justify="center",
                                       state="readonly", readonlybackground="#FF9800")
        self.today_s_month.pack(side="left", padx=2)
        
        self.today_s_day = tk.Entry(shamsi_frame, width=3, font=("Arial", 11), justify="center",
                                     state="readonly", readonlybackground="#FF9800")
        self.today_s_day.pack(side="left", padx=2)
        
        set_time_frame = tk.Frame(time_section, bg="#1565C0")
        set_time_frame.pack(fill="x", pady=20)
        
        tk.Label(set_time_frame, text="تنظیم زمان", bg="#1565C0", fg="white",
                font=("Arial", 18, "bold")).pack(pady=10)
        
        refresh_time_btn = tk.Button(set_time_frame, text="Refresh", bg="#4CAF50", fg="white",
                                      font=("Arial", 12, "bold"), width=10,
                                      command=self._refresh_time_settings)
        refresh_time_btn.pack(pady=10)
        
        set_day_frame = tk.Frame(set_time_frame, bg="#1565C0")
        set_day_frame.pack(fill="x", pady=5)
        
        self.set_day_var = tk.StringVar(value="چهارشنبه")
        set_day_combo = ttk.Combobox(set_day_frame, textvariable=self.set_day_var,
                                      values=self.day_names,
                                      state="readonly", width=12,
                                      font=("Arial", 11))
        set_day_combo.pack(side="left", padx=5)
        
        set_time_input_frame = tk.Frame(set_time_frame, bg="#1565C0")
        set_time_input_frame.pack(fill="x", pady=5)
        
        tk.Label(set_time_input_frame, text="ساعت", bg="#1565C0", fg="white",
                font=("Arial", 12, "bold"), width=8, anchor="w").pack(side="left", padx=5)
        
        self.set_hour = tk.Entry(set_time_input_frame, width=4, font=("Arial", 11), justify="center",
                                  bg="#F44336", fg="white")
        self.set_hour.pack(side="left", padx=2)
        
        self.set_minute = tk.Entry(set_time_input_frame, width=4, font=("Arial", 11), justify="center",
                                    bg="#F44336", fg="white")
        self.set_minute.pack(side="left", padx=2)
        
        self.set_second = tk.Entry(set_time_input_frame, width=4, font=("Arial", 11), justify="center",
                                    bg="#F44336", fg="white")
        self.set_second.pack(side="left", padx=2)
        
        set_gregorian_frame = tk.Frame(set_time_frame, bg="#1565C0")
        set_gregorian_frame.pack(fill="x", pady=5)
        
        tk.Label(set_gregorian_frame, text="تاریخ میلادی", bg="#1565C0", fg="white",
                font=("Arial", 12, "bold"), width=12, anchor="w").pack(side="left", padx=5)
        
        self.set_g_year = tk.Entry(set_gregorian_frame, width=5, font=("Arial", 11), justify="center",
                                    bg="#F44336", fg="white")
        self.set_g_year.pack(side="left", padx=2)
        
        self.set_g_month = tk.Entry(set_gregorian_frame, width=3, font=("Arial", 11), justify="center",
                                     bg="#F44336", fg="white")
        self.set_g_month.pack(side="left", padx=2)
        
        self.set_g_day = tk.Entry(set_gregorian_frame, width=3, font=("Arial", 11), justify="center",
                                   bg="#F44336", fg="white")
        self.set_g_day.pack(side="left", padx=2)
        
        dst_frame = tk.Frame(set_time_frame, bg="#1565C0")
        dst_frame.pack(fill="x", pady=10)
        
        self.dst_var = tk.StringVar(value="اول فروردین و آخر شهریور تغییر ساعت اعمال گردد")
        dst_combo = ttk.Combobox(dst_frame, textvariable=self.dst_var,
                                  values=["اول فروردین و آخر شهریور تغییر ساعت اعمال گردد", 
                                          "تغییری در زمان صورت نگیرد"],
                                  state="readonly", width=45,
                                  font=("Arial", 10))
        dst_combo.pack(side="left", padx=5)
        
        set_time_btn = tk.Button(set_time_frame, text="SET", bg="#4CAF50", fg="white",
                                  font=("Arial", 14, "bold"), width=8,
                                  command=self._set_time)
        set_time_btn.pack(pady=15)
        
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
    
    def _refresh_ip_settings(self):
        if not self.is_connected or not self.client:
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
                
                self.window.after(0, lambda: messagebox.showinfo("موفق", "تنظیمات IP بارگذاری شد!"))
            except Exception as e:
                print(f"خطا در بارگذاری IP: {e}")
                self._handle_connection_error()
        
        threading.Thread(target=_load, daemon=True).start()
    
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
                print(f"خطا در ذخیره IP: {e}")
                self._handle_connection_error()
        
        threading.Thread(target=_save, daemon=True).start()
    
    def _refresh_time_settings(self):
        if not self.is_connected or not self.client:
            messagebox.showwarning("هشدار", "ابتدا به PLC متصل شوید!")
            return
        
        def _load():
            try:
                with self.plc_lock:
                    time_result = self.client.read_holding_registers(address=5409, count=3, device_id=1)
                
                if not time_result.isError():
                    sec = time_result.registers[0]
                    minute = time_result.registers[1]
                    hour = time_result.registers[2]
                    
                    self.window.after(0, self._set_entry_text, self.today_second, f"{sec:02d}")
                    self.window.after(0, self._set_entry_text, self.today_minute, f"{minute:02d}")
                    self.window.after(0, self._set_entry_text, self.today_hour, f"{hour:02d}")
                    
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
                    
                    self.window.after(0, self._set_entry_text, self.set_g_year, f"{gy:04d}")
                    self.window.after(0, self._set_entry_text, self.set_g_month, f"{gmo:02d}")
                    self.window.after(0, self._set_entry_text, self.set_g_day, f"{gd:02d}")
                    
                    if not day_of_week_result.isError():
                        day_idx = day_of_week_result.registers[0]
                        if 0 <= day_idx < len(self.day_names):
                            self.window.after(0, lambda: self.today_day_var.set(self.day_names[day_idx]))
                            self.window.after(0, lambda: self.set_day_var.set(self.day_names[day_idx]))
                
                with self.plc_lock:
                    dst_result = self.client.read_holding_registers(address=self.DST_ADDRESS, count=1, device_id=1)
                
                if not dst_result.isError():
                    dst_value = dst_result.registers[0]
                    if dst_value == 0:
                        self.window.after(0, lambda: self.dst_var.set("اول فروردین و آخر شهریور تغییر ساعت اعمال گردد"))
                    else:
                        self.window.after(0, lambda: self.dst_var.set("تغییری در زمان صورت نگیرد"))
                
                self.window.after(0, lambda: messagebox.showinfo("موفق", "زمان بارگذاری شد!"))
            except Exception as e:
                print(f"خطا در بارگذاری زمان: {e}")
                self._handle_connection_error()
        
        threading.Thread(target=_load, daemon=True).start()
    
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
                
                from datetime import datetime
                dt = datetime(year, month, day)
                day_of_week = (dt.weekday() + 2) % 7
                
                dst_value = 0 if self.dst_var.get() == "اول فروردین و آخر شهریور تغییر ساعت اعمال گردد" else 1
                
                with self.plc_lock:
                    self.client.write_register(address=4246, value=year, device_id=1)
                    self.client.write_register(address=4247, value=day_of_week, device_id=1)
                    self.client.write_register(address=4248, value=month, device_id=1)
                    self.client.write_register(address=4249, value=day, device_id=1)
                    self.client.write_register(address=4250, value=hour, device_id=1)
                    self.client.write_register(address=4251, value=minute, device_id=1)
                    self.client.write_register(address=4252, value=second, device_id=1)
                    self.client.write_register(address=self.DST_ADDRESS, value=dst_value, device_id=1)
                
                time.sleep(0.3)
                with self.plc_lock:
                    self.client.write_coil(address=self.TIME_SET_COIL, value=True, device_id=1)
                time.sleep(0.5)
                with self.plc_lock:
                    self.client.write_coil(address=self.TIME_SET_COIL, value=False, device_id=1)
                
                self.window.after(0, lambda: messagebox.showinfo("موفق", "زمان با موفقیت تنظیم شد!"))
            except Exception as e:
                print(f"خطا در ذخیره زمان: {e}")
                self._handle_connection_error()
                self.window.after(0, lambda: messagebox.showerror("خطا", f"خطا در ذخیره زمان: {e}"))
        
        threading.Thread(target=_save, daemon=True).start()
    
    def build_lamp_test_page(self):
        page = tk.Frame(self.content_frame, bg="#1565C0")
        
        title_frame = tk.Frame(page, bg="#1565C0")
        title_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(title_frame, text="تست لامپ‌ها", bg="#1565C0", fg="white",
                font=("Arial", 20, "bold")).pack()
        
        main_frame = tk.Frame(page, bg="#1565C0")
        main_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.lamp_test_canvas = tk.Canvas(main_frame, width=800, height=600, 
                                           bg="#1565C0", highlightthickness=0)
        self.lamp_test_canvas.pack(side="left", fill="both", expand=True)
        
        control_frame = tk.Frame(main_frame, bg="#1565C0", width=250)
        control_frame.pack(side="right", fill="y", padx=20)
        control_frame.pack_propagate(False)
        
        tk.Label(control_frame, text="حالت تست لامپ:", bg="#1565C0", fg="white",
                font=("Arial", 12, "bold")).pack(pady=10)
        
        self.lamp_test_enabled_var = tk.IntVar(value=0)
        self.lamp_test_toggle_btn = tk.Button(control_frame, 
                                               text="غیرفعال", 
                                               bg="#F44336", fg="white",
                                               font=("Arial", 14, "bold"), width=15,
                                               command=self._toggle_lamp_test_mode)
        self.lamp_test_toggle_btn.pack(pady=10)
        
        self.lamp_test_status_label = tk.Label(control_frame, text="وضعیت: غیرفعال",
                                                bg="#FF9800", fg="white",
                                                font=("Arial", 11, "bold"), width=20)
        self.lamp_test_status_label.pack(pady=10)
        
        tk.Label(control_frame, text="کنترل پارت‌ها:", bg="#1565C0", fg="white",
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
        
        self.pages[7] = page
    
    def _draw_lamp_test_lights(self):
        canvas = self.lamp_test_canvas
        canvas.delete("all")
        
        W, H = 800, 600
        
        canvas.create_rectangle(300, 0, 500, H, fill="#404040")
        canvas.create_rectangle(0, 200, W, 400, fill="#404040")
        
        for i in range(0, 100, 10):
            canvas.create_line(300+i, 200, 300+i+5, 200, fill="white", width=5)
            canvas.create_line(300+i, 400, 300+i+5, 400, fill="white", width=5)
            canvas.create_line(300, 200+i, 300, 200+i+5, fill="white", width=5)
            canvas.create_line(500, 200+i, 500, 200+i+5, fill="white", width=5)
        
        parts_positions = [
            (400, 80, "PART 1", 1),
            (500, 80, "PART 2", 2),
            (680, 300, "PART 3", 3),
            (680, 350, "PART 4", 4),
            (500, 520, "PART 5", 5),
            (400, 520, "PART 6", 6),
            (120, 350, "PART 7", 7),
            (120, 300, "PART 8", 8),
        ]
        
        self.lamp_test_lights = {}
        self.lamp_test_lights_colors = {}
        
        base_address = self.LAMP_TEST_BASE_ADDRESS
        
        for x, y, name, part_num in parts_positions:
            canvas.create_rectangle(x-40, y-25, x+40, y+5, fill="#FF9800", outline="black")
            canvas.create_text(x, y-10, text=name, fill="white", font=("Arial", 10, "bold"))
            
            light_y = y + 35
            colors = ["#FF0000", "#FFFF00", "#00FF00"]
            light_names = ["red", "yellow", "green"]
            light_addresses = [
                base_address + (part_num - 1) * 3,
                base_address + (part_num - 1) * 3 + 1,
                base_address + (part_num - 1) * 3 + 2
            ]
            
            for i, (color, light_name, addr) in enumerate(zip(colors, light_names, light_addresses)):
                light_x = x - 30 + i * 30
                light_id = canvas.create_oval(light_x-12, light_y-12, 
                                              light_x+12, light_y+12,
                                              fill="#333333", outline="black", width=2)
                
                key = f"part{part_num}_{light_name}"
                self.lamp_test_lights[key] = {
                    "id": light_id,
                    "address": addr,
                    "color": color,
                    "state": False
                }
                self.lamp_test_lights_colors[light_id] = color
                
                canvas.tag_bind(light_id, "<Button-1>", 
                              lambda e, k=key: self._toggle_lamp(k))
        
        self.lamp_test_positions = parts_positions
    
    def _toggle_lamp_test_mode(self):
        if not self.is_connected or not self.client:
            messagebox.showwarning("هشدار", "ابتدا به PLC متصل شوید!")
            return
        
        current_value = self.lamp_test_enabled_var.get()
        new_value = 1 - current_value
        
        def _write():
            try:
                with self.plc_lock:
                    self.client.write_register(address=self.LAMP_TEST_MODE_ADDRESS, value=new_value, device_id=1)
                
                self.lamp_test_enabled_var.set(new_value)
                
                if new_value == 1:
                    self.window.after(0, lambda: self.lamp_test_toggle_btn.configure(
                        text="فعال", bg="#4CAF50"))
                    self.window.after(0, lambda: self.lamp_test_status_label.configure(
                        text="وضعیت: فعال", bg="#4CAF50"))
                else:
                    self.window.after(0, lambda: self.lamp_test_toggle_btn.configure(
                        text="غیرفعال", bg="#F44336"))
                    self.window.after(0, lambda: self.lamp_test_status_label.configure(
                        text="وضعیت: غیرفعال", bg="#FF9800"))
                    self.window.after(0, lambda: self._set_all_lamps_visual(False))
            
            except Exception as e:
                print(f"خطا در تغییر حالت تست: {e}")
                self._handle_connection_error()
        
        threading.Thread(target=_write, daemon=True).start()
    
    def _toggle_lamp(self, key):
        if not self.is_connected or not self.client:
            messagebox.showwarning("هشدار", "ابتدا به PLC متصل شوید!")
            return
        
        if self.lamp_test_enabled_var.get() == 0:
            messagebox.showinfo("اطلاع", "ابتدا حالت تست را فعال کنید!")
            return
        
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
                print(f"خطا در تغییر وضعیت چراغ: {e}")
                self._handle_connection_error()
        
        threading.Thread(target=_write, daemon=True).start()
    
    def _set_all_lamps(self, state):
        if not self.is_connected or not self.client:
            messagebox.showwarning("هشدار", "ابتدا به PLC متصل شوید!")
            return
        
        if self.lamp_test_enabled_var.get() == 0:
            messagebox.showinfo("اطلاع", "ابتدا حالت تست را فعال کنید!")
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
                print(f"خطا در تغییر وضعیت همه چراغ‌ها: {e}")
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
                print(f"خطا نقشه فاز {phase_num}: {e}")
        
        for phase_num, addresses in self.phase_lamp_mapping.items():
            try:
                result = self._read_lamp_color(addresses)
                if phase_num in self.phase_light_canvases:
                    self.window.after(0, self._set_phase_light,
                                       self.phase_light_canvases[phase_num], result["color"])
            except Exception as e:
                print(f"خطا چراغ بالای فاز {phase_num}: {e}")
    
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
            self.window.after(1000, lambda: entry.configure(bg="white"))
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
            entry.configure(bg="white")
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
                self.window.after(200, lambda: setattr(self, 'is_editing_settings', False))
                
                if setting_name == "control_mode":
                    self.window.after(300, self._update_police_button)
            except Exception as e:
                self.window.after(0, lambda: self.settings_status.configure(
                    text=f" خطا: {str(e)}", fg="red"))
                self.window.after(200, lambda: setattr(self, 'is_editing_settings', False))
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
                print(f"خطا نوشتن Coil {address}: {e}")
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
        
        if self.selected_option == 0:
            if self.is_connected and self.client:
                threading.Thread(target=self._full_refresh, daemon=True).start()
        
        self.window.after(500, self._auto_update_loop)
    
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
            
            if not self.is_editing_table:
                self._read_phase_table_values()
            
            if not self.is_editing_settings:
                self._read_settings_values()
            
            self.window.after(0, self._update_police_button)
        except Exception as e:
            print(f"خطا در _full_refresh: {e}")
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
                            readonly_entry = entry_dict["readonly"]
                            self.window.after(0, lambda e=readonly_entry, v=value: self._safe_set_readonly(e, str(v)))
        except Exception as e:
            print(f"خطا در خواندن جدول فازها: {e}")
    
    def _read_settings_values(self):
        try:
            sensors_result = self._read_register(self.SETTINGS_ADDRESSES["sensors"]["address"], 1)
            if not sensors_result.isError():
                sensors_value = "فعال" if sensors_result.registers[0] == 1 else "غیر فعال"
                self.window.after(0, lambda: self.sensors_var.set(sensors_value))
            
            green_result = self._read_register(self.SETTINGS_ADDRESSES["green_time"]["address"], 1)
            if not green_result.isError():
                green_value = "دستی" if green_result.registers[0] == 1 else "اتوماتیک"
                self.window.after(0, lambda: self.green_time_var.set(green_value))
            
            control_result = self._read_register(self.SETTINGS_ADDRESSES["control_mode"]["address"], 1)
            if not control_result.isError():
                control_map = {0: "اتوماتیک", 1: "پلیس", 2: "دائمی فلش"}
                control_value = control_map.get(control_result.registers[0], "اتوماتیک")
                self.window.after(0, lambda: self.control_var.set(control_value))
        except Exception as e:
            print(f"خطا در خواندن تنظیمات: {e}")
    
    def _safe_set_readonly(self, entry, value):
        try:
            entry.configure(state="normal")
            entry.delete(0, "end")
            entry.insert(0, value)
            entry.configure(state="readonly")
        except:
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
        elif idx == 7:
            if 7 not in self.pages:
                self.build_lamp_test_page()
            self.pages[7].pack(fill="both", expand=True)
            self.stop_auto_update()
        else:
            self.stop_auto_update()
            self.timing_page_auto_load_running = False
            self.blink_page_auto_load_running = False
            self.part_settings_page_auto_load_running = False
            self.loop_settings_page_auto_load_running = False
            self.loop_status_page_auto_load_running = False
            placeholder = tk.Frame(self.content_frame, bg="white")
            placeholder.pack(fill="both", expand=True)
            
            tk.Label(placeholder, text=f"گزینه {idx+1}", 
                    bg="white", font=("Arial", 20, "bold")).pack(pady=50)
            tk.Label(placeholder, text="به زودی پیاده‌سازی می‌شود...",
                    bg="white", font=("Arial", 14)).pack()
    
    def go_back(self):
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
        if self.is_connected:
            self.disconnect()
        self.control_frame.pack_forget()
        self.login_frame.pack(fill="both", expand=True)
        self.current_page = "login"
    
    def enter_control_page(self):
        self.login_frame.pack_forget()
        self.control_frame.pack(fill="both", expand=True)
        self.current_page = "main"
        self.demo_mode = False
        self.show_page(0)
    
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
            print(f"خطا: {e}")
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
            print(f"خطا: {e}")
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
            print(f"خطا: {e}")
    
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
            print(f"خطا: {e}")
    
    def run(self):
        self.window.mainloop()

if __name__ == "__main__":
    app = TrafficControllerApp()
    app.run()