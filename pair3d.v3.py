# pair3d.py
# Copyright (c) 2025 tiMaxal
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
pair3d

A utility for sorting stereo image pairs in a folder and optionally moving them to a duplicated structure.
Pairs are detected based on file modification timestamps and perceptual image similarity.
Pairs are moved into a '_pairs' subfolder, and unpaired images into a '_singles' subfolder.
After sorting, optionally moves '_pairs' files to their immediate parent in the '_x2_[folder]' structure
with '_pairs' suffix, and '_singles' files to their immediate parent in the source tree.
The source folder is renamed to '[source]_singles'.
A simple GUI picker allows users to select a folder, configure options, and view results.
"""

import sys
import os
import shutil
import threading
import time
from tkinter import filedialog, messagebox, Tk, Label, Button, Listbox, END, StringVar
from tkinter import ttk
from datetime import datetime
from PIL import Image
import imagehash
import json

TIME_DIFF_THRESHOLD = 2
HASH_DIFF_THRESHOLD = 10

def get_app_dir():
    """
    Get the application directory for storing settings and logs.
    """
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        if os.access(exe_dir, os.W_OK):
            return exe_dir
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if os.access(script_dir, os.W_OK):
        return script_dir
    config_dir = os.path.expanduser("~/.config/pair3d")
    os.makedirs(config_dir, exist_ok=True)
    return config_dir

SETTINGS_FILE = os.path.join(get_app_dir(), "pair3d_settings.json")

def load_last_folder():
    """
    Load the last used folder path from the settings file.
    """
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            settings = json.load(f)
            folder = settings.get("last_folder", "")
            if folder and os.path.isdir(folder):
                return folder
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def save_last_folder(folder):
    """
    Save the given folder path to the settings file.
    """
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump({"last_folder": folder}, f)
    except Exception as e:
        print(f"Failed to save settings: {e}")

def get_image_files(directory, recursive=False, include_singles=False):
    """
    Retrieve a list of image file paths from the given directory.
    """
    image_files = []
    if not os.path.exists(directory):
        return image_files
    if recursive:
        for root, dirs, files in os.walk(directory):
            skip_folders = ["_pairs"]
            if not include_singles:
                skip_folders.append("_singles")
            dirs[:] = [d for d in dirs if d not in skip_folders]
            for f in files:
                if f.lower().endswith((".jpg", ".jpeg", ".png")):
                    image_files.append(os.path.join(root, f))
    else:
        image_files = [
            os.path.join(directory, f)
            for f in os.listdir(directory)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
            and os.path.isfile(os.path.join(directory, f))
        ]
    return image_files

def get_image_files_by_folder(directory, recursive=False, include_singles=False):
    """
    Retrieve image files grouped by folder.
    """
    folders = {}
    if not os.path.exists(directory):
        return folders
    if recursive:
        for root, dirs, files in os.walk(directory):
            skip_folders = ["_pairs"]
            if not include_singles:
                skip_folders.append("_singles")
            dirs[:] = [d for d in dirs if d not in skip_folders]
            image_files = [
                os.path.join(root, f)
                for f in files
                if f.lower().endswith((".jpg", ".jpeg", ".png"))
            ]
            if image_files:
                folders[root] = image_files
    else:
        folders[directory] = get_image_files(directory, recursive=False, include_singles=include_singles)
    return folders

def get_image_timestamp(path):
    """
    Get the modification timestamp of an image file.
    """
    try:
        return datetime.fromtimestamp(os.path.getmtime(path))
    except Exception:
        return None

def is_similar_image(file1, file2):
    """
    Determine if two images are perceptually similar using phash.
    """
    try:
        with Image.open(file1) as img1, Image.open(file2) as img2:
            hash1 = imagehash.phash(img1)
            hash2 = imagehash.phash(img2)
        return abs(hash1 - hash2) < HASH_DIFF_THRESHOLD
    except Exception:
        return False

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
            try:
                shutil.move(src_item, dst_item)
            except FileNotFoundError:
                pass
    delete_if_empty(src_dir)

def confirm_close(root, progress):
    """
    Confirm close if processing is in progress.
    """
    if 0 < progress["value"] < 100:
        if not messagebox.askyesno("Work in progress", "Are you sure you want to close?"):
            return
    root.destroy()

def main():
    """
    Launch the Tkinter GUI for sorting stereo image pairs and optionally moving them.
    """
    root = Tk()
    root.title("pair3d - Stereo Image Sorter")
    root.configure(bg="lightcoral")
    root.tk_setPalette(background="lightcoral", foreground="blue")
    root.geometry("600x800")
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - 600) // 2
    y = (screen_height - 800) // 2
    root.geometry(f"+{x}+{y}")
    default_font = ("Arial", 12, "bold")
    root.option_add("*Font", default_font)

    # Set window icon if available
    icon_path = os.path.join(os.path.dirname(__file__), "imgs/pair3d.ico")
    if os.path.exists(icon_path):
        root.iconbitmap(icon_path)

    selected_folder = {"path": load_last_folder()}
    style = ttk.Style()
    style.configure("TCheckbutton", background="lightcoral", foreground="blue")
    style.configure("TRadiobutton", background="lightcoral", foreground="blue")
    style.configure("TFrame", background="lightcoral")
    style.configure("Progress.TFrame", background="lightcoral")
    style.configure("Labels.TFrame", background="lightcoral", foreground="blue")

    # GUI Layout
    label = Label(
        root,
        text="Select folder[s] containing images to sort:",
        bg="lightcoral",
        fg="blue",
        font=("Arial", 14, "bold"),
    )
    label.pack(pady=10)

    frame_folder = ttk.Frame(root)
    frame_folder.pack(fill="x", padx=10)
    label_selected_folder = Label(
        frame_folder,
        text=selected_folder["path"] if selected_folder["path"] else "No folder selected",
        fg="blue" if selected_folder["path"] else "gray",
        bg="lightcoral",
    )
    label_selected_folder.pack(side="left", fill="x", expand=True)
    button_browse = Button(
        frame_folder, text="Browse", command=lambda: browse_folder(), bg="lightblue"
    )
    button_browse.pack(side="right", padx=5, pady=5)

    frame_folder_options = ttk.Frame(root)
    frame_folder_options.pack(pady=5, fill="x")
    frame_folder_options.columnconfigure(0, weight=1)
    frame_folder_options.columnconfigure(1, weight=0)
    frame_folder_options.columnconfigure(2, weight=1)
    frame_folder_options.columnconfigure(3, weight=0)
    frame_folder_options.columnconfigure(4, weight=1)

    process_subfolders_var = StringVar(value="0")
    check_subfolders = ttk.Checkbutton(
        frame_folder_options,
        text="Process subfolders",
        variable=process_subfolders_var,
        onvalue="1",
        offvalue="0",
        command=lambda: update_folder_contents_listbox()
    )
    check_subfolders.grid(row=0, column=1, padx=10, pady=2)

    reprocess_singles_var = StringVar(value="0")
    check_reprocess_singles = ttk.Checkbutton(
        frame_folder_options,
        text="Include '_singles' folders",
        variable=reprocess_singles_var,
        onvalue="1",
        offvalue="0",
        command=lambda: update_folder_contents_listbox()
    )
    check_reprocess_singles.grid(row=1, column=1, padx=10, pady=2)

    move_to_x2_var = StringVar(value="0")
    check_move_to_x2 = ttk.Checkbutton(
        frame_folder_options,
        text="Move to '_x2_[folder]'",
        variable=move_to_x2_var,
        onvalue="1",
        offvalue="0",
        command=lambda: update_radio_state()
    )
    check_move_to_x2.grid(row=0, column=3, padx=10, pady=2)

    frame_radio = ttk.Frame(frame_folder_options)
    frame_radio.grid(row=1, column=3, padx=10, pady=2, sticky="w")
    move_destination_var = StringVar(value="root")
    radio_to_root = ttk.Radiobutton(
        frame_radio,
        text="To root",
        value="root",
        variable=move_destination_var,
        state="disabled"
    )
    radio_to_root.pack(anchor="w")
    radio_to_subdirs = ttk.Radiobutton(
        frame_radio,
        text="To subdir's",
        value="subdirs",
        variable=move_destination_var,
        state="disabled"
    )
    radio_to_subdirs.pack(anchor="w")

    def update_radio_state():
        """
        Enable/disable radio buttons based on checkbox states.
        """
        move_to_x2 = move_to_x2_var.get() == "1"
        process_subfolders = process_subfolders_var.get() == "1"
        state = "normal" if move_to_x2 and process_subfolders else "disabled"
        radio_to_root.config(state=state)
        radio_to_subdirs.config(state=state)

    process_subfolders_var.trace("w", lambda *args: update_radio_state())
    move_to_x2_var.trace("w", lambda *args: update_radio_state())

    label_image_count = Label(root, text="No folder selected", bg="lightcoral", fg="blue")
    label_image_count.pack(pady=5)

    frame_thresholds = ttk.Frame(root)
    frame_thresholds.pack(pady=5, fill="x")
    frame_thresholds.columnconfigure(0, weight=1)
    frame_thresholds.columnconfigure(1, weight=0)
    frame_thresholds.columnconfigure(2, weight=0)
    frame_thresholds.columnconfigure(3, weight=1)
    frame_thresholds.columnconfigure(4, weight=0)
    frame_thresholds.columnconfigure(5, weight=0)
    frame_thresholds.columnconfigure(6, weight=1)

    Label(frame_thresholds, text="Time diff (s):", bg="lightcoral", fg="blue").grid(
        row=0, column=1, padx=(0, 2), pady=2, sticky="e"
    )
    time_diff_var = StringVar(value=str(TIME_DIFF_THRESHOLD))
    entry_time_diff = ttk.Entry(frame_thresholds, textvariable=time_diff_var, width=5)
    entry_time_diff.grid(row=0, column=2, padx=(0, 10), pady=2, sticky="w")
    entry_time_diff.configure(background="lightblue", foreground="blue")

    Label(frame_thresholds, text="Hash diff:", bg="lightcoral", fg="blue").grid(
        row=0, column=4, padx=(0, 2), pady=2, sticky="e"
    )
    hash_diff_var = StringVar(value=str(HASH_DIFF_THRESHOLD))
    entry_hash_diff = ttk.Entry(frame_thresholds, textvariable=hash_diff_var, width=5)
    entry_hash_diff.grid(row=0, column=5, padx=(0, 0), pady=2, sticky="w")
    entry_hash_diff.configure(background="lightblue", foreground="blue")

    def update_thresholds():
        global TIME_DIFF_THRESHOLD, HASH_DIFF_THRESHOLD
        try:
            TIME_DIFF_THRESHOLD = max(0.01, float(time_diff_var.get()))
        except Exception as e:
            print(f"[Warning] Invalid time diff input, keeping previous: {e}")
        try:
            HASH_DIFF_THRESHOLD = max(1, int(hash_diff_var.get()))
        except Exception as e:
            print(f"[Warning] Invalid hash diff input, keeping previous: {e}")
        print(f"[Info] Using thresholds: Time = {TIME_DIFF_THRESHOLD}, Hash = {HASH_DIFF_THRESHOLD}")

    entry_time_diff.bind("<FocusOut>", lambda e: update_thresholds())
    entry_time_diff.bind("<Return>", lambda e: update_thresholds())
    entry_hash_diff.bind("<FocusOut>", lambda e: update_thresholds())
    entry_hash_diff.bind("<Return>", lambda e: update_thresholds())

    frame_listbox = ttk.Frame(root)
    frame_listbox.pack(fill="both", expand=True, padx=10, pady=5)
    listbox_folder_contents = Listbox(
        frame_listbox, width=80, height=10, bg="lightblue", fg="blue"
    )
    listbox_folder_contents.pack(side="left", fill="both", expand=True)
    scrollbar_folder = ttk.Scrollbar(
        frame_listbox, orient="vertical", command=listbox_folder_contents.yview
    )
    scrollbar_folder.pack(side="right", fill="y")
    listbox_folder_contents.config(yscrollcommand=scrollbar_folder.set)

    listbox_results = Listbox(root, width=30, height=3, bg="lightblue", fg="blue")
    listbox_results.pack(pady=10)

    frame_progress = ttk.Frame(root)
    frame_progress.pack(pady=5, fill="x")
    progress = ttk.Progressbar(
        frame_progress, orient="horizontal", length=300, mode="determinate"
    )
    progress.pack(fill="x", pady=5, padx=5, expand=True)

    frame_labels = ttk.Frame(frame_progress)
    frame_labels.pack(fill="x")
    frame_left = ttk.Frame(frame_labels)
    frame_left.pack(side="left", anchor="w")
    frame_right = ttk.Frame(frame_labels)
    frame_right.pack(side="right", anchor="e")
    label_elapsed = Label(
        frame_left, text="Elapsed: 0s", bg="lightcoral", fg="blue"
    )
    label_elapsed.pack(anchor="w")
    label_remaining = Label(
        frame_left, text="Estimated remaining: --", bg="lightcoral", fg="blue"
    )
    label_remaining.pack(anchor="w")
    label_processed = Label(
        frame_right, text="Processed: 0", bg="lightcoral", fg="blue"
    )
    label_processed.pack(anchor="e")
    label_total = Label(
        frame_right, text="Total: --", bg="lightcoral", fg="blue"
    )
    label_total.pack(anchor="e")

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

    def update_folder_contents_listbox():
        """
        Update the Listbox to show images grouped by subfolder.
        """
        listbox_folder_contents.delete(0, END)
        folder = selected_folder["path"]
        if not folder:
            return
        try:
            recursive = process_subfolders_var.get() == "1"
            include_singles = reprocess_singles_var.get() == "1"
            folders_dict = get_image_files_by_folder(
                folder, recursive=recursive, include_singles=include_singles
            )
            total_images = sum(len(files) for files in folders_dict.values())
            label_image_count.config(text=f"Total images found: {total_images}")
            for subfolder, files in sorted(folders_dict.items()):
                rel_subfolder = os.path.relpath(subfolder, folder)
                listbox_folder_contents.insert(END, f"[{rel_subfolder}]")
                for f in sorted(files):
                    listbox_folder_contents.insert(END, f"    {os.path.basename(f)}")
        except Exception as e:
            label_image_count.config(text="Error reading folder")
            listbox_folder_contents.insert(END, f"Error: {e}")

    def browse_folder():
        """
        Handle folder selection and update the UI.
        """
        initialdir = selected_folder["path"] if selected_folder["path"] else None
        folder = filedialog.askdirectory(initialdir=initialdir)
        if folder:
            selected_folder["path"] = folder
            save_last_folder(folder)
            label_selected_folder.config(text=folder, fg="blue")
            listbox_results.delete(0, END)
            update_progress(0, 0, None, 0, None)
            update_folder_contents_listbox()

    def start_sorting():
        """
        Perform image sorting and optional moving to a duplicated structure.
        """
        folder = selected_folder["path"]
        if not folder:
            messagebox.showerror("No folder selected", "Please select a folder before starting.")
            return
        update_thresholds()

        app_log_file = os.path.join(get_app_dir(), "pair3d_log.txt")
        src_log_file = os.path.join(folder, "pair3d_log.txt")

        def log(msg):
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_message = f"[{timestamp}] {msg}\n"
            try:
                with open(app_log_file, "a", encoding="utf-8") as f:
                    f.write(log_message)
            except Exception as e:
                print(f"Failed to write to app log: {e}")
            try:
                with open(src_log_file, "a", encoding="utf-8") as f:
                    f.write(log_message)
            except Exception as e:
                print(f"Failed to write to source log: {e}")

        def task():
            start_time = time.time()
            include_singles = reprocess_singles_var.get() == "1"
            folders_dict = get_image_files_by_folder(
                folder, recursive=(process_subfolders_var.get() == "1"), include_singles=include_singles
            )
            image_files = [f for files in folders_dict.values() for f in files]
            total_files = len(image_files)
            root.after(0, update_progress, 0, 0, None, 0, total_files)

            processed = [0]
            def progress_callback(value):
                now = time.time()
                elapsed = max(0, now - start_time - total_paused_time[0])
                processed_count = int((value / 100) * total_files)
                processed[0] = processed_count
                remaining = ((elapsed / value) * (100 - value)) if value > 0 else -1
                root.after(0, update_progress, value, elapsed, remaining, processed_count, total_files)

            # Sorting Phase
            image_files.sort(key=lambda x: get_image_timestamp(x) or datetime.min)
            used = set()
            pairs = []
            for i, path1 in enumerate(image_files):
                if path1 in used:
                    continue
                time1 = get_image_timestamp(path1)
                if time1 is None:
                    continue
                for path2 in image_files[i+1:]:
                    if path2 in used:
                        continue
                    time2 = get_image_timestamp(path2)
                    if time2 and abs((time2 - time1).total_seconds()) <= TIME_DIFF_THRESHOLD:
                        if is_similar_image(path1, path2):
                            pairs.append((path1, path2))
                            used.add(path1)
                            used.add(path2)
                            break
                while not pause_event.is_set():
                    time.sleep(0.1)
                progress_callback(min(100, int((i / len(image_files)) * 100)))

            # Move files to _pairs or _singles
            for pair in pairs:
                for file in pair:
                    subdir = os.path.dirname(file)
                    dest_dir = os.path.join(subdir, "_pairs")
                    os.makedirs(dest_dir, exist_ok=True)
                    try:
                        shutil.move(file, os.path.join(dest_dir, os.path.basename(file)))
                    except FileNotFoundError:
                        pass

            for file in image_files:
                if file not in used:
                    subdir = os.path.dirname(file)
                    if os.path.basename(subdir) == "_singles":
                        continue
                    dest_dir = os.path.join(subdir, "_singles")
                    os.makedirs(dest_dir, exist_ok=True)
                    try:
                        shutil.move(file, os.path.join(dest_dir, os.path.basename(file)))
                    except FileNotFoundError:
                        pass

            num_pairs = len(pairs)
            num_singles = len(image_files) - len(used)
            root.after(0, listbox_results.delete, 0, END)
            root.after(0, listbox_results.insert, END, f"Pairs moved: {num_pairs}")
            root.after(0, listbox_results.insert, END, f"Singles moved: {num_singles}")

            # Moving Phase (if enabled)
            if move_to_x2_var.get() == "1":
                src_root = folder
                base_name = os.path.basename(src_root)
                if base_name.endswith("_singles"):
                    if not messagebox.askyesno(
                        "Warning",
                        f"Source folder '{src_root}' ends with '_singles', indicating it may have been processed before. Continue?"
                    ):
                        root.after(0, update_progress, 100, time.time() - start_time, 0, total_files, total_files)
                        root.after(0, messagebox.showinfo, "Done", f"Sorted {num_pairs} pairs and {num_singles} singles.")
                        return

                parent_dir = os.path.dirname(src_root)
                dst_root = os.path.join(parent_dir, f"_x2_{base_name}")
                singles_root = os.path.join(parent_dir, f"{base_name}_singles")

                if os.path.exists(dst_root):
                    if not messagebox.askyesno("Destination Exists", f"Destination '{dst_root}' already exists. Overwrite?"):
                        root.after(0, update_progress, 100, time.time() - start_time, 0, total_files, total_files)
                        root.after(0, messagebox.showinfo, "Done", f"Sorted {num_pairs} pairs and {num_singles} singles.")
                        return
                    try:
                        shutil.rmtree(dst_root)
                    except Exception as e:
                        log(f"Failed to remove existing destination: {e}")
                        root.after(0, messagebox.showerror, "Error", f"Failed to remove existing destination: {e}")
                        return

                os.makedirs(dst_root)
                log(f"Processing from: {src_root}")
                log(f"Duplicated tree will be at: {dst_root}")

                for dirpath, _, _ in os.walk(src_root, topdown=False):
                    # Count files before moving
                    file_count = len(get_image_files(dirpath, include_singles=True))
                    rel_path = os.path.relpath(dirpath, src_root)
                    parent_path = os.path.dirname(dirpath)
                    parent_rel = os.path.relpath(parent_path, src_root)
                    if os.path.basename(dirpath) == '_pairs':
                        # Move _pairs to immediate parent in dst_root with _pairs suffix
                        pair_dest = os.path.join(dst_root, parent_rel, f"{os.path.basename(parent_path)}_pairs") if parent_rel != '.' else os.path.join(dst_root, f"{base_name}_pairs")
                        log(f"Moving from _pairs: {dirpath} → {pair_dest}")
                        move_contents(dirpath, pair_dest)
                        processed[0] += file_count
                        progress_callback(min(100, int((processed[0] / total_files) * 100) if total_files else 100))

                    elif os.path.basename(dirpath) == '_singles':
                        # Move _singles to immediate parent in source tree
                        single_dest = src_root if parent_rel == '.' else parent_path
                        log(f"Moving from _singles: {dirpath} → {single_dest}")
                        move_contents(dirpath, single_dest)
                        processed[0] += file_count
                        progress_callback(min(100, int((processed[0] / total_files) * 100) if total_files else 100))

                    delete_if_empty(dirpath)
                    while not pause_event.is_set():
                        time.sleep(0.1)

                try:
                    if os.path.exists(singles_root):
                        log(f"Warning: '{singles_root}' already exists, merging contents")
                        move_contents(src_root, singles_root)
                        shutil.rmtree(src_root)
                    else:
                        os.rename(src_root, singles_root)
                    log(f"Renamed source root: {src_root} → {singles_root}")
                    root.after(0, lambda: selected_folder.update({"path": singles_root}))
                    save_last_folder(singles_root)
                except Exception as e:
                    log(f"Failed to rename source root to {singles_root}: {e}")
                    root.after(0, messagebox.showerror, "Error", f"Failed to rename source root to {singles_root}: {e}")

                log(f"Done. Primary log saved at: {app_log_file}, Source log saved at: {singles_root}/pair3d_log.txt")
                root.after(0, listbox_results.insert, END, f"Moved to: {dst_root}")
                root.after(0, listbox_results.insert, END, f"Source renamed to: {singles_root}")

            elapsed = time.time() - start_time
            root.after(0, update_progress, 100, elapsed, 0, total_files, total_files)
            completion_message = f"Sorted {num_pairs} pairs and {num_singles} singles."
            if move_to_x2_var.get() == "1":
                completion_message += f"\nMoved to: {dst_root}\nSource renamed to: {singles_root}\nPrimary log: {app_log_file}"
            root.after(0, messagebox.showinfo, "Done", completion_message)

        pause_event.set()
        threading.Thread(target=task, daemon=True).start()

    frame_buttons = ttk.Frame(root)
    frame_buttons.pack(fill="x", pady=10)
    frame_buttons.columnconfigure(0, weight=1)
    frame_buttons.columnconfigure(1, weight=0)
    frame_buttons.columnconfigure(2, weight=1)
    frame_buttons.columnconfigure(3, weight=0)
    frame_buttons.columnconfigure(4, weight=1)
    frame_buttons.columnconfigure(5, weight=0)
    frame_buttons.columnconfigure(6, weight=1)

    button_start = Button(
        frame_buttons,
        text="Start",
        command=start_sorting,
        width=7,
        bg="limegreen",
        activebackground="green2"
    )
    button_start.grid(row=0, column=1, padx=10)

    pause_event = threading.Event()
    pause_event.set()
    pause_continue_label = StringVar(value="Pause")
    pause_start_time = [None]
    total_paused_time = [0]

    def pause_or_continue():
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

    button_pause = Button(
        frame_buttons,
        textvariable=pause_continue_label,
        command=pause_or_continue,
        width=10,
        bg="gold",
        activebackground="yellow"
    )
    button_pause.grid(row=0, column=3, padx=10)

    button_close = Button(
        frame_buttons,
        text="Exit",
        command=lambda: confirm_close(root, progress),
        width=7,
        bg="red",
        activebackground="darkred"
    )
    button_close.grid(row=0, column=5, padx=10)

    root.mainloop()

if __name__ == "__main__":
    main()