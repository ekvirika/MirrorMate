import serial
import time
import tkinter as tk

# --- CONFIG ---
PORT = '/dev/cu.usbserial-2140'  # Change this to your port
BAUD = 115200
FINGER_NAMES = ['Thumb', 'Index', 'Middle', 'Ring', 'Pinky']

# --- CONNECT TO ARDUINO ---
arduino = serial.Serial(PORT, BAUD, timeout=1)
time.sleep(2)
print("Connected to Arduino!")

# --- FUNCTIONS ---
def move_servo(finger_index, angle):
    command = f"{finger_index + 1}:{int(angle)}\n"
    arduino.write(command.encode())
    print(f"Sent -> {command.strip()}")

def save_calibration():
    with open("finger_calibration.txt", "w") as f:
        for i, (min_val, max_val) in enumerate(zip(min_vars, max_vars)):
            f.write(f"{FINGER_NAMES[i]}: min={min_val.get()}, max={max_val.get()}\n")
    print("Calibration saved → finger_calibration.txt")

# --- GUI ---
root = tk.Tk()
root.title("InMoov Hand Calibration")

sliders = []
min_vars, max_vars = [], []

for i, name in enumerate(FINGER_NAMES):
    frame = tk.Frame(root, pady=10)
    frame.pack()

    tk.Label(frame, text=name, font=("Arial", 12, "bold")).pack()

    slider = tk.Scale(frame, from_=0, to=180, orient="horizontal", length=300,
                      label="Servo angle", command=lambda val, idx=i: move_servo(idx, val))
    slider.pack()

    min_var = tk.IntVar(value=0)
    max_var = tk.IntVar(value=180)
    min_vars.append(min_var)
    max_vars.append(max_var)

    min_frame = tk.Frame(frame)
    min_frame.pack()
    tk.Label(min_frame, text="Min:").pack(side="left")
    tk.Entry(min_frame, textvariable=min_var, width=5).pack(side="left", padx=5)
    tk.Label(min_frame, text="Max:").pack(side="left")
    tk.Entry(min_frame, textvariable=max_var, width=5).pack(side="left", padx=5)

save_btn = tk.Button(root, text="💾 Save Calibration", command=save_calibration, bg="lightgreen", font=("Arial", 12, "bold"))
save_btn.pack(pady=10)

root.mainloop()
