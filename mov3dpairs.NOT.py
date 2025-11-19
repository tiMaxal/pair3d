import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime
import threading
import time
import sys
import json

def get_app_dir():
    """
    Get the application directory for storing settings and primary log file.
    Returns the executable directory if writable, else the script directory, else ~/.config/mov3dpairs.
    """
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        if os.access(exe_dir, os.W_OK):
            return exe_dir
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if os.access(script_dir, os.W_OK):
        return script_dir
    config_dir = os.path.expanduser("~/.config/mov3dpairs")
    os.makedirs(config_dir, exist_ok=True)
    return config_dir

def load_settings():
    """
    Load the previous source directory from the settings file, if it exists.
    """
    settings_file = os.path.join(get_app_dir(), "mov3dpairs_settings.json")
    try:
        with open(settings_file, "r", encoding="utf-8") as f:
            settings = json.load(f)
            folder = settings.get("last_folder", "")
            if folder and os.path.isdir(folder):
                folder_var.set(folder)
                update_folder_contents_listbox()
    except (FileNotFoundError, json.JSONDecodeError):
        pass  # No settings file or invalid, ignore

def save_settings(folder):
    """
    Save the selected folder to the settings file.
    """
    settings_file = os.path.join(get_app_dir(), "mov3dpairs_settings.json")
    try:
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump({"last_folder": folder}, f)
    except Exception as e:
        print(f"Failed to save settings: {e}")

def choose_folder():
    """
    Open a dialog to let the user select a folder.
    Sets the selected folder path in the folder_var StringVar and saves to settings.
    """
    folder = filedialog.askdirectory()
    if folder:
        folder_var.set(folder)
        save_settings(folder)
        update_folder_contents_listbox()

def delete_if_empty(path):
    """
    Delete the folder at 'path' if it is empty, including any .picasa.ini-only folders.
    """
    if os.path.isdir(path):
        contents = os.listdir(path)
        if not contents:
            os.rmdir(path)
        elif contents == ['.picasa.ini']:
            os.remove(os.path.join(path, '.picasa.ini'))
            os.rmdir(path)

def move_contents(src_dir, dst_dir):
    """
    Move all files from src_dir to dst_dir and delete src_dir if empty.
    """
    os.makedirs(dst_dir, exist_ok=True)
    for item in os.listdir(src_dir):
        src_item = os.path.join(src_dir, item)
        dst_item = os.path.join(dst_dir, item)
        if os.path.isfile(src_item):
            shutil.move(src_item, dst_item)
    delete_if_empty(src_dir)

def get_image_files(directory):
    """
    Retrieve a list of image file paths from the given directory.
    """
    try:
        return [
            os.path.join(directory, f)
            for f in os.listdir(directory)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
            and os.path.isfile(os.path.join(directory, f))
        ]
    except FileNotFoundError:
        return []  # Return empty list if directory is missing

def update_folder_contents_listbox():
    """
    Update the Listbox to show images in the selected folder and subfolders.
    """
    listbox_folder_contents.delete(0, tk.END)
    folder = folder_var.get()
    if not folder:
        return
    try:
        total_images = 0
        for dirpath, _, filenames in os.walk(folder):
            image_files = [f for f in filenames if f.lower().endswith((".jpg", ".jpeg", ".png"))]
            if image_files:
                rel_subfolder = os.path.relpath(dirpath, folder)
                listbox_folder_contents.insert(tk.END, f"[{rel_subfolder}]")
                for f in sorted(image_files):
                    listbox_folder_contents.insert(tk.END, f"    {f}")
                total_images += len(image_files)
        label_image_count.config(text=f"Total images found: {total_images}")
    except Exception as e:
        label_image_count.config(text="Error reading folder")
        listbox_folder_contents.insert(tk.END, f"Error: {e}")

def process_tree():
    """
    Process the folder tree based on the 'Move to Parent' checkbox.
    - If checked: Moves '_pairs' files to parent in duplicated tree (root '_pairs' to duplicated root).
    - If not checked: Moves '_pairs' files to '_pairs' in duplicated tree.
    - Moves '_singles' files to their parent in the source tree (root '_singles' to source root).
    - After all processing, renames source root to '[source]_singles'.
    - Logs to a file in the app folder and a copy in the source folder.
    """
    src_root = folder_var.get()
    if not src_root:
        messagebox.showerror("Error", "Please select a folder.")
        return

    base_name = os.path.basename(src_root)
    if base_name.endswith("_singles"):
        if not messagebox.askyesno(
            "Warning",
            f"Source folder '{src_root}' ends with '_singles', indicating it may have been processed before. Continue?"
        ):
            return

    parent_dir = os.path.dirname(src_root)
    dst_root = os.path.join(parent_dir, f"_x2_{base_name}")
    singles_root = os.path.join(parent_dir, f"{base_name}_singles")

    if os.path.exists(dst_root):
        if not messagebox.askyesno("Destination Exists", f"Destination '{dst_root}' already exists. Overwrite?"):
            return
        try:
            shutil.rmtree(dst_root)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to remove existing destination: {e}")
            return

    os.makedirs(dst_root)

    app_log_file = os.path.join(get_app_dir(), "mov3dpairs_log.txt")
    src_log_file = os.path.join(src_root, "mov3dpairs_log.txt")

    def log(msg):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {msg}\n"
        # Write to app folder log
        try:
            with open(app_log_file, "a", encoding="utf-8") as f:
                f.write(log_message)
        except Exception as e:
            print(f"Failed to write to app log: {e}")
        # Write to source folder log
        try:
            with open(src_log_file, "a", encoding="utf-8") as f:
                f.write(log_message)
        except Exception as e:
            print(f"Failed to write to source log: {e}")

    log(f"Processing from: {src_root}")
    log(f"Duplicated tree will be at: {dst_root}")

    def task():
        start_time = time.time()
        total_files = 0
        for dirpath, _, filenames in os.walk(src_root):
            total_files += len([f for f in filenames if f.lower().endswith((".jpg", ".jpeg", ".png"))])
        processed = [0]

        def progress_callback():
            now = time.time()
            elapsed = max(0, now - start_time - total_paused_time[0])
            processed_count = processed[0]
            progress_value = min(100, (processed_count / total_files * 100) if total_files else 100)
            remaining = ((elapsed / progress_value) * (100 - progress_value)) if progress_value > 0 else -1
            root.after(0, lambda: update_progress(progress_value, elapsed, remaining, processed_count, total_files))

        move_to_parent = move_to_parent_var.get() == "1"

        for dirpath, dirnames, _ in os.walk(src_root, topdown=False):
            rel_path = os.path.relpath(dirpath, src_root)

            if os.path.basename(dirpath) == '_pairs':
                if move_to_parent:
                    parent_path = os.path.dirname(dirpath)
                    parent_rel = os.path.relpath(parent_path, src_root)
                    pair_dest = dst_root if parent_rel == '.' else os.path.join(dst_root, parent_rel)
                else:
                    pair_dest = os.path.join(dst_root, rel_path)
                log(f"Moving from _pairs: {dirpath} → {pair_dest}")
                move_contents(dirpath, pair_dest)
                processed[0] += len(get_image_files(dirpath))
                progress_callback()

            elif os.path.basename(dirpath) == '_singles':
                parent_path = os.path.dirname(dirpath)
                parent_rel = os.path.relpath(parent_path, src_root)
                single_dest = src_root if parent_rel == '.' else parent_path
                log(f"Moving from _singles: {dirpath} → {single_dest}")
                move_contents(dirpath, single_dest)
                processed[0] += len(get_image_files(dirpath))
                progress_callback()

            delete_if_empty(dirpath)

            # Pause support
            while not pause_event.is_set():
                time.sleep(0.1)

        # Always rename source root to [source]_singles
        try:
            if os.path.exists(singles_root):
                log(f"Warning: '{singles_root}' already exists, merging contents")
                move_contents(src_root, singles_root)
                shutil.rmtree(src_root)
            else:
                os.rename(src_root, singles_root)
            log(f"Renamed source root: {src_root} → {singles_root}")
            root.after(0, lambda: folder_var.set(singles_root))  # Update GUI to reflect new root
            save_settings(singles_root)  # Update settings with new root
        except Exception as e:
            log(f"Failed to rename source root to {singles_root}: {e}")
            messagebox.showerror("Error", f"Failed to rename source root to {singles_root}: {e}")

        elapsed = time.time() - start_time
        root.after(0, lambda: update_progress(100, elapsed, 0, processed[0], total_files))
        root.after(0, lambda: log(f"Done. Primary log saved at: {app_log_file}, Source log saved at: {singles_root}/mov3dpairs_log.txt"))
        root.after(0, lambda: messagebox.showinfo("Done", f"Processing complete. Primary log saved at: {app_log_file}\nSource log saved at: {singles_root}/mov3dpairs_log.txt"))

    pause_event.set()
    threading.Thread(target=task, daemon=True).start()

def update_progress(value, elapsed=None, remaining=None, processed=None, total=None):
    """
    Update the progress bar and info labels.
    """
    progress["value"] = value
    if elapsed is not None:
        label_elapsed.config(text=f"Elapsed: {int(elapsed)}s")
    if remaining is not None:
        label_remaining.config(text=f"Estimated remaining: {int(remaining) if remaining >= 0 else '--'}s")
    if processed is not None:
        label_processed.config(text=f"Processed: {processed}")
    if total is not None:
        label_total.config(text=f"Total: {total}")
    root.update_idletasks()

def pause_or_continue():
    """
    Toggle pause/continue state for processing.
    """
    if pause_event.is_set():
        pause_event.clear()
        pause_continue_label.set("Continue")
        pause_start_time[0] = time.time()
    else:
        pause_event.set()
        pause_continue_label.set("Pause")
        if pause_start_time[0] is not None:
            total_paused_time[0] += time.time() - pause_start_time[0]
            pause_start_time[0] = None

def confirm_close():
    """
    Confirm close if processing is in progress.
    """
    if 0 < progress["value"] < 100:
        if not messagebox.askyesno("Work in progress", "Are you sure you want to close?"):
            return
    root.destroy()

# --- GUI setup ---

root = tk.Tk()
root.title("mov3dpairs")
root.configure(bg="lightcoral")
root.geometry("600x800")
root.tk_setPalette(background="lightcoral", foreground="blue")

screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
x = (screen_width - 600) // 2
y = (screen_height - 800) // 2
root.geometry(f"+{x}+{y}")

folder_var = tk.StringVar()
move_to_parent_var = tk.StringVar(value="1")
pause_event = threading.Event()
pause_event.set()
pause_continue_label = tk.StringVar(value="Pause")
pause_start_time = [None]
total_paused_time = [0]

style = ttk.Style()
style.configure("TCheckbutton", background="lightcoral", foreground="blue")
style.configure("TFrame", background="lightcoral")
style.configure("Progress.TFrame", background="lightcoral")
style.configure("Labels.TFrame", background="lightcoral", foreground="blue")

frame = tk.Frame(root, bg="lightcoral")
frame.pack(expand=True, fill="both", padx=10, pady=10)

# GUI layout

tk.Label(frame, text="Select Folder:", bg="lightcoral", fg="blue", font=("Arial", 14, "bold")).pack(pady=5)
tk.Entry(frame, textvariable=folder_var, width=60, bg="lightblue").pack(pady=5)
tk.Button(frame, text="Browse", command=choose_folder, bg="lightblue", font=("Arial", 12, "bold")).pack(pady=5)

frame_options = ttk.Frame(frame)
frame_options.pack(fill="x", pady=5)
frame_options.columnconfigure(0, weight=1)
frame_options.columnconfigure(1, weight=0)
frame_options.columnconfigure(2, weight=1)
ttk.Checkbutton(
    frame_options,
    text="Move to Parent",
    variable=move_to_parent_var,
    onvalue="1",
    offvalue="0",
    style="TCheckbutton"
).grid(row=0, column=1, padx=10, pady=2)

label_image_count = tk.Label(frame, text="No folder selected", bg="lightcoral", fg="blue", font=("Arial", 12, "bold"))
label_image_count.pack(pady=5)

frame_listbox = ttk.Frame(frame)
frame_listbox.pack(fill="both", expand=True, padx=10, pady=5)
listbox_folder_contents = tk.Listbox(frame_listbox, width=80, height=18, bg="lightblue", fg="blue")
listbox_folder_contents.pack(side="left", fill="both", expand=True)
scrollbar = ttk.Scrollbar(frame_listbox, orient="vertical", command=listbox_folder_contents.yview)
scrollbar.pack(side="right", fill="y")
listbox_folder_contents.config(yscrollcommand=scrollbar.set)

frame_progress = ttk.Frame(frame)
frame_progress.pack(fill="x", pady=5)
progress = ttk.Progressbar(frame_progress, orient="horizontal", length=300, mode="determinate")
progress.pack(fill="x", pady=5, padx=5, expand=True)

frame_labels = ttk.Frame(frame_progress)
frame_labels.pack(fill="x")
frame_left = ttk.Frame(frame_labels)
frame_left.pack(side="left", anchor="w")
frame_right = ttk.Frame(frame_labels)
frame_right.pack(side="right", anchor="e")
label_elapsed = tk.Label(frame_left, text="Elapsed: 0s", bg="lightcoral", fg="blue", font=("Arial", 12, "bold"))
label_elapsed.pack(anchor="w")
label_remaining = tk.Label(frame_left, text="Estimated remaining: --", bg="lightcoral", fg="blue", font=("Arial", 12, "bold"))
label_remaining.pack(anchor="w")
label_processed = tk.Label(frame_right, text="Processed: 0", bg="lightcoral", fg="blue", font=("Arial", 12, "bold"))
label_processed.pack(anchor="e")
label_total = tk.Label(frame_right, text="Total: --", bg="lightcoral", fg="blue", font=("Arial", 12, "bold"))
label_total.pack(anchor="e")

frame_buttons = ttk.Frame(frame)
frame_buttons.pack(fill="x", pady=10)
frame_buttons.columnconfigure(0, weight=1)
frame_buttons.columnconfigure(1, weight=0)
frame_buttons.columnconfigure(2, weight=1)
frame_buttons.columnconfigure(3, weight=0)
frame_buttons.columnconfigure(4, weight=1)
frame_buttons.columnconfigure(5, weight=0)
frame_buttons.columnconfigure(6, weight=1)

tk.Button(
    frame_buttons,
    text="Start",
    command=process_tree,
    width=7,
    bg="limegreen",
    activebackground="green2",
    font=("Arial", 12, "bold")
).grid(row=0, column=1, padx=10)
tk.Button(
    frame_buttons,
    textvariable=pause_continue_label,
    command=pause_or_continue,
    width=10,
    bg="gold",
    activebackground="yellow",
    font=("Arial", 12, "bold")
).grid(row=0, column=3, padx=10)
tk.Button(
    frame_buttons,
    text="Exit",
    command=confirm_close,
    width=7,
    bg="red",
    activebackground="darkred",
    font=("Arial", 12, "bold")
).grid(row=0, column=5, padx=10)

# Load settings on startup
load_settings()

root.mainloop()