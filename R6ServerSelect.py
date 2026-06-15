import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import configparser
import os
import sys
import time
import traceback
import webbrowser
from typing import Optional, Dict, Tuple, List
from ping3 import ping as icmp_ping


AUTO_SERVER_NAME = "Auto (Default)"
WEBSITE_URL = "https://recruitofficial.com"
YOUTUBE_URL = "https://www.youtube.com/@Im_Recruit"
APP_ICON = "logo.ico"


def resource_path(relative_path: str) -> str:
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


SERVERS: Dict[str, Tuple[str, Optional[str]]] = {
    AUTO_SERVER_NAME: ("default", None),
    "Asia Pacific - Sydney": ("gamelift/ap-southeast-2", "dynamodb.ap-southeast-2.amazonaws.com"),
    "Asia Pacific - Tokyo": ("gamelift/ap-northeast-1", "dynamodb.ap-northeast-1.amazonaws.com"),
    "Asia Pacific - Osaka": ("gamelift/ap-northeast-3", "dynamodb.ap-northeast-3.amazonaws.com"),
    "Asia Pacific - Seoul": ("gamelift/ap-northeast-2", "dynamodb.ap-northeast-2.amazonaws.com"),
    "Asia Pacific - Hong Kong": ("gamelift/ap-east-1", "dynamodb.ap-east-1.amazonaws.com"),
    "Asia Pacific - Singapore": ("gamelift/ap-southeast-1", "dynamodb.ap-southeast-1.amazonaws.com"),
    "Asia Pacific - Mumbai": ("gamelift/ap-south-1", "dynamodb.ap-south-1.amazonaws.com"),
    "Europe - Stockholm": ("gamelift/eu-north-1", "dynamodb.eu-north-1.amazonaws.com"),
    "Europe - Ireland": ("gamelift/eu-west-1", "dynamodb.eu-west-1.amazonaws.com"),
    "Europe - London": ("gamelift/eu-west-2", "dynamodb.eu-west-2.amazonaws.com"),
    "Europe - Frankfurt": ("gamelift/eu-central-1", "dynamodb.eu-central-1.amazonaws.com"),
    "Europe - Paris": ("gamelift/eu-west-3", "dynamodb.eu-west-3.amazonaws.com"),
    "Europe - Milan": ("gamelift/eu-south-1", "dynamodb.eu-south-1.amazonaws.com"),
    "Africa - Cape Town": ("gamelift/af-south-1", "dynamodb.af-south-1.amazonaws.com"),
    "South America - São Paulo": ("gamelift/sa-east-1", "dynamodb.sa-east-1.amazonaws.com"),
    "US East - N. Virginia": ("gamelift/us-east-1", "dynamodb.us-east-1.amazonaws.com"),
    "US East - Ohio": ("gamelift/us-east-2", "dynamodb.us-east-2.amazonaws.com"),
    "Canada - Central": ("gamelift/ca-central-1", "dynamodb.ca-central-1.amazonaws.com"),
    "US West - N. California": ("gamelift/us-west-1", "dynamodb.us-west-1.amazonaws.com"),
    "US West - Oregon": ("gamelift/us-west-2", "dynamodb.us-west-2.amazonaws.com"),
    "UAE North": ("playfab/uaenorth", "dynamodb.me-central-1.amazonaws.com"),
}


def get_latency_color(latency_ms: int) -> str:
    if latency_ms <= 50:
        return "#4CAF50"
    if latency_ms <= 100:
        return "#FFC107"
    if latency_ms < 9999:
        return "#F44336"
    return "gray"


class R6ServerSelect(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("R6 Server Select")
        self.geometry("820x760")
        self.resizable(False, False)

        try:
            self.iconbitmap(resource_path(APP_ICON))
        except Exception:
            pass

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.ini_full_path: Optional[str] = None
        self.ini_path_display = tk.StringVar(value="No file selected")
        self.selected_server: Optional[str] = None
        self.auto_sort_var = ctk.BooleanVar(value=True)

        self.rows: Dict[str, Tuple[ctk.CTkFrame, ctk.CTkLabel, ctk.CTkLabel]] = {}
        self.latencies: Dict[str, int] = {name: 9999 for name in SERVERS}
        self.current_order: List[str] = list(SERVERS.keys())

        self._create_widgets()
        self._start_ping_threads()

    def _create_widgets(self):
        ctk.CTkLabel(self, text="R6 Server Select", font=("Arial", 20, "bold")).pack(pady=10)

        file_frame = ctk.CTkFrame(self)
        file_frame.pack(pady=5, fill="x", padx=10)

        ctk.CTkLabel(file_frame, text="Current Profile:").pack(side="left", padx=(8, 0))
        ctk.CTkLabel(file_frame, textvariable=self.ini_path_display, text_color="#10B981").pack(side="left", padx=8)

        ctk.CTkButton(file_frame, text="Browse / Change File", command=self.browse_file).pack(side="right", padx=8, pady=8)

        options_frame = ctk.CTkFrame(self, fg_color="transparent")
        options_frame.pack(fill="x", padx=10)

        ctk.CTkCheckBox(
            options_frame,
            text="Auto-Sort by Average Latency",
            variable=self.auto_sort_var,
            checkbox_height=18,
            checkbox_width=18
        ).pack(side="left", padx=5, pady=(0, 5))

        self.ping_frame = ctk.CTkScrollableFrame(self)
        self.ping_frame.pack(pady=10, fill="both", expand=True, padx=10)

        header_row = ctk.CTkFrame(self.ping_frame, fg_color="transparent")
        header_row.pack(anchor="w", pady=(5, 0), padx=10, fill="x")

        ctk.CTkLabel(header_row, text="SERVER REGION", width=330, anchor="w", text_color="gray").pack(side="left")
        ctk.CTkLabel(header_row, text="AVG / JITTER / LOSS", width=330, anchor="w", text_color="gray").pack(side="left")

        for name in SERVERS:
            row = ctk.CTkFrame(self.ping_frame)
            row.pack(anchor="w", pady=2, padx=10, fill="x")

            name_label = ctk.CTkLabel(row, text=name, width=330, anchor="w")
            name_label.pack(side="left", padx=4, pady=4)

            ping_label = ctk.CTkLabel(row, text="…", width=330, anchor="w")
            ping_label.pack(side="left", padx=4, pady=4)

            for widget in (row, name_label, ping_label):
                widget.bind("<Button-1>", lambda e, n=name: self.select_server(n))

            self.rows[name] = (row, name_label, ping_label)

        ctk.CTkButton(self, text="Save to INI", command=self.save_choice, height=36).pack(pady=10)

        bottom_bar = ctk.CTkFrame(self, fg_color="transparent")
        bottom_bar.pack(side="bottom", fill="x", pady=5, padx=8)

        credit_label = ctk.CTkLabel(
            bottom_bar,
            text="Made with ❤ by Recruit",
            text_color="#1E90FF",
            cursor="hand2",
            font=("Arial", 12, "underline")
        )
        credit_label.pack(side="left")
        credit_label.bind("<Button-1>", lambda e: webbrowser.open(YOUTUBE_URL))

        website_label = ctk.CTkLabel(
            bottom_bar,
            text="recruitofficial.com",
            text_color="#1E90FF",
            cursor="hand2",
            font=("Arial", 12, "underline")
        )
        website_label.pack(side="right")
        website_label.bind("<Button-1>", lambda e: webbrowser.open(WEBSITE_URL))

    def _start_ping_threads(self):
        for name, (_, host) in SERVERS.items():
            threading.Thread(target=self.ping_loop, args=(name, host), daemon=True).start()

    def browse_file(self):
        base_path = os.path.join(os.path.expanduser("~"), "Documents", "My Games", "Rainbow Six - Siege")
        initial_dir = base_path if os.path.isdir(base_path) else os.path.expanduser("~")

        path = filedialog.askopenfilename(
            initialdir=initial_dir,
            title="Select GameSettings.ini",
            filetypes=[("INI files", "*.ini"), ("All files", "*.*")]
        )

        if path:
            self.ini_full_path = path
            self.ini_path_display.set(os.path.basename(os.path.dirname(path)))
            self.load_current_server(path)

    def load_current_server(self, path: str):
        config = configparser.ConfigParser(strict=False)
        config.optionxform = str

        try:
            config.read(path, encoding="utf-8")
        except Exception:
            config.read(path)

        if "ONLINE" in config and "DataCenterHint" in config["ONLINE"]:
            hint = config["ONLINE"]["DataCenterHint"].strip()
            for name, (code, _) in SERVERS.items():
                if hint == code:
                    self.select_server(name)
                    return

    def save_choice(self):
        if not self.ini_full_path or not os.path.isfile(self.ini_full_path):
            messagebox.showerror("R6 Server Select", "Invalid GameSettings.ini path")
            return

        if not self.selected_server:
            messagebox.showerror("R6 Server Select", "No server selected")
            return

        config = configparser.ConfigParser(strict=False)
        config.optionxform = str

        try:
            config.read(self.ini_full_path, encoding="utf-8")
        except Exception:
            config.read(self.ini_full_path)

        if "ONLINE" not in config:
            config["ONLINE"] = {}

        config["ONLINE"]["DataCenterHint"] = SERVERS[self.selected_server][0]

        try:
            with open(self.ini_full_path, "w", encoding="utf-8") as f:
                config.write(f)

            messagebox.showinfo("R6 Server Select", f"Server set to {self.selected_server}")
        except Exception as e:
            messagebox.showerror("R6 Server Select", f"Could not write GameSettings.ini:\n{e}")

    def select_server(self, name: str):
        for n, (_, name_label, ping_label) in self.rows.items():
            name_label.configure(text_color="white")
            ping_label.configure(text_color=get_latency_color(self.latencies.get(n, 9999)))

        self.rows[name][1].configure(text_color="#10B981")
        self.rows[name][2].configure(text_color="#10B981")
        self.selected_server = name

    def ping_loop(self, name: str, host: Optional[str]):
        while True:
            if host is None:
                self.latencies[name] = 9999
                self.after(0, self.update_ui, name, "—")
                time.sleep(2)
                continue

            samples = []
            lost = 0
            total = 10

            for _ in range(total):
                try:
                    delay = icmp_ping(host, timeout=1)
                    if delay is None:
                        lost += 1
                    else:
                        samples.append(delay * 1000)
                except Exception:
                    lost += 1
                time.sleep(0.15)

            if samples:
                avg = int(sum(samples) / len(samples))
                jitter = int(max(samples) - min(samples))
                loss = int((lost / total) * 100)
                self.latencies[name] = avg
                result_text = f"{avg} ms | Jitter {jitter} | Loss {loss}%"
            else:
                self.latencies[name] = 9999
                result_text = "timeout | Loss 100%"

            self.after(0, self.update_ui, name, result_text)
            time.sleep(2)

    def update_ui(self, name: str, latency_str: str):
        latency_ms = self.latencies[name]
        text_color = get_latency_color(latency_ms)

        if self.selected_server != name:
            self.rows[name][2].configure(text=latency_str, text_color=text_color)
        else:
            self.rows[name][2].configure(text=latency_str, text_color="#10B981")

        best_server = min(
            [n for n in self.latencies if n != AUTO_SERVER_NAME],
            key=lambda n: self.latencies[n],
            default=None
        )

        if best_server:
            self.rows[AUTO_SERVER_NAME][2].configure(
                text=f"Best: {best_server}",
                text_color=get_latency_color(self.latencies[best_server])
            )

        if self.auto_sort_var.get():
            new_order = [AUTO_SERVER_NAME] + sorted(
                [n for n in self.latencies if n != AUTO_SERVER_NAME],
                key=lambda n: self.latencies[n]
            )
        else:
            new_order = list(SERVERS.keys())

        if new_order != self.current_order:
            for n in new_order:
                row, _, _ = self.rows[n]
                row.pack_forget()
                row.pack(anchor="w", pady=2, padx=10, fill="x")
            self.current_order = new_order


if __name__ == "__main__":
    try:
        app = R6ServerSelect()
        app.mainloop()
    except Exception:
        traceback.print_exc()
        input("Press Enter to exit...")