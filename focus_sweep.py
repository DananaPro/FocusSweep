import os
import psutil
import time
import threading
import customtkinter as ctk
import ctypes
import json
import sys
from PIL import Image, ImageTk  # Make sure pillow is installed
from tkinter import messagebox


ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(u"FocusSweepApp")

# -------------------- App Setup --------------------
ctk.set_appearance_mode("dark")
app = ctk.CTk()
app.geometry("500x580")
app.title("Focus Sweep")

# -------------------- Helper for PyInstaller --------------------
def resource_path(relative_path):
    """
    Returns the absolute path to resources, works for dev & PyInstaller.
    """
    if hasattr(sys, "_MEIPASS"):  # PyInstaller bundle folder
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# -------------------- Set App Icon --------------------
icon_file = resource_path("icon.ico")  # your ICO file
if os.path.exists(icon_file):
    try:
        app.iconbitmap(icon_file)
    except Exception as e:
        print(f"Failed to set icon: {e}")
else:
    print("Icon file not found:", icon_file)

# -------------------- AppData Path --------------------
DECKS_PATH = os.path.join(os.getenv('APPDATA'), 'FocusSweep', 'decks.json')
os.makedirs(os.path.dirname(DECKS_PATH), exist_ok=True)

def ensure_decks_file():
    if not os.path.exists(DECKS_PATH):
        with open(DECKS_PATH, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2)

ensure_decks_file()

# -------------------- Declarations------------------
deck_buttons = []
extra_visible = False
delete_mode = False
shake_jobs = {}        # for after jobs
shake_positions = {}   # original x positions of wrappers
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
        with open(DECKS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def write_decks(data):
    with open(DECKS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def load_decks():
    return read_decks()

def save_deck():
    deck_name = deck_entry.get().strip()
    apps_raw = apps_entry.get().strip()

    # Parse + normalize apps
    apps_list = [normalize(app) for app in apps_raw.split(",") if app.strip()]

    if not deck_name:
        log_message("⚠️ Deck name is required.")
        return

    if not apps_list:
        log_message("⚠️ Enter at least one valid app.")
        return

    data = read_decks()

    existing_apps = data.get(deck_name, [])

    # Merge while preserving order and removing duplicates
    merged = list(dict.fromkeys(existing_apps + apps_list))

    if not merged:
        log_message(f"⚠️ Deck '{deck_name}' is empty and was not saved.")
        data.pop(deck_name, None)
        write_decks(data)
        return

    data[deck_name] = merged
    write_decks(data)

    log_message(f"✅ Deck '{deck_name}' saved ({len(merged)} apps).")
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
    # Remove apps
    data[deck_name] = [app for app in data[deck_name] if app not in apps_to_remove]
    
    # Auto-delete empty deck
    if not data[deck_name]:
        del data[deck_name]
        log_message(f"🗑️ Deck '{deck_name}' is now empty and has been deleted.")
    else:
        log_message(f"🗑️ Removed {apps_to_remove} from '{deck_name}'. Current apps: {data[deck_name]}")
    
    write_decks(data)
    apps_entry.delete(0, "end")
    refresh_deck_buttons_dynamic()

    
def clear_all_decks():
    from tkinter import messagebox

    confirm = messagebox.askyesno(
        "Clear All Decks",
        "This will permanently delete ALL decks.\n\nAre you sure?"
    )
    if not confirm:
        return

    write_decks({})
    log_message("🗑️ All decks deleted.")

    global deck_buttons, active_deck_name, safe_apps_lower, extra_visible
    for btn, wrapper in deck_buttons:
        btn.destroy()

    deck_buttons = []
    active_deck_name = None
    safe_apps_lower = set()
    extra_visible = False

    toggle_button.configure(text="Show More Decks")

# -------------------- Refresh Deck Buttons + Shake --------------------
def refresh_deck_buttons_dynamic():
    global deck_buttons
    data = load_decks()
    deck_names = list(data.keys())

    # Destroy old buttons and wrappers
    for btn, wrapper in deck_buttons:
        stop_shake(wrapper)
        btn.destroy()
        wrapper.destroy()
    deck_buttons = []

    for i, name in enumerate(deck_names):
        row, col = divmod(i, 3)  # 3 buttons per row

        # Wrapper frame
        wrapper = ctk.CTkFrame(button_row, fg_color="transparent", width=110, height=40)
        wrapper.grid_propagate(False)
        wrapper.grid(row=row, column=col, padx=5, pady=5)

        # Ensure geometry is calculated so we can store x
        wrapper.update_idletasks()
        shake_positions[wrapper] = wrapper.winfo_x()  # original x for shake

        # Button inside wrapper
        btn = ctk.CTkButton(
            wrapper,
            text=name,
            width=100,
            command=lambda i=i: use_deck_by_index(i)
        )
        btn.place(relx=0.5, rely=0.5, anchor="center")

        deck_buttons.append((btn, wrapper))

        # Visibility logic
        if i >= 3 and not extra_visible:
            wrapper.grid_forget()

    update_deck_buttons()
    set_delete_mode_visual(delete_mode)  # apply delete mode visuals & shake

# -------------------- Shake System --------------------
def set_delete_mode_visual(active):
    for btn, wrapper in deck_buttons:
        if active:
            btn.configure(fg_color="darkred", hover_color="red")
            if wrapper.winfo_ismapped():
                start_shake(wrapper)
        else:
            stop_shake(wrapper)
            btn.configure(fg_color="green", hover_color="green")

def start_shake(wrapper):
    if wrapper not in shake_positions:
        wrapper.update_idletasks()
        shake_positions[wrapper] = wrapper.winfo_x()
    shake_step(wrapper, direction=1)

def shake_step(wrapper, direction):
    if not delete_mode or not wrapper.winfo_ismapped():
        stop_shake(wrapper)
        return

    original_x = shake_positions.get(wrapper, 0)
    offset = 3 * direction
    # Move relative to original x without affecting y
    wrapper.place(x=original_x + offset, y=wrapper.winfo_y())

    shake_jobs[wrapper] = app.after(40, lambda: shake_step(wrapper, -direction))

def stop_shake(wrapper):
    job = shake_jobs.pop(wrapper, None)
    if job:
        app.after_cancel(job)
    original_x = shake_positions.get(wrapper, 0)
    wrapper.place(x=original_x, y=wrapper.winfo_y())

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
    global delete_mode

    if delete_mode:
        from tkinter import messagebox

        confirm = messagebox.askyesno(
            "Delete Deck",
            f"Delete '{deck_name}' permanently?"
        )
        if not confirm:
            return

        data = read_decks()
        data.pop(deck_name, None)
        write_decks(data)

        if active_deck_name == deck_name:
            stop_sweep()

        log_message(f"🗑️ Deck '{deck_name}' deleted.")

        delete_mode = False
        delete_deck_button.configure(text="Delete Deck", fg_color="darkred")
        refresh_deck_buttons_dynamic()
        return

    # normal behavior
    if active_deck_name == deck_name:
        stop_sweep()
    else:
        start_sweep(deck_name)


def update_deck_buttons():
    for btn, wrapper in deck_buttons:
        btn.configure(hover_color="red" if btn.cget("text") == active_deck_name else "green")

def toggle_delete_mode():
    global delete_mode
    delete_mode = not delete_mode

    if delete_mode:
        log_message("⚠️ Delete mode ON: click a deck to delete it.")
        delete_deck_button.configure(text="Cancel Delete", fg_color="gray")
    else:
        log_message("❎ Delete mode cancelled.")
        delete_deck_button.configure(text="Delete Deck", fg_color="darkred")

    set_delete_mode_visual(delete_mode)

        
# -------------------- Dynamic Deck Buttons --------------------
extra_visible = False  # tracks if extra decks are visible


# Wrapper for deck buttons
def use_deck_by_index(i):
    data = load_decks()
    deck_names = list(data.keys())
    if i >= len(deck_names) or i >= len(deck_buttons):
        log_message(f"⚠️ Deck {i+1} does not exist.")
        return
    use_deck_by_name(deck_names[i], deck_buttons[i])

# Button to show/hide extra decks
def toggle_extra_decks():
    global extra_visible
    extra_visible = not extra_visible
    toggle_button.configure(
        text="Hide Extra Decks" if extra_visible else "Show More Decks"
    )
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
action_row_1 = ctk.CTkFrame(app, fg_color="gray25")
action_row_1.pack(pady=(10, 4))

ctk.CTkButton(
    action_row_1,
    text="Save Deck",
    command=save_deck
).pack(side="left", padx=5)

ctk.CTkButton(
    action_row_1,
    text="Remove Apps",
    command=remove_from_deck
).pack(side="left", padx=5)


action_row_2 = ctk.CTkFrame(app, fg_color="gray25")
action_row_2.pack(pady=(4, 10))

delete_deck_button = ctk.CTkButton(
    action_row_2,
    text="Delete Deck",
    fg_color="darkred",
    command=toggle_delete_mode
)
delete_deck_button.pack(side="left", padx=5)

ctk.CTkButton(
    action_row_2,
    text="Clear All",
    fg_color="red",
    command=clear_all_decks
).pack(side="left", padx=5)

# -------------------- Version --------------------
APP_VERSION = "v1.2.0"
version_label = ctk.CTkLabel(app, text=f"Focus Sweep {APP_VERSION}", font=("Arial", 14), text_color="red")
version_label.pack(pady=(5, 5))

refresh_deck_buttons_dynamic()  # populate buttons on startup
app.mainloop()
