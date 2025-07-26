
import asyncio
import tkinter as tk
from tkinter import ttk
import threading
from bleak import BleakScanner

# --- Constants ---
APPLE_MANUFACTURER_ID = 76
DATA_LENGTH = 27
BATTERY_SERVICE_UUID = "0000180f-0000-1000-8000-00805f9b34fb"

# --- Data Parsing Functions ---
def parse_airpods_data(raw_data):
    """Parses raw AirPods advertisement data into a dict."""
    hex_data = raw_data.hex()
    
    def get_level(hex_char):
        level = int(hex_char, 16)
        return level * 10 if level <= 10 else None

    left_level = get_level(hex_data[12])
    right_level = get_level(hex_data[13])
    case_level = get_level(hex_data[15])

    return {
        "Left": left_level,
        "Right": right_level,
        "Case": case_level,
    }

# --- GUI Classes ---
class DeviceBatteryFrame(tk.Frame):
    """A widget to display battery info for a single device component."""
    def __init__(self, parent, name, battery_level, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.configure(bg="white")

        self.name_label = tk.Label(self, text=name, font=("Segoe UI", 10), bg="white", anchor="w")
        self.name_label.pack(fill="x", padx=10, pady=(5, 0))

        progress_frame = tk.Frame(self, bg="white")
        progress_frame.pack(fill="x", padx=10, pady=(0, 5))

        self.progress = ttk.Progressbar(progress_frame, orient="horizontal", length=200, mode="determinate")
        self.progress.pack(side="left", fill="x", expand=True)

        self.percent_label = tk.Label(progress_frame, font=("Segoe UI", 10), bg="white", width=5, anchor="e")
        self.percent_label.pack(side="left", padx=(5, 0))

        self.set_battery_level(battery_level)

    def set_battery_level(self, level):
        if level is not None:
            self.progress["value"] = level
            self.percent_label.config(text=f"{level}%")
            color = "green" if level > 50 else "orange" if level > 20 else "red"
            ttk.Style().configure(f"{color}.Horizontal.TProgressbar", background=color)
            self.progress.config(style=f"{color}.Horizontal.TProgressbar")
        else:
            self.progress["value"] = 0
            self.percent_label.config(text="N/A")
            ttk.Style().configure("grey.Horizontal.TProgressbar", background="grey")
            self.progress.config(style="grey.Horizontal.TProgressbar")

class Application(tk.Tk):
    """Main application window."""
    def __init__(self):
        super().__init__()
        self.title("Bluetooth Device Checker")
        self.geometry("320x400")
        self.configure(bg="white")
        
        self.status_label = tk.Label(self, text="Scanning...", font=("Segoe UI", 10), bg="white", pady=15)
        self.status_label.pack(fill="x")

        self.device_frames = {} # To hold device widgets

        self.scan_thread = threading.Thread(target=self.ble_scanner_thread, daemon=True)
        self.scan_thread.start()

    def ble_scanner_thread(self):
        """Runs the asyncio event loop for bleak."""
        asyncio.run(self.scan_and_update())

    async def scan_and_update(self):
        """Continuously scans for devices and updates the GUI."""
        while True:
            self.after(0, self.status_label.config, {"text": "Scanning..."})
            devices_found = {}

            async with BleakScanner() as scanner:
                await asyncio.sleep(5.0)
                
                for dev, adv in scanner.discovered_devices_and_advertisement_data.values():
                    if APPLE_MANUFACTURER_ID in adv.manufacturer_data and len(adv.manufacturer_data[APPLE_MANUFACTURER_ID]) == DATA_LENGTH:
                        name = dev.name or "AirPods"
                        if name not in devices_found:
                            devices_found[name] = {"type": "airpods", "data": adv.manufacturer_data[APPLE_MANUFACTURER_ID]}
                    elif BATTERY_SERVICE_UUID in adv.service_uuids:
                        name = dev.name or "Unknown Device"
                        # For standard devices, we'd need to connect, which is slow.
                        # For this version, we'll just show they exist. A full implementation
                        # would require a connection queue.
                        if name not in devices_found:
                             devices_found[name] = {"type": "standard", "address": dev.address}


            self.after(0, self.update_gui, devices_found)
            self.after(0, self.status_label.config, {"text": "Scan complete. Next scan in 15s."})
            await asyncio.sleep(15) # Wait before next scan

    def update_gui(self, devices):
        """Updates the Tkinter window with the latest device data."""
        if not devices:
            self.status_label.config(text="No devices found. Retrying...")
            return

        # Remove old frames
        for name in list(self.device_frames.keys()):
            if name not in devices:
                self.device_frames[name].destroy()
                del self.device_frames[name]

        # Add/update frames
        for name, info in devices.items():
            if name not in self.device_frames:
                container = tk.LabelFrame(self, text=name, padx=5, pady=5, bg="white", font=("Segoe UI", 12, "bold"))
                container.pack(fill="x", padx=10, pady=5)
                self.device_frames[name] = container
            
            container = self.device_frames[name]
            # Clear old widgets in container
            for widget in container.winfo_children():
                widget.destroy()

            if info["type"] == "airpods":
                battery_data = parse_airpods_data(info["data"])
                for part, level in battery_data.items():
                    DeviceBatteryFrame(container, part, level, bg="white").pack(fill="x")
            elif info["type"] == "standard":
                # In a real app, you'd connect here to get the battery level.
                # For now, we just show it was detected.
                tk.Label(container, text="Standard battery device detected.", bg="white").pack(padx=5, pady=5)


if __name__ == "__main__":
    app = Application()
    app.mainloop()
