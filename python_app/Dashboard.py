#!/usr/bin/env python3
import tkinter as tk
from tkinter import messagebox, ttk
import requests
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import deque
import numpy as np
import time
import csv
import threading

# Konfigurace - IP adresa ESP32
URL = "http://192.168.4.1"

class AnemoDashboardV45:
    def __init__(self, root):
        self.root = root
        self.root.title("Anemometr Dashboard V4.5 - Science Edition")
        self.root.geometry("1100x850")

        # Styly a barvy
        self.dark_bg = '#0a0a0a'
        self.dark_fg = '#00ffcc'
        self.light_bg = '#f0f0f0'
        self.light_fg = '#000000'
        self.is_dark = True

        # Data
        self.history_s = deque(maxlen=100)
        self.history_raw = {
            'tp': deque(maxlen=100), 'tz': deque(maxlen=100),
            'tl': deque(maxlen=100), 'tpr': deque(maxlen=100)
        }
        self.times = deque(maxlen=100)
        self.is_logging = False
        self.science_mode = False
        self.last_data = {}
        self.start_t = time.time()

        # UI Inicializace
        self.main_frame = tk.Frame(root, bg=self.dark_bg)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Header
        self.header = tk.Frame(self.main_frame, bg=self.dark_bg)
        self.header.pack(fill=tk.X, pady=10)

        self.lbl_title = tk.Label(self.header, text="SONIC ANEMO V4.5 - PRO", fg=self.dark_fg, bg=self.dark_bg, font=("Arial", 16, "bold"))
        self.lbl_title.pack()

        self.lbl_speed = tk.Label(self.header, text="0.00 m/s", fg=self.dark_fg, bg=self.dark_bg, font=("Consolas", 50, "bold"))
        self.lbl_speed.pack()

        self.lbl_info = tk.Label(self.header, text="Připojování...", fg="#ff3300", bg=self.dark_bg, font=("Arial", 10))
        self.lbl_info.pack()

        # Matplotlib Setup
        plt.style.use('dark_background')
        self.fig = plt.figure(figsize=(10, 6), facecolor=self.dark_bg)
        self.gs = self.fig.add_gridspec(2, 2)

        # 1. Polární / Science graf
        self.ax_left = self.fig.add_subplot(self.gs[0, 0], projection='polar')
        self.line_now, = self.ax_left.plot([], [], color=self.dark_fg, lw=4)

        # 2. Časový graf (Rychlost nebo ToF)
        self.ax_right = self.fig.add_subplot(self.gs[0, 1])
        self.line_main, = self.ax_right.plot([], [], color=self.dark_fg, lw=2)
        self.ax_right.set_facecolor('#111')

        # 3. Boxplot / Raw Stats
        self.ax_bottom = self.fig.add_subplot(self.gs[1, :])
        self.ax_bottom.set_facecolor('#111')

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.main_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10)

        # Ovládací panel
        ctrl = tk.Frame(self.main_frame, bg=self.dark_bg)
        ctrl.pack(fill=tk.X, pady=15)

        # Režimy
        self.btn_theme = tk.Button(ctrl, text="LIGHT MODE", command=self.toggle_theme, width=15)
        self.btn_theme.pack(side=tk.LEFT, padx=10)

        self.lbl_sci = tk.Label(ctrl, text="SCIENCE MODE:", fg="white", bg=self.dark_bg)
        self.lbl_sci.pack(side=tk.LEFT, padx=5)
        self.sci_switch = ttk.Checkbutton(ctrl, command=self.toggle_science)
        self.sci_switch.pack(side=tk.LEFT, padx=5)

        # Akce
        tk.Button(ctrl, text="ZERO", command=lambda: self.send_cmd("/zero"), width=10).pack(side=tk.LEFT, padx=5)
        self.btn_log = tk.Button(ctrl, text="LOG TO CSV", command=self.toggle_log, bg="#222", fg="white", width=15)
        self.btn_log.pack(side=tk.LEFT, padx=20)

        self.update_loop()

    def toggle_theme(self):
            self.is_dark = not self.is_dark
            # Definice barev podle režimu
            bg = self.dark_bg if self.is_dark else self.light_bg
            fg = self.dark_fg if self.is_dark else self.light_fg
            plot_bg = '#111111' if self.is_dark else '#ffffff' # Pozadí vnitřku grafu

            # UI prvky
            self.main_frame.config(bg=bg)
            self.header.config(bg=bg)
            self.lbl_title.config(bg=bg, fg=fg)
            self.lbl_speed.config(bg=bg, fg=fg)
            self.lbl_info.config(bg=bg)
            self.lbl_sci.config(bg=bg, fg=fg)

            # Matplotlib Figure pozadí
            self.fig.set_facecolor(bg)

            # Nastavení barev pro všechny osy
            for ax in [self.ax_left, self.ax_right, self.ax_bottom]:
                ax.set_facecolor(plot_bg)
                ax.tick_params(colors=fg)
                ax.xaxis.label.set_color(fg)
                ax.yaxis.label.set_color(fg)
                ax.title.set_color(fg)
                for spine in ax.spines.values():
                    spine.set_color(fg)

            # Polární graf má specifické mřížky
            self.ax_left.grid(color=fg, alpha=0.3)

            if self.is_dark:
                self.btn_theme.config(text="LIGHT MODE", bg="#333", fg="white")
            else:
                self.btn_theme.config(text="DARK MODE", bg="#ddd", fg="black")

            self.canvas.draw()

    def toggle_science(self):
        self.science_mode = not self.science_mode
        self.ax_right.clear()
        self.line_main, = self.ax_right.plot([], [], color=self.dark_fg if self.is_dark else 'blue')

    def send_cmd(self, path):
        threading.Thread(target=lambda: requests.get(f"{URL}{path}"), daemon=True).start()

    def toggle_log(self):
        self.is_logging = not self.is_logging
        if self.is_logging:
            filename = f"science_log_{int(time.time())}.csv"
            self.f = open(filename, "w", newline="")
            self.writer = csv.writer(self.f)
            self.writer.writerow(["Timestamp", "ESP_Uptime", "Speed", "Deg", "Temp", "TP", "TZ", "TL", "TPR"])
            self.btn_log.config(bg="#e74c3c", text="STOP LOG")
        else:
            if hasattr(self, 'f'): self.f.close()
            self.btn_log.config(bg="#222", text="LOG TO CSV")

    def fetch_data(self):
        try:
            r = requests.get(f"{URL}/data", timeout=0.5)
            data = r.json()
            self.last_data = data

            s = data.get('speed', 0)
            raw = data.get('raw', {})

            self.history_s.append(s)
            self.times.append(time.time() - self.start_t)

            for k in self.history_raw:
                self.history_raw[k].append(raw.get(k, 0))

            if self.is_logging:
                self.writer.writerow([time.time(), data.get('up'), s, data.get('deg'), data.get('temp'),
                                    raw.get('tp'), raw.get('tz'), raw.get('tl'), raw.get('tpr')])
        except:
            pass

    def update_loop(self):
            threading.Thread(target=self.fetch_data, daemon=True).start()

            if self.last_data:
                d = self.last_data
                raw = d.get('raw', {})
                fg = self.dark_fg if self.is_dark else 'black' # Dynamická barva čáry

                self.lbl_speed.config(text=f"{d['speed']:.2f} m/s")
                self.lbl_info.config(text=f"Teplota: {d['temp']:.1f}°C | ESP Uptime: {d['up']/1000:.1f}s",
                                    fg="#00aa00" if not self.is_dark else "#00ff00")

                if not self.science_mode:
                    # Klasický režim
                    self.ax_left.set_theta_zero_location('N')
                    self.ax_left.set_theta_direction(-1)
                    rad = np.deg2rad(d.get('deg', 0))
                    self.line_now.set_data([rad, rad], [0, d['speed']])
                    self.line_now.set_color(self.dark_fg if self.is_dark else 'blue')
                    self.ax_left.set_rmax(max(5, d['speed'] + 1))

                    self.line_main.set_data(list(self.times), list(self.history_s))
                    self.line_main.set_color(self.dark_fg if self.is_dark else 'blue')
                    self.ax_right.set_title("Rychlost v čase (m/s)")
                else:
                    # Science režim
                    self.ax_right.clear()
                    # Vynucení pozadí po clear()
                    self.ax_right.set_facecolor('#111111' if self.is_dark else '#ffffff')
                    self.ax_right.plot(list(self.times), list(self.history_raw['tp']), label='TP', color='#ff3300')
                    self.ax_right.plot(list(self.times), list(self.history_raw['tz']), label='TZ', color='#0033ff')
                    self.ax_right.legend(loc='upper left', fontsize='x-small')
                    self.ax_right.set_title("Surové ToF Osa Y (us)")

                if len(self.history_s) > 10:
                    self.ax_bottom.clear()
                    self.ax_bottom.set_facecolor('#111111' if self.is_dark else '#ffffff')
                    bp = self.ax_bottom.boxplot([list(self.history_s)], vert=False, patch_artist=True)
                    # Barva boxplotu pro light mode
                    for patch in bp['boxes']:
                        patch.set_facecolor(self.dark_fg if self.is_dark else '#add8e6')
                    self.ax_bottom.set_title("Statistický rozptyl měření", fontsize=9)

                self.canvas.draw_idle()

            self.root.after(300, self.update_loop)
if __name__ == "__main__":
    root = tk.Tk()
    app = AnemoDashboardV45(root)
    root.mainloop()
