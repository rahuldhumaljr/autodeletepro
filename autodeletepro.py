"""AutoDelete Pro: Windows desktop file/folder expiry timer.

WARNING: Expiry can permanently delete data when Recycle Bin mode is explicitly
disabled. Test with disposable files before relying on this application.
"""
import tkinter as tk
from tkinter import messagebox, filedialog
import os
import sys
import time
import winreg
import shutil
import ctypes
from ctypes import wintypes
from datetime import datetime

# --- WINDOWS TASKBAR ICON FIX ---
try:
    myappid = "autodeletepro.app.1.0"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass

CONFIG_FILE = os.path.expanduser("~\\.AutoDelete Pro_config.txt")
SETTINGS_FILE = os.path.expanduser("~\\.AutoDelete Pro_settings.txt")
HISTORY_FILE = os.path.expanduser("~\\.AutoDelete Pro_history.txt")
STATS_FILE = os.path.expanduser("~\\.AutoDelete Pro_stats.txt")
PENDING_FILE = os.path.expanduser("~\\.AutoDelete Pro_pending.txt")
LOCK_FILE = os.path.expanduser("~\\.AutoDelete Pro_lock.tmp")

THEMES = {
    "dark": {
        "bg_color": "#0f131a",
        "sidebar_bg": "#141923",
        "card_bg": "#1a212c",
        "card_border": "#263142",
        "accent_color": "#3b82f6",
        "accent_hover": "#2563eb",
        "danger_color": "#ef4444",
        "text_color": "#f8fafc",
        "subtext_color": "#94a3b8",
        "success_color": "#22c55e",
        "warning_color": "#eab308",
        "inner_bg": "#131822",
        "select_color": "#1a212c"
    },
    "light": {
        "bg_color": "#f1f5f9",
        "sidebar_bg": "#ffffff",
        "card_bg": "#ffffff",
        "card_border": "#e2e8f0",
        "accent_color": "#2563eb",
        "accent_hover": "#1d4ed8",
        "danger_color": "#dc2626",
        "text_color": "#0f172a",
        "subtext_color": "#64748b",
        "success_color": "#16a34a",
        "warning_color": "#ca8a04",
        "inner_bg": "#f8fafc",
        "select_color": "#e2e8f0"
    }
}

def resource_path(relative_path):
    """Get absolute path to resource, works for development and for PyInstaller bundle"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def set_window_icon(window):
    """Utility function to reliably load the icon onto any Tkinter window"""
    try:
        icon_p = resource_path("AutoDelete Pro.ico")
        if os.path.exists(icon_p):
            window.iconbitmap(icon_p)
        else:
            window.iconbitmap(sys.executable)
    except Exception:
        pass

def get_setting(key, default=True):
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    if "=" in line:
                        k, v = line.strip().split("=", 1)
                        if k == key:
                            return v == "1"
        except Exception:
            pass
    return default

def set_setting(key, val):
    settings = {}
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    if "=" in line:
                        k, v = line.strip().split("=", 1)
                        settings[k] = v
        except Exception:
            pass
    settings[key] = "1" if val else "0"
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            for k, v in settings.items():
                f.write(f"{k}={v}\n")
    except Exception:
        pass

def check_startup_setting():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, "AutoDelete Pro")
            return True
    except Exception:
        return False

def get_application_command():
    """Return a Windows command that starts this app in source or frozen mode."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    script_path = os.path.abspath(sys.argv[0])
    return f'"{sys.executable}" "{script_path}"'


def set_startup_setting(enable):
    """Enable/disable per-user startup without requiring administrator rights."""
    set_setting("startup", enable)
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            if enable:
                winreg.SetValueEx(key, "AutoDelete Pro", 0, winreg.REG_SZ, get_application_command())
            else:
                try:
                    winreg.DeleteValue(key, "AutoDelete Pro")
                except FileNotFoundError:
                    pass
    except OSError as exc:
        # Keep the app running even if Windows blocks the registry update.
        print(f"AutoDelete Pro: could not update startup setting: {exc}", file=sys.stderr)


def check_context_menu_setting():
    return get_setting("context_menu", True)

def set_context_menu_setting(enable):
    """Install/remove AutoDelete Pro's per-user Explorer context-menu entry."""
    set_setting("context_menu", enable)
    key_path = r"Software\Classes\AllFilesystemObjects\shell\AutoDelete Pro"
    cmd_path = key_path + r"\command"
    try:
        if enable:
            if getattr(sys, "frozen", False):
                app_path = os.path.abspath(sys.executable)
                command_str = f'"{app_path}" "%1"'
            else:
                script_path = os.path.abspath(sys.argv[0])
                command_str = f'"{sys.executable}" "{script_path}" "%1"'
                app_path = script_path

            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                winreg.SetValue(key, "", winreg.REG_SZ, "Set to AutoDelete Pro")
                winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, app_path)
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, cmd_path) as key:
                winreg.SetValue(key, "", winreg.REG_SZ, command_str)
        else:
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, cmd_path)
            except FileNotFoundError:
                pass
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path)
            except FileNotFoundError:
                pass
    except OSError as exc:
        print(f"AutoDelete Pro: could not update context menu: {exc}", file=sys.stderr)


def load_config_dict():
    tracked = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split("|")
                    if len(parts) >= 2:
                        path = parts[0]
                        exp = float(parts[1])
                        recycle_bin = True if len(parts) > 2 and parts[2] == "1" else get_setting("recycle_bin", True)
                        keep_folder = True if len(parts) > 3 and parts[3] == "1" else False
                        if os.path.exists(path):
                            tracked[path] = {"expiry": exp, "recycle_bin": recycle_bin, "keep_folder": keep_folder}
        except Exception:
            pass
    return tracked

def save_config_dict(tracked):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            for path, data in tracked.items():
                exp = data["expiry"] if isinstance(data, dict) else data
                rb = "1" if (isinstance(data, dict) and data.get("recycle_bin", True)) else "0"
                kf = "1" if (isinstance(data, dict) and data.get("keep_folder", False)) else "0"
                f.write(f"{path}|{exp}|{rb}|{kf}\n")
    except Exception:
        pass

def move_to_recycle_bin(path):
    """Safely move files or folders to Windows Recycle Bin using pure ctypes"""
    try:
        class SHFILEOPSTRUCTW(ctypes.Structure):
            _fields_ = [
                ("hwnd", wintypes.HWND),
                ("wFunc", wintypes.UINT),
                ("pFrom", wintypes.LPCWSTR),
                ("pTo", wintypes.LPCWSTR),
                ("fFlags", wintypes.WORD),
                ("fAnyOperationsAborted", wintypes.BOOL),
                ("hNameMappings", ctypes.c_void_p),
                ("lpszTitle", wintypes.LPCWSTR),
            ]
        FO_DELETE = 3
        FOF_ALLOWUNDO = 0x0040
        FOF_NOCONFIRMATION = 0x0010
        FOF_SILENT = 0x0004
        
        abs_path = os.path.abspath(path)
        path_double_null = abs_path + "\0\0"
        
        sh_file_op = SHFILEOPSTRUCTW()
        sh_file_op.hwnd = None
        sh_file_op.wFunc = FO_DELETE
        sh_file_op.pFrom = path_double_null
        sh_file_op.pTo = None
        sh_file_op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT
        
        res = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(sh_file_op))
        # SHFileOperation can return success while the user/system aborts the operation.
        return res == 0 and not bool(sh_file_op.fAnyOperationsAborted)
    except Exception:
        return False

def get_path_size(path):
    total_size = 0
    try:
        if os.path.isfile(path):
            total_size = os.path.getsize(path)
        elif os.path.isdir(path):
            for dirpath, dirnames, filenames in os.walk(path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    try:
                        if not os.path.islink(fp):
                            total_size += os.path.getsize(fp)
                    except Exception:
                        pass
    except Exception:
        pass
    return total_size

def get_folder_contents_size(path):
    total_size = 0
    try:
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            total_size += get_path_size(item_path)
    except Exception:
        pass
    return total_size

def clear_folder_contents(path, use_recycle):
    """Clear a folder's children. Recycle-bin failures never trigger permanent deletion."""
    try:
        for name in os.listdir(path):
            item_path = os.path.join(path, name)
            if use_recycle:
                if not move_to_recycle_bin(item_path):
                    return False
            elif os.path.isdir(item_path) and not os.path.islink(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)
        return True
    except OSError as exc:
        print(f"AutoDelete Pro: could not clear folder {path!r}: {exc}", file=sys.stderr)
        return False


def get_total_saved_bytes():
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                val = f.read().strip()
                return float(val) if val else 0.0
        except Exception:
            pass
    return 0.0

def add_saved_bytes(b):
    current = get_total_saved_bytes()
    new_val = current + b
    try:
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            f.write(str(new_val))
    except Exception:
        pass
    return new_val

def format_size(size_bytes):
    try:
        size_bytes = float(size_bytes)
    except Exception:
        return "0 B"
    
    if size_bytes < 1024:
        return f"{int(size_bytes)} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


class QuickExpiryDialog:
    """Lightweight popup supporting single or multiple files/folders triggered via Windows Context Menu"""
    def __init__(self, root, paths):
        self.root = root
        self.paths = paths

        self.root.title("AutoDelete Pro - Set Expiry Timer")
        self.root.geometry("380x320")
        self.root.resizable(False, False)
        self.root.configure(bg="#1a212c")
        self.root.attributes("-topmost", True)

        set_window_icon(self.root)

        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

        title_text = f"⏱️ Set Timer ({len(paths)} items selected)" if len(paths) > 1 else f"⏱️ Set Auto-Expiry Timer"
        tk.Label(self.root, text=title_text, font=("Mulish", 12, "bold"), bg="#1a212c", fg="#f8fafc").pack(pady=(16, 4))
        
        display_name = os.path.basename(paths[0]) if len(paths) == 1 else f"{os.path.basename(paths[0])} and {len(paths)-1} other(s)"
        tk.Label(self.root, text=display_name, font=("Mulish", 9), bg="#1a212c", fg="#94a3b8", wraplength=340).pack(pady=(0, 10))

        input_frame = tk.Frame(self.root, bg="#1a212c")
        input_frame.pack(pady=5)

        self.val_var = tk.StringVar(value="5")
        entry = tk.Entry(input_frame, textvariable=self.val_var, font=("Mulish", 12), justify="center", width=6, bg="#131822", fg="#f8fafc", insertbackground="white", relief="flat")
        entry.pack(side=tk.LEFT, padx=5)
        entry.focus()
        entry.select_range(0, tk.END)

        self.unit_var = tk.StringVar(value="Minutes")
        unit_menu = tk.OptionMenu(input_frame, self.unit_var, "Seconds", "Minutes", "Hours", "Days")
        unit_menu.config(font=("Mulish", 10), bg="#131822", fg="#f8fafc", activebackground="#334155", activeforeground="white", highlightthickness=0, relief="flat")
        unit_menu["menu"].config(bg="#131822", fg="#f8fafc", activebackground="#3b82f6")
        unit_menu.pack(side=tk.LEFT, padx=5)

        self.recycle_var = tk.BooleanVar(value=get_setting("recycle_bin", True))
        chk_recycle = tk.Checkbutton(self.root, text="Move to Windows Recycle Bin on expiry", variable=self.recycle_var, font=("Mulish", 9), bg="#1a212c", fg="#f8fafc", selectcolor="#131822", activebackground="#1a212c", activeforeground="#f8fafc", cursor="hand2")
        chk_recycle.pack(pady=(10, 0))

        self.keep_folder_var = tk.BooleanVar(value=False)
        chk_keep_folder = tk.Checkbutton(self.root, text="Delete folder contents only (keep folder)", variable=self.keep_folder_var, font=("Mulish", 9), bg="#1a212c", fg="#f8fafc", selectcolor="#131822", activebackground="#1a212c", activeforeground="#f8fafc", cursor="hand2")
        chk_keep_folder.pack(pady=(6, 0))

        save_btn = tk.Button(self.root, text="Start Countdown Timer", font=("Mulish", 10, "bold"), bg="#3b82f6", fg="white", activebackground="#2563eb", activeforeground="white", bd=0, padx=16, pady=8, cursor="hand2", command=self.confirm)
        save_btn.pack(pady=12)

    def confirm(self):
        try:
            val = float(self.val_var.get())
            if val <= 0:
                raise ValueError
            
            unit = self.unit_var.get()
            if unit == "Seconds":
                seconds = val
            elif unit == "Minutes":
                seconds = val * 60
            elif unit == "Hours":
                seconds = val * 3600
            else:
                seconds = val * 86400

            expiry_time = time.time() + seconds
            use_recycle = self.recycle_var.get()
            keep_folder = self.keep_folder_var.get()
            tracked = load_config_dict()
            for p in self.paths:
                tracked[p] = {"expiry": expiry_time, "recycle_bin": use_recycle, "keep_folder": keep_folder}
            save_config_dict(tracked)
            
            self.root.destroy()
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid positive number.", parent=self.root)


class AutoDeleteProApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AutoDelete Pro")
        self.root.geometry("1024x680")
        self.root.minsize(850, 580)

        set_window_icon(self.root)

        self.is_dark = get_setting("theme_dark", True)
        self.colors = THEMES["dark"] if self.is_dark else THEMES["light"]

        self.apply_theme_colors()

        self.tracked_files = {}       
        self.history_logs = []        
        self.file_vars = {}           
        self.active_row_widgets = {}  
        
        self.load_config()
        self.load_history()

        # Enforce context menu setting on startup (removes if disabled)
        set_context_menu_setting(get_setting("context_menu", True))

        # --- MAIN LAYOUT ---
        self.sidebar = tk.Frame(root, bg=self.colors["sidebar_bg"], width=220)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        logo_frame = tk.Frame(self.sidebar, bg=self.colors["sidebar_bg"])
        logo_frame.pack(fill=tk.X, padx=16, pady=20)
        self.logo_lbl = tk.Label(logo_frame, text="⏳ AutoDelete Pro", font=("Mulish", 13, "bold"), bg=self.colors["sidebar_bg"], fg=self.colors["text_color"])
        self.logo_lbl.pack(anchor="w")

        self.nav_title_lbl = tk.Label(logo_frame, text="NAVIGATION", font=("Mulish", 8, "bold"), bg=self.colors["sidebar_bg"], fg=self.colors["subtext_color"])
        self.nav_title_lbl.pack(anchor="w", pady=(16, 6))

        self.nav_dashboard_btn = tk.Button(self.sidebar, text="  📁 Active Items", font=("Mulish", 10, "bold"), bg=self.colors["accent_color"], fg="white", anchor="w", bd=0, padx=12, pady=10, cursor="hand2", command=lambda: self.switch_tab("active"))
        self.nav_dashboard_btn.pack(fill=tk.X, padx=10, pady=2)

        self.nav_history_btn = tk.Button(self.sidebar, text="  📜 Deletion History", font=("Mulish", 10), bg=self.colors["sidebar_bg"], fg=self.colors["subtext_color"], anchor="w", bd=0, padx=12, pady=10, cursor="hand2", command=lambda: self.switch_tab("history"))
        self.nav_history_btn.pack(fill=tk.X, padx=10, pady=2)

        self.nav_settings_btn = tk.Button(self.sidebar, text="  ⚙️ Service Settings", font=("Mulish", 10), bg=self.colors["sidebar_bg"], fg=self.colors["subtext_color"], anchor="w", bd=0, padx=12, pady=10, cursor="hand2", command=lambda: self.switch_tab("settings"))
        self.nav_settings_btn.pack(fill=tk.X, padx=10, pady=2)

        sidebar_bottom = tk.Frame(self.sidebar, bg=self.colors["sidebar_bg"])
        sidebar_bottom.pack(side=tk.BOTTOM, fill=tk.X, padx=12, pady=16)

        self.btn_add_files = tk.Button(sidebar_bottom, text="+ Add Files (Multi)", font=("Mulish", 10, "bold"), bg=self.colors["accent_color"], fg="white", activebackground=self.colors["accent_hover"], activeforeground="white", bd=0, pady=8, cursor="hand2", command=self.add_files_dialog)
        self.btn_add_files.pack(fill=tk.X, pady=(0, 4))

        self.btn_add_folder = tk.Button(sidebar_bottom, text="+ Add Folder", font=("Mulish", 10, "bold"), bg=self.colors["inner_bg"], fg=self.colors["text_color"], activebackground=self.colors["select_color"], activeforeground=self.colors["text_color"], bd=0, pady=8, cursor="hand2", command=self.add_folder_dialog)
        self.btn_add_folder.pack(fill=tk.X, pady=(0, 6))

        # 2. Main Container Area
        self.main_container = tk.Frame(root, bg=self.colors["bg_color"])
        self.main_container.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        top_header = tk.Frame(self.main_container, bg=self.colors["bg_color"], height=60)
        top_header.pack(fill=tk.X, padx=24, pady=(16, 10))
        top_header.pack_propagate(False)

        status_pill = tk.Frame(top_header, bg=self.colors["inner_bg"], highlightbackground=self.colors["card_border"], highlightthickness=1)
        status_pill.pack(side=tk.LEFT, pady=10)
        tk.Label(status_pill, text=" ● System background monitoring active ", font=("Mulish", 9), bg=self.colors["inner_bg"], fg=self.colors["success_color"]).pack(padx=10, pady=4)

        pro_badge = tk.Label(top_header, text=" OPEN SOURCE PROJECT ", font=("Mulish", 8, "bold"), bg=self.colors["accent_color"], fg="white", padx=8, pady=4)
        pro_badge.pack(side=tk.RIGHT, pady=12)

        metrics_frame = tk.Frame(self.main_container, bg=self.colors["bg_color"])
        metrics_frame.pack(fill=tk.X, padx=24, pady=(0, 16))

        self.card_tracked = self.create_metric_card(metrics_frame, "ACTIVE ITEMS", "0", "Monitored files & folders")
        self.card_tracked.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=(0, 6))

        self.card_deleted = self.create_metric_card(metrics_frame, "ITEMS REMOVED", "0", "Auto-cleaned items")
        self.card_deleted.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=6)

        self.card_space = self.create_metric_card(metrics_frame, "SPACE SAVED", "0 B", "Total cleaned storage")
        self.card_space.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=6)

        self.card_status = self.create_metric_card(metrics_frame, "DAEMON STATUS", "Running", "1s tick interval")
        self.card_status.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=(6, 0))

        self.content_card = tk.Frame(self.main_container, bg=self.colors["card_bg"], highlightbackground=self.colors["card_border"], highlightthickness=1)
        self.content_card.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 16))

        # --- Active Items View Frame ---
        self.active_frame = tk.Frame(self.content_card, bg=self.colors["card_bg"])

        active_header_row = tk.Frame(self.active_frame, bg=self.colors["card_bg"])
        active_header_row.pack(fill=tk.X, pady=(0, 10))
        self.active_title_lbl = tk.Label(active_header_row, text="Monitored Files & Folders Countdowns", font=("Mulish", 12, "bold"), bg=self.colors["card_bg"], fg=self.colors["text_color"])
        self.active_title_lbl.pack(side=tk.LEFT)
        
        self.btn_remove = tk.Button(active_header_row, text="🗑️ Remove Selected", font=("Mulish", 9, "bold"), bg=self.colors["danger_color"], fg="white", activebackground="#dc2626", activeforeground="white", bd=0, padx=12, pady=6, cursor="hand2", command=self.remove_checked_files)
        self.btn_remove.pack(side=tk.RIGHT)

        active_list_container = tk.Frame(self.active_frame, bg=self.colors["card_bg"])
        active_list_container.pack(fill=tk.BOTH, expand=True)

        self.canvas_active = tk.Canvas(active_list_container, bg=self.colors["card_bg"], highlightthickness=0)
        self.scrollbar_active = tk.Scrollbar(active_list_container, orient="vertical", command=self.canvas_active.yview)
        
        self.scrollable_active_inner = tk.Frame(self.canvas_active, bg=self.colors["card_bg"])
        self.scrollable_active_inner.bind(
            "<Configure>",
            lambda e: self.canvas_active.configure(scrollregion=self.canvas_active.bbox("all"))
        )

        self.canvas_active.create_window((0, 0), window=self.scrollable_active_inner, anchor="nw")
        self.canvas_active.configure(yscrollcommand=self.scrollbar_active.set)

        self.canvas_active.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar_active.pack(side=tk.RIGHT, fill=tk.Y)

        # --- Deleted History View Frame ---
        self.history_frame = tk.Frame(self.content_card, bg=self.colors["card_bg"])

        history_header_row = tk.Frame(self.history_frame, bg=self.colors["card_bg"])
        history_header_row.pack(fill=tk.X, pady=(0, 10))
        self.history_title_lbl = tk.Label(history_header_row, text="Cleanup Operation Logs", font=("Mulish", 12, "bold"), bg=self.colors["card_bg"], fg=self.colors["text_color"])
        self.history_title_lbl.pack(side=tk.LEFT)

        self.btn_clear_hist = tk.Button(history_header_row, text="Clear History Log", font=("Mulish", 9), bg=self.colors["inner_bg"], fg=self.colors["subtext_color"], activebackground=self.colors["select_color"], activeforeground=self.colors["text_color"], bd=0, padx=10, pady=5, cursor="hand2", command=self.clear_history)
        self.btn_clear_hist.pack(side=tk.RIGHT)

        hist_container = tk.Frame(self.history_frame, bg=self.colors["card_bg"])
        hist_container.pack(fill=tk.BOTH, expand=True)

        self.scrollbar_history = tk.Scrollbar(hist_container)
        self.scrollbar_history.pack(side=tk.RIGHT, fill=tk.Y)

        self.history_listbox = tk.Listbox(
            hist_container, 
            font=("Mulish", 9), 
            bg=self.colors["inner_bg"], 
            fg=self.colors["subtext_color"],
            selectbackground=self.colors["select_color"],
            selectforeground=self.colors["text_color"],
            yscrollcommand=self.scrollbar_history.set,
            bd=0, highlightthickness=0
        )
        self.history_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar_history.config(command=self.history_listbox.yview)

        # --- Service Settings View Frame ---
        self.settings_frame = tk.Frame(self.content_card, bg=self.colors["card_bg"])
        
        self.settings_title_lbl = tk.Label(self.settings_frame, text="Global Application & System Settings", font=("Mulish", 12, "bold"), bg=self.colors["card_bg"], fg=self.colors["text_color"])
        self.settings_title_lbl.pack(anchor="w", pady=(0, 12))

        settings_canvas = tk.Canvas(self.settings_frame, bg=self.colors["card_bg"], highlightthickness=0)
        settings_scrollbar = tk.Scrollbar(self.settings_frame, orient="vertical", command=settings_canvas.yview)
        self.settings_inner_frame = tk.Frame(settings_canvas, bg=self.colors["card_bg"])
        self.settings_inner_frame.bind("<Configure>", lambda e: settings_canvas.configure(scrollregion=settings_canvas.bbox("all")))
        settings_canvas.create_window((0, 0), window=self.settings_inner_frame, anchor="nw")
        settings_canvas.configure(yscrollcommand=settings_scrollbar.set)

        settings_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        settings_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.build_settings_cards()

        self.current_tab = "active"
        self.active_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

        footer_frame = tk.Frame(self.main_container, bg=self.colors["bg_color"])
        footer_frame.pack(fill=tk.X, padx=24, pady=(0, 12))
        self.footer_lbl = tk.Label(footer_frame, text="AutoDelete Pro — Automatic File & Folder Expiry Timer", font=("Mulish", 8), bg=self.colors["bg_color"], fg=self.colors["subtext_color"])
        self.footer_lbl.pack(side=tk.LEFT)

        self.running = True
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.refresh_views()
        self.root.after(1000, self.background_worker)

    def apply_theme_colors(self):
        try:
            self.root.configure(bg=self.colors["bg_color"])
        except Exception:
            pass

    def build_settings_cards(self):
        for widget in self.settings_inner_frame.winfo_children():
            widget.destroy()

        # 1. Theme Selector Radio Card
        self.build_settings_radio_card(
            self.settings_inner_frame,
            title="Application Theme",
            desc="Switch between Dark Mode and Light Mode aesthetic.",
            setting_key="theme_dark",
            get_fn=lambda: self.is_dark,
            set_fn=self.toggle_theme_mode,
            label_true="Dark Theme",
            label_false="Light Theme"
        )

        # 2. Context Menu Integration
        self.build_settings_radio_card(
            self.settings_inner_frame,
            title="Windows Context Menu Integration",
            desc="Integrate 'Auto Delete With AutoDelete Pro' directly into the Windows right-click menu.",
            setting_key="context_menu",
            get_fn=check_context_menu_setting,
            set_fn=set_context_menu_setting
        )

        # 3. Start with Windows
        self.build_settings_radio_card(
            self.settings_inner_frame,
            title="Start with Windows",
            desc="Automatically launch AutoDelete Pro in the background when you log into Windows.",
            setting_key="startup",
            get_fn=check_startup_setting,
            set_fn=set_startup_setting
        )

        # 4. Default Deletion Target
        self.build_settings_radio_card(
            self.settings_inner_frame,
            title="Default Deletion Target",
            desc="Choose whether expired items are sent to the Windows Recycle Bin or wiped permanently.",
            setting_key="recycle_bin",
            get_fn=lambda: get_setting("recycle_bin", True),
            set_fn=lambda val: set_setting("recycle_bin", val),
            label_true="Recycle Bin (Safer)",
            label_false="Permanent Delete"
        )

    def toggle_theme_mode(self, val):
        self.is_dark = val
        set_setting("theme_dark", val)
        self.colors = THEMES["dark"] if val else THEMES["light"]
        
        self.root.configure(bg=self.colors["bg_color"])
        self.sidebar.configure(bg=self.colors["sidebar_bg"])
        self.logo_lbl.configure(bg=self.colors["sidebar_bg"], fg=self.colors["text_color"])
        self.nav_title_lbl.configure(bg=self.colors["sidebar_bg"], fg=self.colors["subtext_color"])
        self.main_container.configure(bg=self.colors["bg_color"])
        self.content_card.configure(bg=self.colors["card_bg"], highlightbackground=self.colors["card_border"])
        self.active_frame.configure(bg=self.colors["card_bg"])
        self.history_frame.configure(bg=self.colors["card_bg"])
        self.settings_frame.configure(bg=self.colors["card_bg"])
        self.settings_inner_frame.configure(bg=self.colors["card_bg"])
        self.active_title_lbl.configure(bg=self.colors["card_bg"], fg=self.colors["text_color"])
        self.history_title_lbl.configure(bg=self.colors["card_bg"], fg=self.colors["text_color"])
        self.settings_title_lbl.configure(bg=self.colors["card_bg"], fg=self.colors["text_color"])
        self.footer_lbl.configure(bg=self.colors["bg_color"], fg=self.colors["subtext_color"])
        
        self.switch_tab(self.current_tab)
        self.build_settings_cards()
        self.refresh_views()

    def build_settings_radio_card(self, parent, title, desc, setting_key, get_fn, set_fn, label_true="Enabled", label_false="Disabled"):
        card = tk.Frame(parent, bg=self.colors["inner_bg"], highlightbackground=self.colors["card_border"], highlightthickness=1)
        card.pack(fill=tk.X, pady=6, padx=4)

        inner = tk.Frame(card, bg=self.colors["inner_bg"])
        inner.pack(fill=tk.BOTH, expand=True, padx=16, pady=14)

        tk.Label(inner, text=title, font=("Mulish", 11, "bold"), bg=self.colors["inner_bg"], fg=self.colors["text_color"]).pack(anchor="w")
        tk.Label(inner, text=desc, font=("Mulish", 9), bg=self.colors["inner_bg"], fg=self.colors["subtext_color"], wraplength=650, justify="left").pack(anchor="w", pady=(2, 10))

        current_val = get_fn()
        var = tk.BooleanVar(value=current_val)

        def on_change():
            val = var.get()
            set_fn(val)

        radio_row = tk.Frame(inner, bg=self.colors["inner_bg"])
        radio_row.pack(anchor="w")

        rb1 = tk.Radiobutton(
            radio_row, text=label_true, variable=var, value=True,
            font=("Mulish", 11, "bold"), bg=self.colors["inner_bg"], fg=self.colors["success_color"],
            selectcolor=self.colors["card_bg"], activebackground=self.colors["inner_bg"], activeforeground=self.colors["success_color"],
            cursor="hand2", command=on_change
        )
        rb1.pack(side=tk.LEFT, padx=(0, 24))

        rb2 = tk.Radiobutton(
            radio_row, text=label_false, variable=var, value=False,
            font=("Mulish", 11, "bold"), bg=self.colors["inner_bg"], fg=self.colors["danger_color"],
            selectcolor=self.colors["card_bg"], activebackground=self.colors["inner_bg"], activeforeground=self.colors["danger_color"],
            cursor="hand2", command=on_change
        )
        rb2.pack(side=tk.LEFT)

    def create_metric_card(self, parent, title, value_str, subtitle):
        card = tk.Frame(parent, bg=self.colors["card_bg"], highlightbackground=self.colors["card_border"], highlightthickness=1)
        inner = tk.Frame(card, bg=self.colors["card_bg"])
        inner.pack(fill=tk.BOTH, expand=True, padx=16, pady=14)

        tk.Label(inner, text=title, font=("Mulish", 8, "bold"), bg=self.colors["card_bg"], fg=self.colors["subtext_color"]).pack(anchor="w")
        
        val_lbl = tk.Label(inner, text=value_str, font=("Mulish", 20, "bold"), bg=self.colors["card_bg"], fg=self.colors["text_color"])
        val_lbl.pack(anchor="w", pady=(4, 2))
        card.value_label = val_lbl

        tk.Label(inner, text=subtitle, font=("Mulish", 8), bg=self.colors["card_bg"], fg=self.colors["subtext_color"]).pack(anchor="w")
        return card

    def switch_tab(self, tab_name):
        self.current_tab = tab_name
        
        self.nav_dashboard_btn.config(bg=self.colors["sidebar_bg"], fg=self.colors["subtext_color"], font=("Mulish", 10))
        self.nav_history_btn.config(bg=self.colors["sidebar_bg"], fg=self.colors["subtext_color"], font=("Mulish", 10))
        self.nav_settings_btn.config(bg=self.colors["sidebar_bg"], fg=self.colors["subtext_color"], font=("Mulish", 10))

        self.active_frame.pack_forget()
        self.history_frame.pack_forget()
        self.settings_frame.pack_forget()

        if tab_name == "active":
            self.nav_dashboard_btn.config(bg=self.colors["accent_color"], fg="white", font=("Mulish", 10, "bold"))
            self.active_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)
        elif tab_name == "history":
            self.nav_history_btn.config(bg=self.colors["accent_color"], fg="white", font=("Mulish", 10, "bold"))
            self.history_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)
            self.refresh_history_listbox()
        elif tab_name == "settings":
            self.nav_settings_btn.config(bg=self.colors["accent_color"], fg="white", font=("Mulish", 10, "bold"))
            self.settings_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

    def add_files_dialog(self):
        filepaths = filedialog.askopenfilenames(title="Select files to set expiry")
        if not filepaths:
            return
        self.prompt_multi_expiry(filepaths, item_type="Files")

    def add_folder_dialog(self):
        dirpath = filedialog.askdirectory(title="Select folder to set expiry")
        if not dirpath:
            return
        self.prompt_multi_expiry([dirpath], item_type="Folder")

    def prompt_multi_expiry(self, paths, item_type="Files"):
        dialog = tk.Toplevel(self.root)
        dialog.title("AutoDelete Pro - Set Expiry Timer")
        dialog.geometry("380x320")
        dialog.resizable(False, False)
        dialog.configure(bg=self.colors["card_bg"])
        dialog.grab_set()

        set_window_icon(dialog)

        count_str = f"{len(paths)} {item_type} selected" if len(paths) > 1 else os.path.basename(paths[0])
        tk.Label(dialog, text="Auto-delete timer for:", font=("Mulish", 11, "bold"), bg=self.colors["card_bg"], fg=self.colors["text_color"]).pack(pady=(16, 6))
        tk.Label(dialog, text=count_str, font=("Mulish", 9), bg=self.colors["card_bg"], fg=self.colors["subtext_color"], wraplength=340).pack(pady=(0, 10))
        
        input_frame = tk.Frame(dialog, bg=self.colors["card_bg"])
        input_frame.pack(pady=5)

        val_var = tk.StringVar(value="5")
        entry = tk.Entry(input_frame, textvariable=val_var, font=("Mulish", 12), justify="center", width=6, bg=self.colors["inner_bg"], fg=self.colors["text_color"], insertbackground=self.colors["text_color"], relief="flat")
        entry.pack(side=tk.LEFT, padx=5)
        entry.focus()
        entry.select_range(0, tk.END)

        unit_var = tk.StringVar(value="Minutes")
        unit_menu = tk.OptionMenu(input_frame, unit_var, "Seconds", "Minutes", "Hours", "Days")
        unit_menu.config(font=("Mulish", 10), bg=self.colors["inner_bg"], fg=self.colors["text_color"], activebackground=self.colors["select_color"], activeforeground=self.colors["text_color"], highlightthickness=0, relief="flat")
        unit_menu["menu"].config(bg=self.colors["inner_bg"], fg=self.colors["text_color"], activebackground=self.colors["accent_color"])
        unit_menu.pack(side=tk.LEFT, padx=5)

        recycle_var = tk.BooleanVar(value=get_setting("recycle_bin", True))
        chk_recycle = tk.Checkbutton(dialog, text="Move to Windows Recycle Bin on expiry", variable=recycle_var, font=("Mulish", 9), bg=self.colors["card_bg"], fg=self.colors["text_color"], selectcolor=self.colors["inner_bg"], activebackground=self.colors["card_bg"], activeforeground=self.colors["text_color"], cursor="hand2")
        chk_recycle.pack(pady=(10, 0))

        keep_folder_var = tk.BooleanVar(value=False)
        chk_keep_folder = tk.Checkbutton(dialog, text="Delete folder contents only (keep folder)", variable=keep_folder_var, font=("Mulish", 9), bg=self.colors["card_bg"], fg=self.colors["text_color"], selectcolor=self.colors["inner_bg"], activebackground=self.colors["card_bg"], activeforeground=self.colors["text_color"], cursor="hand2")
        chk_keep_folder.pack(pady=(6, 0))

        def confirm():
            try:
                val = float(val_var.get())
                if val <= 0:
                    raise ValueError
                
                unit = unit_var.get()
                if unit == "Seconds":
                    seconds = val
                elif unit == "Minutes":
                    seconds = val * 60
                elif unit == "Hours":
                    seconds = val * 3600
                else:
                    seconds = val * 86400

                expiry_time = time.time() + seconds
                use_recycle = recycle_var.get()
                keep_folder = keep_folder_var.get()
                for p in paths:
                    self.tracked_files[p] = {"expiry": expiry_time, "recycle_bin": use_recycle, "keep_folder": keep_folder}

                self.save_config()
                self.refresh_views()
                dialog.destroy()
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter a valid positive number.", parent=dialog)

        save_btn = tk.Button(dialog, text="Start Countdown Timer", font=("Mulish", 10, "bold"), bg=self.colors["accent_color"], fg="white", activebackground=self.colors["accent_hover"], activeforeground="white", bd=0, padx=16, pady=8, cursor="hand2", command=confirm)
        save_btn.pack(pady=12)

    def remove_checked_files(self):
        paths_to_remove = [path for path, var in self.file_vars.items() if var.get()]
        if not paths_to_remove:
            messagebox.showwarning("Selection Required", "Please check at least one item to remove from tracking.")
            return

        for path in paths_to_remove:
            if path in self.tracked_files:
                del self.tracked_files[path]
            if path in self.file_vars:
                del self.file_vars[path]
            if path in self.active_row_widgets:
                del self.active_row_widgets[path]

        self.save_config()
        self.refresh_views()

    def clear_history(self):
        self.history_logs.clear()
        self.save_history()
        try:
            if os.path.exists(STATS_FILE):
                os.remove(STATS_FILE)
        except Exception:
            pass
        self.refresh_history_listbox()
        self.update_metrics()

    def refresh_views(self):
        if self.current_tab == "active":
            now = time.time()
            valid_tracked = {p: data for p, data in self.tracked_files.items() if os.path.exists(p)}

            current_paths = set(self.active_row_widgets.keys())
            target_paths = set(valid_tracked.keys())

            if current_paths != target_paths:
                for widget in self.scrollable_active_inner.winfo_children():
                    widget.destroy()
                self.active_row_widgets.clear()
                self.file_vars.clear()

                for path, data in valid_tracked.items():
                    self.file_vars[path] = tk.BooleanVar(value=False)

                    is_dir = os.path.isdir(path)
                    item_prefix = "📁 " if is_dir else "📄 "

                    row_frame = tk.Frame(self.scrollable_active_inner, bg=self.colors["inner_bg"], highlightbackground=self.colors["card_border"], highlightthickness=1)
                    row_frame.pack(fill=tk.X, padx=4, pady=4)

                    chk = tk.Checkbutton(row_frame, variable=self.file_vars[path], bg=self.colors["inner_bg"], activebackground=self.colors["inner_bg"], selectcolor=self.colors["card_bg"], cursor="hand2")
                    chk.pack(side=tk.LEFT, padx=(10, 6), pady=10)

                    info_frame = tk.Frame(row_frame, bg=self.colors["inner_bg"])
                    info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=8)

                    tk.Label(info_frame, text=item_prefix + path, font=("Mulish", 10, "bold"), bg=self.colors["inner_bg"], fg=self.colors["text_color"], anchor="w").pack(fill=tk.X)
                    
                    sub_row = tk.Frame(info_frame, bg=self.colors["inner_bg"])
                    sub_row.pack(fill=tk.X, pady=(2, 0))

                    status_lbl = tk.Label(sub_row, text="", font=("Mulish", 8, "bold"), bg=self.colors["inner_bg"])
                    status_lbl.pack(side=tk.LEFT)
                    
                    time_lbl = tk.Label(sub_row, text="", font=("Mulish", 8), bg=self.colors["inner_bg"], fg=self.colors["subtext_color"])
                    time_lbl.pack(side=tk.LEFT)

                    self.active_row_widgets[path] = {
                        "status_lbl": status_lbl,
                        "time_lbl": time_lbl
                    }

            # Smooth in-place updates
            for path, widgets in self.active_row_widgets.items():
                if path not in valid_tracked:
                    continue
                data = valid_tracked[path]
                exp = data["expiry"] if isinstance(data, dict) else data
                remaining = exp - now

                if remaining <= 0:
                    time_str = "EXPIRED (Cleaning up...)"
                    status_badge = "🔴 Expired"
                    status_color = self.colors["danger_color"]
                elif remaining <= 60:
                    secs = int(remaining % 60)
                    time_str = f"{secs} seconds left"
                    status_badge = "🟡 Expiring Soon"
                    status_color = self.colors["warning_color"]
                else:
                    days = int(remaining // 86400)
                    hours = int((remaining % 86400) // 3600)
                    mins = int((remaining % 3600) // 60)
                    secs = int(remaining % 60)
                    
                    if days > 0:
                        time_str = f"{days}d {hours}h {mins}m {secs}s left"
                    elif hours > 0:
                        time_str = f"{hours}h {mins}m {secs}s left"
                    else:
                        time_str = f"{mins}m {secs}s left"
                    status_badge = "🟢 Active"
                    status_color = self.colors["success_color"]

                widgets["status_lbl"].config(text=status_badge, fg=status_color)
                widgets["time_lbl"].config(text=f"  |  Expires in: {time_str}")

        self.update_metrics()

    def update_metrics(self):
        self.card_tracked.value_label.config(text=str(len(self.tracked_files)))
        self.card_deleted.value_label.config(text=str(len(self.history_logs)))
        saved_bytes = get_total_saved_bytes()
        self.card_space.value_label.config(text=format_size(saved_bytes))

    def refresh_history_listbox(self):
        self.history_listbox.delete(0, tk.END)
        for log in reversed(self.history_logs):
            self.history_listbox.insert(tk.END, log)

    def background_worker(self):
        """Check expiry on Tk's main thread to avoid races with GUI state and file writes."""
        if not self.running:
            return

        now = time.time()
        # Merge items added from Explorer's context menu since the app was opened.
        disk_tracked = load_config_dict()
        for path, data in disk_tracked.items():
            if path not in self.tracked_files:
                self.tracked_files[path] = data
        for path in list(self.tracked_files):
            if path not in disk_tracked and os.path.exists(path):
                # A user may have removed tracking in another app instance.
                del self.tracked_files[path]

        expired_items = [
            (path, data.copy() if isinstance(data, dict) else {"expiry": data})
            for path, data in list(self.tracked_files.items())
            if now >= (data["expiry"] if isinstance(data, dict) else data)
        ]

        changed = False
        for path, data in expired_items:
            timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            use_recycle = data.get("recycle_bin", get_setting("recycle_bin", True))
            keep_folder = data.get("keep_folder", False)
            item_size = 0
            success = False
            action_str = ""

            try:
                if not os.path.exists(path):
                    success = True
                    action_str = "No action needed (item no longer exists)"
                elif os.path.isdir(path) and keep_folder:
                    item_size = get_folder_contents_size(path)
                    success = clear_folder_contents(path, use_recycle)
                    action_str = "Cleared folder contents (kept folder)"
                elif use_recycle:
                    item_size = get_path_size(path)
                    success = move_to_recycle_bin(path)
                    if success:
                        action_str = "Moved to Recycle Bin"
                else:
                    item_size = get_path_size(path)
                    if os.path.isdir(path) and not os.path.islink(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
                    success = True
                    action_str = "Permanently deleted (Recycle Bin disabled)"
            except OSError as exc:
                print(f"AutoDelete Pro: expiry operation failed for {path!r}: {exc}", file=sys.stderr)

            if success:
                if item_size:
                    add_saved_bytes(item_size)
                log_msg = f"[{timestamp_str}] Successfully {action_str}: {path}"
                self.tracked_files.pop(path, None)
                changed = True
            else:
                # Keep the item tracked and retry later. Never fall back to permanent deletion.
                if path in self.tracked_files:
                    self.tracked_files[path]["expiry"] = time.time() + 60
                log_msg = (
                    f"[{timestamp_str}] FAILED safely: could not move/remove {path}. "
                    "The item was not permanently deleted as a fallback; retrying in 60 seconds."
                )
                changed = True

            self.history_logs.append(log_msg)

        if changed:
            self.save_config()
            self.save_history()

        self.refresh_views()
        self.root.after(1000, self.background_worker)

    def on_close(self):
        """Stop scheduling checks and close the application cleanly."""
        self.running = False
        try:
            self.save_config()
            self.save_history()
        finally:
            self.root.destroy()

    def save_config(self):
        save_config_dict(self.tracked_files)

    def load_config(self):
        self.tracked_files = load_config_dict()

    def save_history(self):
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                for log in self.history_logs:
                    f.write(f"{log}\n")
        except Exception:
            pass

    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        clean_line = line.strip()
                        if clean_line:
                            self.history_logs.append(clean_line)
            except Exception:
                pass

if __name__ == "__main__":
    if len(sys.argv) > 1:
        incoming = [arg.strip('"') for arg in sys.argv[1:] if os.path.exists(arg.strip('"'))]
        script_abs = os.path.normcase(os.path.abspath(sys.argv[0]))
        valid_paths = [p for p in incoming if os.path.normcase(os.path.abspath(p)) != script_abs]
        
        if valid_paths:
            try:
                with open(PENDING_FILE, "a", encoding="utf-8") as f:
                    for p in valid_paths:
                        f.write(f"{p}\n")
            except Exception:
                pass

            is_master = False
            try:
                fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
                is_master = True
            except FileExistsError:
                sys.exit(0)

            if is_master:
                time.sleep(0.4)
                
                all_paths = []
                if os.path.exists(PENDING_FILE):
                    try:
                        with open(PENDING_FILE, "r", encoding="utf-8") as f:
                            all_paths = [line.strip() for line in f if line.strip() and os.path.exists(line.strip())]
                    except Exception:
                        pass
                    try:
                        os.remove(PENDING_FILE)
                    except Exception:
                        pass

                try:
                    if os.path.exists(LOCK_FILE):
                        os.remove(LOCK_FILE)
                except Exception:
                    pass

                if all_paths:
                    unique_paths = list(dict.fromkeys(all_paths))
                    dialog_root = tk.Tk()
                    app_dialog = QuickExpiryDialog(dialog_root, unique_paths)
                    dialog_root.mainloop()
                sys.exit(0)

    root = tk.Tk()
    app = AutoDeleteProApp(root)
    root.mainloop()
