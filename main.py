#!/usr/bin/env python3
"""
Activity #4 - Two Time Zone Clocks (PH + UTC) using Tkinter + Threads

Notes:
- Tkinter widgets must be updated from the MAIN thread.
- Each clock's time calculation runs in its own thread.
- Threads send formatted time strings to the GUI through a thread-safe Queue.
"""

import threading
import time
from datetime import datetime, timezone
from queue import Queue, Empty
import tkinter as tk

# Timezone handling:
# Prefer stdlib zoneinfo (Python 3.9+). Fallback to pytz if zoneinfo isn't available.
try:
    from zoneinfo import ZoneInfo  # Python 3.9+
    PH_TZ = ZoneInfo("Asia/Manila")
    USE_PYTZ = False
except Exception:
    USE_PYTZ = True
    try:
        import pytz
        PH_TZ = pytz.timezone("Asia/Manila")
    except Exception as e:
        raise SystemExit(
            "Could not load timezone info. Install pytz (pip install pytz) "
            "or use Python 3.9+ with zoneinfo."
        ) from e


REFRESH_SECONDS = 1  # refresh rate for both clocks


def format_time(dt: datetime) -> str:
    """24-hour (military) format HH:MM:SS."""
    return dt.strftime("%H:%M:%S")


def clock_worker(name: str, out_q: Queue, stop_event: threading.Event, tz_kind: str) -> None:
    """
    Worker thread that continuously computes the time for a zone and sends updates to the GUI.
    tz_kind: 'UTC' or 'PH'
    """
    while not stop_event.is_set():
        if tz_kind == "UTC":
            now = datetime.now(timezone.utc)
            out_q.put((name, format_time(now)))
        else:  # PH
            if USE_PYTZ:
                now = datetime.now(PH_TZ)
            else:
                now = datetime.now(tz=PH_TZ)
            out_q.put((name, format_time(now)))

        # Sleep in small steps so stop_event is responsive
        for _ in range(10):
            if stop_event.is_set():
                break
            time.sleep(REFRESH_SECONDS / 10)


class DualClockApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Dual Clock (PH & UTC) - Activity #4")

        self.queue = Queue()
        self.stop_event = threading.Event()

        # --- UI ---
        header = tk.Label(root, text="Two Time Zone Clocks", font=("Arial", 16, "bold"))
        header.pack(pady=(12, 6))

        container = tk.Frame(root)
        container.pack(padx=16, pady=10)

        # PH clock
        ph_frame = tk.LabelFrame(container, text="Philippines (Asia/Manila)", padx=14, pady=10)
        ph_frame.grid(row=0, column=0, padx=10, pady=6, sticky="nsew")
        self.ph_time_var = tk.StringVar(value="--:--:--")
        tk.Label(ph_frame, textvariable=self.ph_time_var, font=("Consolas", 28)).pack()

        # UTC clock
        utc_frame = tk.LabelFrame(container, text="UTC", padx=14, pady=10)
        utc_frame.grid(row=0, column=1, padx=10, pady=6, sticky="nsew")
        self.utc_time_var = tk.StringVar(value="--:--:--")
        tk.Label(utc_frame, textvariable=self.utc_time_var, font=("Consolas", 28)).pack()

        # Footer / controls
        footer = tk.Frame(root)
        footer.pack(pady=(0, 12))

        self.status_var = tk.StringVar(value="Running...")
        tk.Label(footer, textvariable=self.status_var).pack(side="left", padx=(0, 12))

        tk.Button(footer, text="Quit", command=self.on_close).pack(side="right")

        # --- Threads (one per clock) ---
        self.threads = [
            threading.Thread(
                target=clock_worker,
                args=("PH", self.queue, self.stop_event, "PH"),
                daemon=True,
            ),
            threading.Thread(
                target=clock_worker,
                args=("UTC", self.queue, self.stop_event, "UTC"),
                daemon=True,
            ),
        ]

        for t in self.threads:
            t.start()

        # Poll the queue to safely update GUI from the main thread
        self.root.after(50, self.poll_queue)

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def poll_queue(self):
        """Read queued updates from worker threads and apply to Tkinter variables."""
        try:
            while True:
                name, value = self.queue.get_nowait()
                if name == "PH":
                    self.ph_time_var.set(value)
                elif name == "UTC":
                    self.utc_time_var.set(value)
        except Empty:
            pass

        if not self.stop_event.is_set():
            self.root.after(50, self.poll_queue)

    def on_close(self):
        """Stop threads and close app safely."""
        if not self.stop_event.is_set():
            self.status_var.set("Stopping...")
            self.stop_event.set()
            # Give threads a moment to exit (they are daemons, so app will still close)
            self.root.after(150, self.root.destroy)


def main():
    root = tk.Tk()
    # A slightly nicer minimum size
    root.minsize(520, 220)
    DualClockApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
