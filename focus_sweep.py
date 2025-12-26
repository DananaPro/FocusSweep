import os
import psutil
import time
import threading
import customtkinter as ctk
import ctypes
import json
import sys

ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(u"FocusSweepApp")

# -------------------- App Setup --------------------
ctk.set_appearance_mode("dark")
app = ctk.CTk()
app.geometry("500x500")
app.title("Focus Sweep")

def resource_path(relative_path):
    """Get absolute path to resource (works for dev and PyInstaller exe)."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

try:
    app.iconbitmap(resource_path("icon.ico"))
except Exception:
    pass

DECKS_PATH = "decks.json"

def ensure_decks_file():
    if not os.path.exists(DECKS_PATH):
        with open(DECKS_PATH, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2)

ensure_decks_file()


# -------------------- Thresholds --------------------
MIN_RAM_MB = 80
MIN_CPU_PERCENT = 3.0
CHECK_INTERVAL = 5

# -------------------- Whitelist --------------------
system_whitelist = [
    "System", "System Idle Process", "wininit.exe", "winlogon.exe",
    "services.exe", "lsass.exe", "csrss.exe", "smss.exe","SystemSettings",
    "explorer.exe", "svchost.exe", "sihost.exe", "StartMenuExperienceHost.exe",
    "ShellExperienceHost.exe", "SearchHost.exe", "TextInputHost.exe",
    "fontdrvhost.exe", "RuntimeBroker.exe", "dwm.exe", "conhost.exe",
    "taskhostw.exe", "SecurityHealthService.exe", "SecurityHealthSystray.exe",
    "MsMpEng.exe", "wmiPrvSE.exe", "WerFault.exe", "audiodg.exe",
    "python.exe", "cmd.exe", "powershell.exe", "py.exe","Focus Sweep",
    "GitExtensions","Git Extensions", "SignalRPG.exe", "WallpaperAlive.exe",
    "SignalRgb.exe", "Code.exe"
]

current_pid = os.getpid()
stop_event = threading.Event()
sweep_thread = None
safe_apps_lower = set()
active_deck_name = None

def normalize(name):
    if not name:
        return ""
    name = name.strip().lower()
    return name if name.endswith(".exe") else f"{name}.exe"

# -------------------- Focus Sweep Loop --------------------
def focus_sweep_loop():
    while not stop_event.is_set():
        for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
            try:
                if proc.pid == current_pid:
                    continue
                proc_name = normalize(proc.info['name'])
                if proc_name in safe_apps_lower:
                    continue
                ram_mb = proc.info['memory_info'].rss / (1024*1024)
                cpu_percent = proc.cpu_percent(None)
                if ram_mb > MIN_RAM_MB or cpu_percent > MIN_CPU_PERCENT:
                    try:
                        proc.terminate()
                        log_message(f"❌ Closed: {proc.info['name']} | RAM: {ram_mb:.1f} MB | CPU: {cpu_percent:.1f}%")
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        time.sleep(CHECK_INTERVAL)

def log_message(msg):
    app.after(0, lambda: (textbox.insert("end", msg + "\n"), textbox.see("end")))

# -------------------- Deck Management --------------------
def read_decks():
    try:
        with open("decks.json", "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def write_decks(data):
    with open("decks.json", "w") as f:
        json.dump(data, f, indent=2)

def load_decks():
    return read_decks()

def save_deck():
    deck_name = deck_entry.get().strip()
    apps_raw = apps_entry.get().strip()
    if not deck_name or not apps_raw:
        log_message("⚠️ Please enter deck name and at least one app.")
        return
    apps_list = [normalize(app) for app in apps_raw.split(',')]
    data = read_decks()
    data.setdefault(deck_name, [])
    data[deck_name].extend(apps_list)
    data[deck_name] = list(set(data[deck_name]))
    write_decks(data)
    log_message(f"✅ Deck '{deck_name}' saved.")
    refresh_deck_buttons_dynamic()  

def remove_from_deck():
    deck_name = deck_entry.get().strip()
    apps_raw = apps_entry.get().strip()
    if not deck_name or not apps_raw:
        log_message("⚠️ Enter deck name and apps to remove.")
        return
    apps_to_remove = [normalize(app) for app in apps_raw.split(',')]
    data = read_decks()
    if deck_name not in data:
        log_message(f"⚠️ Deck '{deck_name}' does not exist.")
        return
    data[deck_name] = [app for app in data[deck_name] if app not in apps_to_remove]
    write_decks(data)
    log_message(f"🗑️ Removed {apps_to_remove} from '{deck_name}'. Current apps: {data[deck_name]}")
    apps_entry.delete(0, "end")
    refresh_deck_buttons_dynamic()
    
def clear_all_decks():
    write_decks({})
    log_message("🗑️ All decks deleted.")
    for button in deck_buttons:
        button.configure(text="")
    refresh_deck_buttons_dynamic()  

def refresh_deck_buttons_dynamic():
    global deck_buttons
    data = load_decks()
    deck_names = list(data.keys())

    # Clear old buttons
    for btn in deck_buttons:
        btn.destroy()
    deck_buttons = []

    # Place buttons in grid: 3 per row
    for i, name in enumerate(deck_names):
        btn = ctk.CTkButton(
            button_row,
            text=name,
            command=lambda i=i: use_deck_by_index(i),
            width=100
        )
        row = i // 3
        col = i % 3
        if i < 3 or extra_visible:  # show first 3 always, extras only if toggled
            btn.grid(row=row, column=col, padx=5, pady=5)
        deck_buttons.append(btn)

    update_deck_buttons()

    # Update hover colors
    update_deck_buttons()



# -------------------- Sweep Control --------------------
def stop_sweep():
    global sweep_thread, active_deck_name
    if sweep_thread and sweep_thread.is_alive():
        stop_event.set()
        sweep_thread.join()
        sweep_thread = None
        log_message("🛑 Focus Sweep stopped.")
    active_deck_name = None
    stop_event.clear()
    update_deck_buttons()

def start_sweep(deck_name):
    global sweep_thread, active_deck_name, safe_apps_lower
    stop_sweep()
    data = load_decks()
    if deck_name not in data:
        log_message(f"⚠️ Deck '{deck_name}' not found.")
        return
    active_deck_name = deck_name
    allowed_apps = data[deck_name]
    safe_apps_lower = set(normalize(app) for app in allowed_apps + system_whitelist)
    # Prime CPU
    for proc in psutil.process_iter(['pid', 'name']):
        try: proc.cpu_percent(None)
        except (psutil.NoSuchProcess, psutil.AccessDenied): continue
    sweep_thread = threading.Thread(target=focus_sweep_loop, daemon=True)
    sweep_thread.start()
    log_message(f"🧹 Focus Sweep started: {deck_name}")
    update_deck_buttons()

def use_deck_by_name(deck_name, button):
    if not deck_name:
        return
    if active_deck_name == deck_name:
        stop_sweep()
    else:
        start_sweep(deck_name)

def update_deck_buttons():
    for b in deck_buttons:
        b.configure(hover_color="red" if b.cget("text") == active_deck_name else "green")

        
# -------------------- Dynamic Deck Buttons --------------------
deck_buttons = []  # all deck buttons
extra_visible = False  # tracks if extra decks are visible


# Wrapper for deck buttons
def use_deck_by_index(i):
    data = load_decks()
    deck_names = list(data.keys())
    if i >= len(deck_names):
        log_message(f"⚠️ Deck {i+1} does not exist.")
        return
    use_deck_by_name(deck_names[i], deck_buttons[i])

# Button to show/hide extra decks
def toggle_extra_decks():
    global extra_visible
    extra_visible = not extra_visible
    toggle_button.configure(text="Hide Extra Decks" if extra_visible else "Show More Decks")
    refresh_deck_buttons_dynamic()

# -------------------- UI --------------------
# -------------------- Decks Section --------------------
deck_label = ctk.CTkLabel(app, text="Decks:", font=("Arial", 16))
deck_label.pack(pady=(10, 0))

# Frame to hold all deck buttons
button_row = ctk.CTkFrame(app, fg_color="gray20")
button_row.pack(pady=5)

# Button to show/hide extra decks
toggle_button = ctk.CTkButton(app, text="Show More Decks", command=toggle_extra_decks)
toggle_button.pack(pady=5)

# List to store all dynamically created deck buttons
deck_buttons = []

# Initially populate first 3 deck buttons


# -------------------- Deck Inputs Section --------------------
label1 = ctk.CTkLabel(app, text="Enter deck name:", font=("Arial", 14))
label1.pack(pady=(10, 0))
deck_entry = ctk.CTkEntry(app, width=300)
deck_entry.pack(pady=5)

label2 = ctk.CTkLabel(app, text="Enter apps (comma separated):", font=("Arial", 14))
label2.pack(pady=(10, 0))
apps_entry = ctk.CTkEntry(app, width=300)
apps_entry.pack(pady=5)


# -------------------- Log Textbox --------------------
textbox = ctk.CTkTextbox(app, width=350, height=150)
textbox.pack(pady=10)


# -------------------- Action Buttons --------------------
action_row = ctk.CTkFrame(app, fg_color="gray25")
action_row.pack(pady=10)
ctk.CTkButton(action_row, text="Save Deck", command=save_deck).pack(side="left", padx=5)
ctk.CTkButton(action_row, text="Remove Apps", command=remove_from_deck).pack(side="left", padx=5)
ctk.CTkButton(action_row, text="Clear All Decks", command=clear_all_decks).pack(side="left", padx=5)


refresh_deck_buttons_dynamic()  # populate buttons on startup
app.mainloop()
