import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading, configparser, os, re, time, traceback, webbrowser
from typing import Optional, Dict, Tuple, List, Any
from ping3 import ping as icmp_ping   # pure Python ping

# ---------- Constants ----------
AUTO_SERVER_NAME = "Auto (Default)"

# Server display name -> (DataCenterHint code, DynamoDB Host for ping)
SERVERS: Dict[str, Tuple[str, Optional[str]]] = {
    AUTO_SERVER_NAME: ("default", None),
    "Australia East": ("playfab/australiaeast", "dynamodb.ap-southeast-2.amazonaws.com"),
    "Brazil South": ("playfab/brazilsouth", "dynamodb.sa-east-1.amazonaws.com"),
    "Central US": ("playfab/centralus", "dynamodb.us-east-1.amazonaws.com"),
    "East Asia": ("playfab/eastasia", "dynamodb.ap-east-1.amazonaws.com"),
    "East US": ("playfab/eastus", "dynamodb.us-east-1.amazonaws.com"),
    "Japan East": ("playfab/japaneast", "dynamodb.ap-northeast-1.amazonaws.com"),
    "North Europe": ("playfab/northeurope", "dynamodb.eu-north-1.amazonaws.com"),
    "South Africa North": ("playfab/southafricanorth", "dynamodb.af-south-1.amazonaws.com"),
    "South Central US": ("playfab/southcentralus", "dynamodb.us-east-2.amazonaws.com"),
    "South East Asia": ("playfab/southeastasia", "dynamodb.ap-southeast-1.amazonaws.com"),
    "UAE North": ("playfab/uaenorth", "dynamodb.me-central-1.amazonaws.com"),
    "West Europe": ("playfab/westeurope", "dynamodb.eu-west-2.amazonaws.com"),
    "West US": ("playfab/westus", "dynamodb.us-west-1.amazonaws.com"),
}

# ---------- Helpers ----------

def ping(host: Optional[str]) -> str:
    """Ping using ping3 (no subprocess, no cmd popup)."""
    if host is None:
        return "—"
    try:
        delay = icmp_ping(host, timeout=1)  # returns seconds
        if delay is None:
            return "timeout"
        return f"{int(delay * 1000)} ms"
    except Exception:
        return "timeout"

def parse_latency(value: str) -> int:
    """Parses a ping string (e.g., '50 ms') into an integer (50) or 9999 for errors."""
    if value in ["—", "timeout", None]:
        return 9999
    m = re.search(r"(\d+)", value)
    return int(m.group(1)) if m else 9999

def get_latency_color(latency_ms: int) -> str:
    """Returns a color string based on latency for visual feedback."""
    if latency_ms <= 50:
        return "#4CAF50"  # Green
    elif latency_ms <= 100:
        return "#FFC107" # Yellow/Amber
    elif latency_ms < 9999:
        return "#F44336"  # Red
    else:
        return "gray"    # Timeout/Error

# ---------- GUI ----------
class R6ServerSelect(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("R6 Server Select")
        self.geometry("640x660")
        self.resizable(False, False)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.ini_full_path: Optional[str] = None
        self.ini_path_display = tk.StringVar(value="No file selected")
        self.selected_server: Optional[str] = None
        self.auto_sort_var = ctk.BooleanVar(value=True) # New setting for auto-sort

        # Data structure for GUI elements: {server_name: (frame, name_label, ping_label)}
        self.rows: Dict[str, Tuple[ctk.CTkFrame, ctk.CTkLabel, ctk.CTkLabel]] = {}
        # Data structure for ping results: {server_name: latency_ms}
        self.latencies: Dict[str, int] = {name: 9999 for name in SERVERS.keys()}
        self.current_order: List[str] = list(SERVERS.keys())

        self._create_widgets()
        self._start_ping_threads()

    def _create_widgets(self):
        """Sets up the main layout and widgets of the application."""
        # Title
        ctk.CTkLabel(self, text="R6 Server Select",
                     font=("Arial", 18, "bold")).pack(pady=10)

        # File picker frame
        file_frame = ctk.CTkFrame(self)
        file_frame.pack(pady=5, fill="x", padx=10)
        ctk.CTkLabel(file_frame, text="Current Profile:").pack(side="left", padx=(5, 0))
        ctk.CTkLabel(file_frame, textvariable=self.ini_path_display, text_color="#10B981").pack(side="left", padx=5)
        ctk.CTkButton(file_frame, text="Browse / Change File", command=self.browse_file).pack(side="right", padx=5)

        # Options frame (for Checkbox)
        options_frame = ctk.CTkFrame(self, fg_color="transparent")
        options_frame.pack(fill="x", padx=10)
        ctk.CTkCheckBox(
            options_frame,
            text="Auto-Sort by Latency",
            variable=self.auto_sort_var,
            checkbox_height=18,
            checkbox_width=18
        ).pack(side="left", padx=5, pady=(0, 5))


        # Ping table frame (Scrollable area for servers)
        self.ping_frame = ctk.CTkFrame(self)
        self.ping_frame.pack(pady=10, fill="both", expand=True, padx=10)
        
        # Header row (optional, but good for clarity)
        header_row = ctk.CTkFrame(self.ping_frame, fg_color="transparent")
        header_row.pack(anchor="w", pady=(5, 0), padx=10, fill="x")
        ctk.CTkLabel(header_row, text="SERVER REGION", width=280, anchor="w", text_color="gray").pack(side="left")
        ctk.CTkLabel(header_row, text="PING / AUTO-SELECT", width=120, anchor="w", text_color="gray").pack(side="left")

        # Create rows for each server
        for name in SERVERS.keys():
            row = ctk.CTkFrame(self.ping_frame)
            row.pack(anchor="w", pady=2, padx=10, fill="x")

            # Name label
            name_label = ctk.CTkLabel(row, text=name, width=280, anchor="w")
            name_label.pack(side="left")
            
            # Ping label (will be updated by ping_loop)
            ping_label = ctk.CTkLabel(row, text="…", width=120, anchor="w")
            ping_label.pack(side="left")

            # Make row clickable
            for widget in (row, name_label, ping_label):
                widget.bind("<Button-1>", lambda e, n=name: self.select_server(n))

            self.rows[name] = (row, name_label, ping_label)

        # Save button
        ctk.CTkButton(self, text="Save to INI", command=self.save_choice, height=35).pack(pady=10)

        # Bottom bar
        bottom_bar = ctk.CTkFrame(self, fg_color="transparent")
        bottom_bar.pack(side="bottom", fill="x", pady=5, padx=5)

        support_label = ctk.CTkLabel(
            bottom_bar,
            text="Made with ❤ by Recruit",
            text_color="#1E90FF", # DodgerBlue
            cursor="hand2",
            font=("Arial", 12, "underline"),
            anchor="e",
            justify="right"
        )
        support_label.pack(side="right")
        support_label.bind("<Button-1>", lambda e: webbrowser.open("https://www.youtube.com/@Im_Recruit"))

    def _start_ping_threads(self):
        """Initializes and starts a ping thread for each server."""
        for name, (_, host) in SERVERS.items():
            threading.Thread(target=self.ping_loop, args=(name, host), daemon=True).start()

    # ---------- File Handling ----------
    def browse_file(self):
        base_path = os.path.join(
            os.path.expanduser("~"),
            "Documents",
            "My Games",
            "Rainbow Six - Siege"
        )
        # Ensure base path exists for initialdir, if not, use home directory
        initial_dir = base_path if os.path.isdir(base_path) else os.path.expanduser("~")
        
        path = filedialog.askopenfilename(
            initialdir=initial_dir,
            title="Select GameSettings.ini",
            filetypes=[("INI files", "*.ini"), ("All files", "*.*")]
        )
        if path:
            self.ini_full_path = path
            # Extract profile ID (folder name above GameSettings.ini)
            profile_id = os.path.basename(os.path.dirname(path))
            self.ini_path_display.set(profile_id)
            self.load_current_server(path)

    def load_current_server(self, path: str):
        if not os.path.isfile(path):
            return
        config = configparser.ConfigParser(strict=False)
        config.optionxform = str
        try:
            config.read(path)
        except Exception:
            return
        
        if "ONLINE" in config and "DataCenterHint" in config["ONLINE"]:
            hint = config["ONLINE"]["DataCenterHint"].strip()
            for name, (code, _) in SERVERS.items():
                if hint == code:
                    self.select_server(name)
                    break

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
            config.read(self.ini_full_path)
        except Exception:
            messagebox.showerror("R6 Server Select", "Could not read GameSettings.ini")
            return

        # Ensure [ONLINE] section exists
        if "ONLINE" not in config:
            config["ONLINE"] = {}
            
        config["ONLINE"]["DataCenterHint"] = SERVERS[self.selected_server][0]
        
        try:
            # Use 'w' mode to ensure existing content is overwritten cleanly
            with open(self.ini_full_path, "w") as f:
                config.write(f)
            messagebox.showinfo("R6 Server Select", f"Server set to {self.selected_server}")
        except Exception as e:
            # Provide more detailed error message
            messagebox.showerror("R6 Server Select", f"Could not write GameSettings.ini: {e}")

    # ---------- Server Selection ----------
    def select_server(self, name: str):
        """Highlights the selected server row."""
        # Reset color of all rows
        for n, (_, name_label, ping_label) in self.rows.items():
            name_label.configure(text_color="white")
            # Also reset the ping column color to the calculated ping color (not always white)
            latency_ms = self.latencies.get(n, 9999)
            ping_label.configure(text_color=get_latency_color(latency_ms))
            
        # Highlight the selected row
        self.rows[name][1].configure(text_color="#10B981") # Green highlight
        self.rows[name][2].configure(text_color="#10B981") # Green highlight
        self.selected_server = name

    # ---------- Ping Threads ----------
    def ping_loop(self, name: str, host: Optional[str]):
        """Runs continuously in a separate thread to ping the server."""
        while True:
            latency_str = ping(host)
            self.latencies[name] = parse_latency(latency_str)
            # Use self.after to schedule UI update on the main thread
            self.after(0, self.update_ui, name, latency_str)
            time.sleep(2)

    def update_ui(self, name: str, latency_str: str):
        """Updates the UI elements based on new ping data."""
        # Determine the color based on latency value
        latency_ms = self.latencies[name]
        text_color = get_latency_color(latency_ms)

        # Update normal server row (if not currently selected, use calculated color)
        if self.selected_server != name:
            self.rows[name][2].configure(text=latency_str, text_color=text_color)
        else:
             # If selected, maintain the green selection highlight
             self.rows[name][2].configure(text=latency_str)


        # Update "Auto (Default)" row with best server details
        best_server = min(
            [n for n in self.latencies if n != AUTO_SERVER_NAME],
            key=lambda n: self.latencies[n],
            default=None
        )
        if best_server:
            # Update the latency column for 'Auto (Default)' with the best server's name
            self.rows[AUTO_SERVER_NAME][2].configure(
                text=f"{best_server}",
                text_color=get_latency_color(self.latencies[best_server])
            )
        
        # Reorder rows by latency (except Auto stays on top) if auto-sort is enabled
        if self.auto_sort_var.get():
            new_order = [AUTO_SERVER_NAME] + sorted(
                [n for n in self.latencies if n != AUTO_SERVER_NAME],
                key=lambda n: self.latencies[n]
            )
            
            if new_order != self.current_order:
                for n in new_order:
                    row, _, _ = self.rows[n]
                    # Repack the frame to move it to the new position
                    row.pack_forget()
                    row.pack(anchor="w", pady=2, padx=10, fill="x")
                self.current_order = new_order
        else:
            # If auto-sort is disabled, ensure the initial order is maintained
            # by packing the rows according to the original SERVERS keys list
            if self.current_order != list(SERVERS.keys()):
                for n in list(SERVERS.keys()):
                    row, _, _ = self.rows[n]
                    row.pack_forget()
                    row.pack(anchor="w", pady=2, padx=10, fill="x")
                self.current_order = list(SERVERS.keys())


# ---------- Entry ----------
if __name__ == "__main__":
    try:
        app = R6ServerSelect()
        app.mainloop()
    except Exception:
        traceback.print_exc()
        input("Press Enter to exit...")