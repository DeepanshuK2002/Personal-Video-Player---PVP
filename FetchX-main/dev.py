import os
import sys
import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_FILE = os.path.join(PROJECT_DIR, "FetchX_Desktop.py")


class RestartHandler(FileSystemEventHandler):
    def __init__(self):
        self.process = None
        self.last_restart = 0
        self.start_app()

    def start_app(self):
        print("Starting FetchX...")
        self.process = subprocess.Popen(
            [sys.executable, MAIN_FILE],
            cwd=PROJECT_DIR
        )

    def restart_app(self):
        now = time.time()

        # Prevent multiple restarts from one save
        if now - self.last_restart < 1:
            return

        self.last_restart = now

        print("\nChange detected — restarting FetchX...")

        if self.process and self.process.poll() is None:
            self.process.terminate()

            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()

        self.start_app()

    def on_modified(self, event):
        if event.is_directory:
            return

        if os.path.abspath(event.src_path) == os.path.abspath(MAIN_FILE):
            self.restart_app()


if __name__ == "__main__":
    handler = RestartHandler()

    observer = Observer()
    observer.schedule(handler, PROJECT_DIR, recursive=False)
    observer.start()

    print(f"Watching: {MAIN_FILE}")
    print("Save your Python file to automatically restart FetchX.")
    print("Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

        if handler.process and handler.process.poll() is None:
            handler.process.terminate()

    observer.join()