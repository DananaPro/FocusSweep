import os
import psutil
import time
import PIL.Image
import PIL.ImageTk
import tkinter
import customtkinter
import threading
import customtkinter as ctk
import ctypes
import json
import sys
from PIL import Image, ImageTk  # Make sure pillow is installed
from tkinter import messagebox
import time
import random
from datetime import datetime

ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(u"FocusSweepApp")

# -------------------- App Setup --------------------
ctk.set_appearance_mode("dark")
app = ctk.CTk()
app.geometry("500x580")
app.title("Focus Sweep")

# -------------------- Helper for PyInstaller --------------------
def resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    full_path = os.path.join(base_path, relative_path)
    if not os.path.exists(full_path):
        print(f"⚠️ Resource not found: {full_path}")
    return full_path
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
shake_jobs = {}        # keeps after jobs
shake_grid_positions = {}   # original grid info for wrappers
shake_positions = {}   # original x positions of wrappers
ACTION_BUTTON_COLOR = "#1f6aa5"  # or whatever your main buttons use
last_closed_apps = []
last_closed_apps_lock = threading.Lock()
_last_lockin_time = 0
LOCKIN_COOLDOWN = 60  # seconds
LOCKIN_CHANCE = 1 / 75
# -------------------- Thresholds --------------------
# MIN_RAM_MB:
# 150–250 = normal GUI apps
# 300+   = heavy apps (Chrome, Discord)
MIN_RAM_MB = 200
CHECK_INTERVAL = 5
# -------------------- system_whitelist --------------
system_whitelist = set(
    x.lower() + ".exe" if not x.lower().endswith(".exe") else x.lower()
    for x in [
        "System", "System Idle Process", "wininit.exe", "winlogon.exe",
        "services.exe", "lsass.exe", "csrss.exe", "smss.exe",
        "explorer.exe", "svchost.exe", "sihost.exe",
        "StartMenuExperienceHost.exe", "ShellExperienceHost.exe",
        "SearchHost.exe", "TextInputHost.exe", "fontdrvhost.exe",
        "RuntimeBroker.exe", "dwm.exe", "conhost.exe", "taskhostw.exe",
        "SecurityHealthService.exe", "SecurityHealthSystray.exe",
        "MsMpEng.exe", "wmiPrvSE.exe", "WerFault.exe", "audiodg.exe",
        "python.exe", "cmd.exe", "powershell.exe", "py.exe",
        "FocusSweep.exe", "Code.exe"
    ]
)
# -------------------- Normalize --------------------
def normalize(name: str) -> str:
    if not name:
        return ""
    name = name.strip().lower()
    return name if name.endswith(".exe") else name + ".exe"

# Normalize whitelist ONCE
system_whitelist = set(normalize(x) for x in system_whitelist)

current_pid = os.getpid()
stop_event = threading.Event()
sweep_thread = None
safe_apps_lower = set()
active_deck_name = None

# -------------------- Focus Sweep Loop --------------------
last_closed_apps = []

def focus_sweep_loop():
    global last_closed_apps
    while not stop_event.is_set():
        to_kill, closed_apps = [], []

        for proc in psutil.process_iter(["pid", "name", "memory_info", "username"]):
            try:
                if proc.pid == current_pid:
                    continue

                name_raw = proc.info.get("name")
                if not name_raw:
                    continue

                name = normalize(name_raw)
                if name in safe_apps_lower:
                    continue

                username = (proc.info.get("username") or "").upper()
                if username.startswith("NT AUTHORITY"):
                    continue

                ram_mb = proc.info.get("memory_info").rss / (1024 * 1024)
                if ram_mb >= MIN_RAM_MB:
                    to_kill.append((proc, ram_mb))
            except:
                continue

        for proc, ram_mb in to_kill:
            try:
                if not proc.is_running():
                    continue
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except:
                    proc.kill()
                closed_apps.append((normalize(proc.info["name"]), ram_mb))
            except:
                continue

        if closed_apps:
            with last_closed_apps_lock:
                last_closed_apps = closed_apps.copy()
            app.after(0, lambda apps=closed_apps: display_summary(apps))

        time.sleep(CHECK_INTERVAL)

# -------------------- Display Summary --------------------
def display_summary(closed_apps):
    """
    Logs a short summary of recently closed apps to the textbox.
    """
    summary = ", ".join(name for name, _ in closed_apps[:2])
    extra_count = len(closed_apps) - 2
    if extra_count > 0:
        summary += f" (+{extra_count} more)"

    log_message(f"❌ Closed: {summary}")
# -------------------- Full List Popup --------------------
def show_full_closed_apps():
    with last_closed_apps_lock:
        snapshot = last_closed_apps.copy()

    if not snapshot:
        messagebox.showinfo("Info", "No closed apps yet.")
        return

    if hasattr(show_full_closed_apps, "popup") and show_full_closed_apps.popup.winfo_exists():
        show_full_closed_apps.popup.lift()
        return

    popup = ctk.CTkToplevel(app)
    show_full_closed_apps.popup = popup
    popup.title("Closed Apps")
    popup.geometry("400x350")
    popup.resizable(False, False)

    scroll_frame = ctk.CTkScrollableFrame(popup, width=380, height=220)
    scroll_frame.pack(padx=5, pady=5)

    check_vars = {}
    for name, ram in snapshot:
        var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            scroll_frame,
            text=f"{name} ({ram:.1f} MB)",
            variable=var
        ).pack(anchor="w", pady=2)
        check_vars[name] = var

    deck_label = ctk.CTkLabel(popup, text="Enter deck name:")
    deck_label.pack(pady=(5, 0))

    deck_input = ctk.CTkEntry(popup, width=200)
    deck_input.pack(pady=(0, 5))

    def add_to_deck(apps_list):
        deck_name = deck_input.get().strip()
        if not deck_name:
            messagebox.showwarning("Warning", "Enter a deck name first.")
            return
        if not apps_list:
            messagebox.showinfo("Info", "No apps to add.")
            return

        data = read_decks()
        existing = data.get(deck_name, [])
        merged = list(dict.fromkeys(existing + [normalize(a) for a in apps_list]))
        data[deck_name] = merged
        write_decks(data)

        log_message(f"✅ Added {', '.join(apps_list)} to deck '{deck_name}'")
        refresh_deck_buttons_dynamic()
        popup.destroy()

    ctk.CTkButton(
        popup,
        text="Add Selected to Deck",
        command=lambda: add_to_deck([n for n, var in check_vars.items() if var.get()])
    ).pack(pady=5)

    ctk.CTkButton(
        popup,
        text="Add All to Deck",
        command=lambda: add_to_deck([n for n, _ in snapshot])
    ).pack(pady=5)

    popup.bind("<Escape>", lambda e: popup.destroy())

# -------------------- Logging (HARDENED) --------------------

def log_message(msg):
    try:
        timestamp = datetime.now().strftime("%H:%M:%S")
        if 'app' in globals() and app.winfo_exists():
            app.after(0, lambda: (
                textbox.insert("end", f"[{timestamp}] {msg}\n"),
                textbox.see("end")
            ))
        else:
            print(f"[{timestamp}] {msg}")
    except Exception:
        pass

# -------------------- Deck Management --------------------
def read_decks():
    try:
        with open(DECKS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def write_decks(data):
    tmp = DECKS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, DECKS_PATH)

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
    apps_entry.delete(0, "end")  # clear after saving


def remove_from_deck():
    deck_name = deck_entry.get().strip()
    apps_raw = apps_entry.get().strip()

    if not deck_name:
        log_message("⚠️ Enter a deck name.")
        return
    if not apps_raw:
        log_message("⚠️ Enter apps to remove.")
        return

    apps_to_remove = [normalize(app.strip()) for app in apps_raw.split(',') if app.strip()]
    data = read_decks()

    if deck_name not in data:
        log_message(f"⚠️ Deck '{deck_name}' does not exist.")
        return

    current_apps = data[deck_name]
    removed = []
    skipped = []

    for app in apps_to_remove:
        if app in current_apps:
            current_apps.remove(app)
            removed.append(app)
        else:
            skipped.append(app)

    # Delete deck if empty
    if not current_apps:
        del data[deck_name]
        log_message(f"🗑️ Deck '{deck_name}' is now empty and has been deleted.")
    else:
        data[deck_name] = current_apps
        log_message(f"🗑️ Removed: {', '.join(removed)}. Skipped: {', '.join(skipped)}.")

    write_decks(data)
    apps_entry.delete(0, "end")
    refresh_deck_buttons_dynamic()

def clear_all_decks():
    global deck_buttons  
    confirm = messagebox.askyesno(
        "Clear All Decks",
        "This will permanently delete ALL decks.\n\nAre you sure?"
    )
    if not confirm:
        return

    try:
        tmp = DECKS_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2)
        os.replace(tmp, DECKS_PATH)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to clear decks: {e}")
        return

    log_message("🗑️ All decks deleted.")

    global deck_buttons, active_deck_name, safe_apps_lower, extra_visible
    for btn, wrapper in deck_buttons:
        stop_shake(wrapper)
        btn.destroy()
        wrapper.destroy()

    deck_buttons = []
    active_deck_name = None
    safe_apps_lower = set()
    extra_visible = False

    toggle_button.configure(text="Show More Decks")
# -------------------- Refresh Deck Buttons + Shake --------------------
def refresh_deck_buttons_dynamic():
    global deck_buttons
    if 'deck_buttons' not in globals():
        deck_buttons = []
    if 'button_row' not in globals():
        return  # can't refresh buttons yet
    """
    Refreshes all deck buttons dynamically.
    Destroys old buttons, creates new ones, applies shake if delete mode is on.
    """

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

        # Button inside wrapper
        btn = ctk.CTkButton(wrapper, text=name, width=100, command=lambda i=i: use_deck_by_index(i))
        btn.place(relx=0.5, rely=0.5, anchor="center")

        deck_buttons.append((btn, wrapper))

        # Visibility logic
        if i >= 3 and not extra_visible:
            wrapper.grid_forget()

        # Ensure geometry is calculated so we can store x for shake
        wrapper.update_idletasks()
        shake_positions[wrapper] = wrapper.winfo_x()
        shake_grid_positions[wrapper] = wrapper.grid_info()

    update_deck_buttons()
    set_delete_mode_visual(delete_mode)

# -------------------- Shake System --------------------
def set_delete_mode_visual(active):
    for _, wrapper in deck_buttons:
        if active and wrapper.winfo_ismapped():
            start_shake(wrapper)
        else:
            stop_shake(wrapper)

def start_shake(wrapper):
    if wrapper in shake_jobs:
        return
    # store grid info
    shake_positions[wrapper] = wrapper.grid_info()
    shake_jobs[wrapper] = app.after(0, lambda: shake_step(wrapper, 1))

def shake_step(wrapper, direction):
    if not delete_mode or not wrapper.winfo_ismapped():
        stop_shake(wrapper)
        return

    offset = 4 * direction
    wrapper.place(in_=button_row, x=wrapper.winfo_x() + offset, y=wrapper.winfo_y())
    shake_jobs[wrapper] = app.after(50, lambda: shake_step(wrapper, -direction))

def stop_shake(wrapper):
    job = shake_jobs.pop(wrapper, None)
    if job:
        app.after_cancel(job)
    if wrapper.winfo_ismapped() and wrapper in shake_grid_positions:
        wrapper.place_forget()
        wrapper.grid(**shake_grid_positions[wrapper])
# -------------------- Sweep Control --------------------
def stop_sweep():
    global sweep_thread, active_deck_name
    stop_event.set()
    active_deck_name = None
    update_deck_buttons()


def start_sweep(deck_name):
    global sweep_thread, active_deck_name, safe_apps_lower
    log_message("⚠️ All non-deck apps above RAM threshold will be closed.")

    if sweep_thread and sweep_thread.is_alive():
        return

    stop_event.clear()

    data = load_decks()
    if deck_name not in data:
        log_message(f"⚠️ Deck '{deck_name}' not found.")
        return

    active_deck_name = deck_name
    allowed_apps = data[deck_name]

    safe_apps_lower = set(
        normalize(app) for app in allowed_apps
    ) | system_whitelist

    sweep_thread = threading.Thread(
        target=focus_sweep_loop,
        daemon=True
    )
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
    for btn, _ in deck_buttons:
        name = btn.cget("text")

        if delete_mode:
            btn.configure(
                fg_color="darkred",
                hover_color="red"
            )

        elif name == active_deck_name:
            btn.configure(
                fg_color=ACTION_BUTTON_COLOR,  # same as Start/Stop buttons
                hover_color="red"
            )

        else:
            btn.configure(
                fg_color="gray30",
                hover_color="green"
            )


def toggle_delete_mode():
    global delete_mode
    delete_mode = not delete_mode

    if delete_mode:
        log_message("⚠️ Delete mode ON: click a deck to delete it.")
        delete_deck_button.configure(text="Cancel Delete", fg_color="gray")
    else:
        log_message("❎ Delete mode cancelled.")
        delete_deck_button.configure(text="Delete Deck", fg_color="darkred")
        
    update_deck_buttons()
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
ctk.CTkButton(app, text="Show Full Closed Apps", command=show_full_closed_apps).pack(pady=(0,5))
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

# -------------------- lock in --------------------
def load_quotes():
    path = resource_path("quotes.json")
    if not os.path.exists(path):
        print(f"⚠️ quotes.json not found at {path}")
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

quotes_by_mood = load_quotes()
# -------------------- secret ---------------------
def show_quote_popup(quote):
    popup = ctk.CTkToplevel()
    popup.geometry("500x120+800+400")  # adjust size & position
    popup.title("FocusBoost 💡")
    
    label = ctk.CTkLabel(
        popup,
        text=quote,
        wraplength=480,
        justify="center",
        font=("Arial", 14)
    )
    label.pack(expand=True, fill="both", padx=10, pady=10)
    
    # Auto-close after 5 seconds
    popup.after(5000, popup.destroy)

def show_random_quote():
    # Pick a random mood
    mood = random.choice(list(quotes_by_mood.keys()))
    # Pick a random quote from that mood
    quote = random.choice(quotes_by_mood[mood])
    # Show popup
    show_quote_popup(quote)
    # Schedule next popup in 3–7 minutes (milliseconds)
    delay = random.randint(180000, 420000)
    app.after(delay, show_random_quote)

# Start the cycle
app.after(0, show_random_quote)
# -------------------- Version --------------------

APP_VERSION = "v1.3.1 beta"
version_label = ctk.CTkLabel(app, text=f"Focus Sweep {APP_VERSION}", font=("Arial", 14), text_color="red")
version_label.pack(pady=(5, 5))

refresh_deck_buttons_dynamic()  # populate buttons on startup
app.mainloop()
