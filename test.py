import threading
import time
import customtkinter as ctk

# Create the main window
app = ctk.CTk()
app.geometry("500x400")
app.title("Your App Name")

def background_task():
    for i in range(5):
        print(f"Background task running... {i+1}")
        time.sleep(1)  # wait 1 second

print("Main program starts")

# Create a thread to run the background task
thread = threading.Thread(target=background_task)

# Start the thread
thread.start()

# Meanwhile, main program keeps running
# 1. Label (text display)
label = ctk.CTkLabel(app, text="Hello world!", font=("Arial", 16))
label.pack(pady=10)  # pack it into the window with vertical padding

# 2. Entry (single-line text input)
entry = ctk.CTkEntry(app, width=300)
entry.pack(pady=10)

# 3. Button (clickable button)
def start_button():
    print("Button clicked!")

button = ctk.CTkButton(app, text="start", command=start_button)
button.pack(pady=10)

# 4. Textbox (multi-line text display/input)
textbox = ctk.CTkTextbox(app, width=350, height=150)
textbox.pack(pady=10)

app.mainloop()

# Wait for the background thread to finish before exiting
thread.join()

print("Main program finished")


