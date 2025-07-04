import os
import psutil
import time
import threading
import customtkinter as ctk
import ctypes
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(u"FocusSweepApp")


ctk.set_appearance_mode("dark")
app = ctk.CTk()
app.geometry("500x400")
app.title("Focus Sweep")
app.iconbitmap("logo.ico")  # ← your logo here!


# ------------------------------
# 1. Customize thresholds
# ------------------------------
MIN_RAM_MB = 80         # RAM threshold
MIN_CPU_PERCENT = 3.0   # CPU usage threshold
CHECK_INTERVAL = 5      # seconds between scans


# ------------------------------
# 3. System/process whitelist
# ------------------------------
system_whitelist = [
    # Core Windows
    "System", "System Idle Process", "wininit.exe", "winlogon.exe",
    "services.exe", "lsass.exe", "csrss.exe", "smss.exe",

    # Shell & UI
    "explorer.exe", "svchost.exe", "sihost.exe", "StartMenuExperienceHost.exe",
    "ShellExperienceHost.exe", "SearchHost.exe", "TextInputHost.exe",
    "fontdrvhost.exe", "RuntimeBroker.exe", "dwm.exe", "conhost.exe",
    "taskhostw.exe",

    # Security
    "SecurityHealthService.exe", "SecurityHealthSystray.exe", "MsMpEng.exe",
    "wmiPrvSE.exe", "WerFault.exe",

    # Audio & Background
    "audiodg.exe",

    # Script tools
    "python.exe", "cmd.exe", "powershell.exe", "py.exe","Focus Sweep",

    # Extras
    "Spotify.exe", "SignalRPG.exe", "WallpaperAlive.exe", "SignalRgb.exe","Acrobat.exe",

    # Cloud tools
    "OneDrive.exe", "steam.exe", "steamwebhelper.exe",

    # Development tools
    "Code.exe"
]


# Get current script's process ID to avoid closing itself
current_pid = os.getpid()
stop_requested = False

safe_apps_lower = set()
def focus_sweep_loop():
    try:
        while not stop_requested:
            for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent']):
                try:
                    if proc.pid == current_pid:
                        continue
                    name = proc.info['name']
                    if name is None:
                        continue
                    if name.lower() in safe_apps_lower:
                        continue
                    ram_mb = proc.info['memory_info'].rss / (1024 * 1024)
                    cpu_percent = proc.cpu_percent(interval=0.1)
                    if ram_mb > MIN_RAM_MB or cpu_percent > MIN_CPU_PERCENT:
                        try:
                            proc.terminate()
                            textbox.insert("end", f"❌ Closed: {name} | RAM: {ram_mb:.1f} MB | CPU: {cpu_percent:.1f}%\n")
                            textbox.see("end")
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        print("\n🛑 Focus mode stopped by user. Exiting...")




label = ctk.CTkLabel(
    app,
    text="Focus Sweep is active",
    font=("Arial", 16),
    text_color="white"
)
label.pack(pady=10)


label = ctk.CTkLabel(
    app,
    text="Enter the names of the apps you want to keep running",
    font=("Arial", 16),
    text_color="blue"
)
label.pack(pady=10)


entry = ctk.CTkEntry(app, width=300)
entry.pack(pady=10)

textbox = ctk.CTkTextbox(app, width=350, height=150)
textbox.pack(pady=10)

button_clicked = False  # Flag to track state

def start_button():
    global button_clicked, safe_apps_lower, stop_requested

    user_input = entry.get().strip()
    if not user_input:
        textbox.insert("end", "⚠️ Please enter at least one app name.\n")
        return

    if button_clicked:
        # Stop focus sweep
        stop_requested = True
        button_clicked = False
        button.configure(
            text="Start",
            text_color="black",
            hover_color="green"
        )
        textbox.insert("end", "🛑 Focus Sweep stopped.\n")
        textbox.see("end")
        return

    # Start focus sweep
    stop_requested = False  # Reset stop flag

    allowed_apps = [app.strip() + ".exe" for app in user_input.lower().split(',')]
    safe_apps = set(allowed_apps + system_whitelist)
    safe_apps_lower = set(app.lower() for app in safe_apps)

    button_clicked = True

    threading.Thread(target=focus_sweep_loop, daemon=True).start()

    textbox.insert("end", "🧹 Focus Sweep started!\n")
    for app_name in safe_apps:
        textbox.insert("end", f" • {app_name}\n")
    textbox.see("end")

    button.configure(
        text="Stop ?",
        text_color="black",
        hover_color="red"
    )

# Create the Start button
button = ctk.CTkButton(
    app,
    text="Start",
    command=start_button,
    text_color="black",    # Default text black
    hover_color="green"      # Hover green for "Start" state
)
button.pack(pady=10)



app.mainloop()