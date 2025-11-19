# pair3d.v1-3.py
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

A utility for sorting stereo image pairs in a folder.
Pairs are detected based on file modification timestamps and perceptual image similarity.
Pairs are moved into a '_pairs' subfolder, and unpaired images into a 'singles' subfolder.
A simple GUI picker allows users to select a folder and view results.

    =====

vibe-coded 'voded' from original ai prompt [chatgpt 'getting to know you' 20250624] with perplexity-ai, and copilot-ai:

 "a way to separate pairs from folders also containing singles .. software that compares for image-similarity and closeness of time-created"

"""

import sys, os
import shutil
import threading
import time
from tkinter import filedialog, messagebox, Tk, Label, Button, Listbox, END, StringVar
from tkinter import ttk
from datetime import datetime
from PIL import Image
import imagehash

# Ensure the base directory exists
if getattr(sys, 'frozen', False):
    # Running as bundled .exe
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SETTINGS_FILE = os.path.join(BASE_DIR, "settings.txt")

TIME_DIFF_THRESHOLD = 2
HASH_DIFF_THRESHOLD = 10

def load_last_folder():
    """
    Load the last used folder path from the settings file.
    Returns:
        str or None: The last used folder path, or None if not set.
    """
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                folder = f.read().strip()
                if folder and os.path.isdir(folder):
                    return folder
        except Exception:
            pass
    return None


def save_last_folder(folder):
    """
    Save the given folder path to the settings file.
    Args:
        folder (str): The folder path to save.
    """
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            f.write(folder)
    except Exception:
        pass


def get_image_files(directory, recursive=False):
    """
    Retrieve a list of image file paths from the given directory (and optionally subdirectories),
    skipping any '_pairs' or '_singles' folders.

    Args:
        directory (str): Path to the directory to search.
        recursive (bool): Whether to include image files from subdirectories.

    Returns:
        list: List of image file paths with extensions .jpg, .jpeg, or .png.
    """
    image_files = []
    if recursive:
        for root, dirs, files in os.walk(directory):
            # Skip '_pairs' and '_singles' folders
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
    Retrieve image files grouped by folder. When recursive is True,
    returns a dictionary mapping each folder path to its own list of image files.

    Skips '_pairs' and '_singles' folders.

    Args:
        directory (str): Root directory.
        recursive (bool): Whether to include subfolders.

    Returns:
        dict: Mapping from folder path to list of image file paths.
    """
    folders = {}
    if recursive:
        for root, dirs, files in os.walk(directory):
            # Skip '_pairs' and optionally '_singles' folders
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
        folders[directory] = get_image_files(directory, recursive=False)
    return folders


def get_image_timestamp(path):
    """
    Get the modification timestamp of an image file.

    Args:
        path (str): Path to the image file.

    Returns:
        datetime or None: Modification time as a datetime object, or None if unavailable.
    """
    try:
        return datetime.fromtimestamp(os.path.getmtime(path))
    except Exception:
        return None


def is_similar_image(file1, file2):
    """
    Determine if two images are perceptually similar using phash.

    Args:
        file1 (str): Path to the first image.
        file2 (str): Path to the second image.

    Returns:
        bool: True if images are similar within the hash threshold, False otherwise.
    """
    try:
        with Image.open(file1) as img1, Image.open(file2) as img2:
            hash1 = imagehash.phash(img1)
            hash2 = imagehash.phash(img2)
        print("HASH_DIFF_THRESHOLD used:", HASH_DIFF_THRESHOLD)  # Debug
        return abs(hash1 - hash2) < HASH_DIFF_THRESHOLD
    except Exception:
        return False


# Confirm close if work in progress
def confirm_close(root, progress):
    if 0 < progress["value"] < 100:
        if not messagebox.askyesno(
            "Work in progress:",
            " Are you sure you want to close?",
        ):
            return
    root.destroy()


def main():
    """
    Launch the Tkinter GUI for selecting a folder and sorting stereo image pairs.
    The color theme is loosely based on the red+cyan spectacles used to view anaglyph stereo images.
    The interface provides:
    - A label to prompt folder selection.
    - A label to display the currently selected folder path.
    - A 'Browse' button to choose a directory containing image files.
    - A checkbox to enable processing of subfolders.
    - A checkbox to allow re-processing of '_singles' folders.
    - Displays the contents of the selected folder[s] in a Listbox,
        [allow to assess whether the folder needs processing.]
    - A 'Start' button to commence sorting after a folder is selected.
    - A progress bar that updates as image pairs are processed.
    - Elapsed time [left], processed count [right],
        and estimated time remaining [left, below elapsed]
            and total file count [right, below processed] are displayed.
    - A 'Pause' button to suspend processing.
    - A listbox to display the result counts for pairs and singles.
    - An 'Exit' button to close the app, with alert warning [tied to unfinished progress bar].
    """
    root = Tk()
    root.resizable(True, True)
    root.title("pair3d - Stereo Image Sorter")

    # Set app background color
    root.configure(bg="lightcoral")
    root.tk_setPalette(background="lightcoral", foreground="blue")

    # Set default font for all widgets
    default_font = ("Arial", 12, "bold")
    root.option_add("*Font", default_font)
    
    # Set window size
    root.geometry("600x800")
    
    # Center the window on the screen
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - 800) // 4
    y = (screen_height - 600) // 4
    root.geometry(f"+{x}+{y}")
        
    # Set minimum window size
    #root.minsize(600, 600)
    
    # Set maximum window size
    #root.maxsize(1200, 1600)
    
    # Set window title
    root.title("pair3d - Stereo Image Sorter")

    # Set window background color
    root.configure(bg="lightcoral")

    # Set window icon if available
    icon_path = os.path.join(os.path.dirname(__file__), "imgs/pair3d.ico")
    if os.path.exists(icon_path):
        root.iconbitmap(icon_path)

    # Set default font for all widgets
    default_font = ("Arial", 12)
    root.option_add("*Font", default_font)

    # Store selected folder path using a mutable object, initialized from settings
    selected_folder = {"path": load_last_folder()}

    # Prompt text
    label = Label(root, text="Select folder[s] containing images to sort:", bg="lightcoral", fg="blue", font=("Arial", 14, "bold"))
    label.pack(pady=10)

    # Display selected folder (show last folder if available)
    init_folder = selected_folder["path"]

    # Frame for folder label and browse button side by side
    frame_folder = ttk.Frame(root)
    frame_folder.pack(fill="x", padx=10)

    label_selected_folder = Label(
        frame_folder,
        text=init_folder if init_folder else "No folder selected",
        fg="black" if init_folder else "gray",
        bg="lightcoral",
    )
    label_selected_folder.pack(side="left", fill="x", expand=True)

    def browse_folder():
        """
        Handle folder selection via file dialog and update the UI.
        Displays the contents of the selected folder in a Listbox.
        Remembers the last used folder across sessions.
        """
        initialdir = selected_folder["path"] if selected_folder["path"] else None
        folder = filedialog.askdirectory(initialdir=initialdir)
        if folder:
            selected_folder["path"] = folder
            save_last_folder(folder)
            label_selected_folder.config(text=folder, fg="blue")
            listbox_results.delete(0, END)
            progress["value"] = 0
            label_elapsed.config(text="Elapsed: 0s")
            label_remaining.config(text="Estimated remaining: --")
            label_processed.config(text="Processed: 0")
            label_total.config(text="Total: --")
            update_folder_contents_listbox()  # Update listbox with folder contents
            # Show folder contents
            recursive = process_subfolders_var.get() == "1"
            include_singles = reprocess_singles_var.get() == "1"
            try:
                folders_dict = get_image_files_by_folder(folder, recursive=recursive, include_singles=include_singles)
                for subfolder, files in sorted(folders_dict.items()):
                    # Show subfolder name (relative to root)
                    rel_subfolder = os.path.relpath(subfolder, folder)
                    listbox_folder_contents.insert(END, f"[{rel_subfolder}]")
                    for f in sorted(files):
                        listbox_folder_contents.insert(
                            END, f"    {os.path.basename(f)}"
                        )
            except Exception as e:
                listbox_folder_contents.insert(END, f"Error: {e}")

    # Folder selection button (Browse) on the right of the label
    button_browse = Button(frame_folder, text="Browse", command=browse_folder, bg="lightblue")
    button_browse.pack(side="right", padx=5, pady=5)

    # --- Folder Checkboxes: subfolders | reprocess singles ---
    frame_folder_options = ttk.Frame(root)
    frame_folder_options.pack(pady=5, fill="x")

    # Configure columns for centering
    frame_folder_options.columnconfigure(0, weight=1)  # left spacer
    frame_folder_options.columnconfigure(1, weight=0)  # first checkbox
    frame_folder_options.columnconfigure(2, weight=1)  # middle spacer
    frame_folder_options.columnconfigure(3, weight=0)  # second checkbox
    frame_folder_options.columnconfigure(4, weight=1)  # right spacer

    # Set background for ttk.Checkbutton via style
    style = ttk.Style()
    frame_folder_options.configure(style="FolderOptions.TFrame")
    style.configure("TCheckbutton", background="lightcoral")
    style.configure("TCheckbutton", foreground="blue")
    style.configure("TFrame", background="lightcoral")
    style.configure("FolderOptions.TFrame", background="lightcoral")

    # Checkbox for processing subfolders
    process_subfolders_var = StringVar(value="0")
    check_subfolders = ttk.Checkbutton(
        frame_folder_options,
        text="Process subfolders",
        variable=process_subfolders_var,
        onvalue="1",
        offvalue="0",
        command=None,  # will assign after defining update function
    )
    check_subfolders.grid(row=0, column=1, padx=10, pady=2)

    # Checkbox to allow re-processing '_singles' folders
    reprocess_singles_var = StringVar(value="0")
    check_reprocess_singles = ttk.Checkbutton(
        frame_folder_options,
        text="Include '_singles' folders",
        variable=reprocess_singles_var,
        onvalue="1",
        offvalue="0"
    )
    check_reprocess_singles.grid(row=0, column=3, padx=10, pady=2)

    # Label to show total image count
    label_image_count = Label(root, text="No folder selected")
    label_image_count.pack()

    # --- Threshold controls ---
    frame_thresholds = ttk.Frame(root)
    frame_thresholds.pack(pady=5, fill="x")
    frame_thresholds.configure(style="Thresholds.TFrame")
    style.configure("Thresholds.TFrame", background="lightcoral")
    
    # Configure columns for centering
    frame_thresholds.columnconfigure(0, weight=1)  # left spacer
    frame_thresholds.columnconfigure(1, weight=0)  # label: Time diff
    frame_thresholds.columnconfigure(2, weight=0)  # entry: Time diff
    frame_thresholds.columnconfigure(3, weight=1)  # middle spacer
    frame_thresholds.columnconfigure(4, weight=0)  # label: Hash diff
    frame_thresholds.columnconfigure(5, weight=0)  # entry: Hash diff
    frame_thresholds.columnconfigure(6, weight=1)  # right spacer

    # Time difference threshold
    Label(
        frame_thresholds,
        text="Time diff (s):",
        font=("Arial", 12, "bold")).grid(row=0, column=1, padx=(0,2), pady=2, sticky="e"
        )
    time_diff_var = StringVar(value=str(TIME_DIFF_THRESHOLD))
    entry_time_diff = ttk.Entry(frame_thresholds, textvariable=time_diff_var, width=5)
    entry_time_diff.grid(row=0, column=2, padx=(0, 10), pady=2, sticky="w")
    entry_time_diff.configure(background="lightblue",foreground="blue")

    # Bind events to update threshold live
    entry_time_diff.bind("<FocusOut>", lambda e: update_thresholds())
    entry_time_diff.bind("<Return>", lambda e: update_thresholds())

    # Hash difference threshold
    Label(
        frame_thresholds,
        text="Hash diff:",
        font=("Arial", 12, "bold")).grid(row=0, column=4, padx=(0,2), pady=2, sticky="e"
)
    hash_diff_var = StringVar(value=str(HASH_DIFF_THRESHOLD))
    entry_hash_diff = ttk.Entry(frame_thresholds, textvariable=hash_diff_var, width=5)
    entry_hash_diff.grid(row=0, column=5, padx=(0,0), pady=2, sticky="w")
    entry_hash_diff.configure(background="lightblue", foreground="blue")

    # Bind events to update threshold live
    entry_hash_diff.bind("<FocusOut>", lambda e: update_thresholds())
    entry_hash_diff.bind("<Return>", lambda e: update_thresholds())

    # Update thresholds before sorting
    def update_thresholds():
        global TIME_DIFF_THRESHOLD, HASH_DIFF_THRESHOLD
        try:
            val = float(time_diff_var.get())
            TIME_DIFF_THRESHOLD = max(0.01, val)
        except Exception as e:
            print("[Warning] Invalid time diff input, keeping previous:", e)

        try:
            val = int(hash_diff_var.get())
            HASH_DIFF_THRESHOLD = max(1, val)
        except Exception as e:
            print("[Warning] Invalid hash diff input, keeping previous:", e)

        print(f"[Info] Using thresholds: Time = {TIME_DIFF_THRESHOLD}, Hash = {HASH_DIFF_THRESHOLD}")

    # Listbox and Scrollbar to show folder contents
    frame_listbox = ttk.Frame(root)
    frame_listbox.pack(fill="both", expand=True, padx=10, pady=5)

    listbox_folder_contents = Listbox(frame_listbox, width=80, height=18, bg="lightblue", fg="blue")
    listbox_folder_contents.pack(side="left", fill="both", expand=True)

    scrollbar_folder = ttk.Scrollbar(
        frame_listbox, orient="vertical", command=listbox_folder_contents.yview
    )
    scrollbar_folder.pack(side="right", fill="y")

    listbox_folder_contents.config(yscrollcommand=scrollbar_folder.set)

    # Display results
    listbox_results = Listbox(root, width=30, height=3, bg="lightblue", fg="blue")
    listbox_results.pack(pady=10)

    # Function to update the Listbox with folder contents
    def update_folder_contents_listbox():
        """
        Update the Listbox to show images grouped by subfolder if 'Process subfolders' is checked.
        """
        listbox_folder_contents.delete(0, END)
        folder = selected_folder["path"]
        if not folder:
            return
        try:
            recursive = process_subfolders_var.get() == "1"
            include_singles = reprocess_singles_var.get() == "1"
            folders_dict = get_image_files_by_folder(folder, recursive=recursive, include_singles=include_singles)
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

    # Callback for the checkbox
    check_subfolders.config(command=update_folder_contents_listbox)

    # --- Progress bar and info frame ---
    frame_progress = ttk.Frame(root)
    frame_progress.pack(pady=5, fill="x")
    frame_progress.configure(style="Progress.TFrame")
    style.configure("Progress.TFrame", background="lightcoral")

    # Elapsed/remaining on left, processed/total on right
    frame_labels = ttk.Frame(frame_progress)
    frame_labels.pack(fill="x")  # Place labels in a row
    frame_labels.configure(style="Labels.TFrame")
    style.configure("Labels.TFrame", background="lightcoral", foreground="blue")

    frame_left = ttk.Frame(frame_labels)
    frame_left.pack(side="left", anchor="w")
    frame_left.configure(style="Labels.TFrame")
    frame_right = ttk.Frame(frame_labels)
    frame_right.pack(side="right", anchor="e")
    frame_right.configure(style="Labels.TFrame")

    label_elapsed = Label(frame_left, text="Elapsed: 0s", bg="lightcoral", fg="blue", font=("Arial", 12, "bold"))
    label_elapsed.pack(anchor="w")
    label_remaining = Label(frame_left, text="Estimated remaining: --", bg="lightcoral", fg="blue", font=("Arial", 12, "bold"))
    label_remaining.pack(anchor="w")

    label_processed = Label(frame_right, text="Processed: 0", bg="lightcoral", fg="blue", font=("Arial", 12, "bold"))
    label_processed.pack(anchor="e")
    label_total = Label(frame_right, text="Total: --", bg="lightcoral", fg="blue", font=("Arial", 12, "bold"))
    label_total.pack(anchor="e")

    progress = ttk.Progressbar(
        frame_progress, orient="horizontal", length=300, mode="determinate"
    )
    progress.pack(fill="x", pady=5, padx=5, expand=True)

    # --- End progress bar/info frame ---

    def update_progress(
        value, elapsed=None, remaining=None, processed=None, total=None
    ):
        """
        Update the progress bar and info labels.

        Args:
            value (int): Percentage (0–100) to set the progress bar to.
            elapsed (float, optional): Elapsed time in seconds.
            remaining (float or None, optional): Estimated time remaining in seconds, or None if not available.
            processed (int, optional): Number of files processed so far.
            total (int, optional): Total number of files to process.
        """
        progress["value"] = value
        if elapsed is not None:
            label_elapsed.config(text=f"Elapsed: {int(elapsed)}s")
        if remaining is not None:
            if remaining >= 0:
                label_remaining.config(text=f"Estimated remaining: {int(remaining)}s")
            else:
                label_remaining.config(text="Estimated remaining: --")
        if processed is not None:
            label_processed.config(text=f"Processed: {processed}")
        if total is not None:
            label_total.config(text=f"Total: {total}")
        root.update_idletasks()
    
    def start_sorting():
        """
        Perform image sorting using the selected folder.
        Moves paired and single images into separate subfolders.
        Displays the result in the listbox and alerts completion.
        Also shows elapsed and estimated remaining time, processed count, and total count.
        """
        progress["value"] = 0
        label_elapsed.config(text="Elapsed: 0s")
        label_remaining.config(text="Estimated remaining: --")
        label_processed.config(text="Processed: 0")
        label_total.config(text="Total: --")
        listbox_results.delete(0, END)

        folder = selected_folder["path"]
        if not folder:
            messagebox.showerror("No folder selected", "Please select a folder before starting.")
            return
        update_thresholds()
        
        def task():
            start_time = time.time()
            include_singles = reprocess_singles_var.get() == "1"
            folders_dict = get_image_files_by_folder(
                folder, recursive=(process_subfolders_var.get() == "1"),
                include_singles=include_singles
            )
            image_files = [f for files in folders_dict.values() for f in files]
            total_files = len(image_files)
            root.after(0, update_progress, 0, 0, None, 0, total_files)

            processed = [0]

            def progress_callback(value):
                now = time.time()
                # allows for intervening 'pause'
                elapsed = max(0, now - start_time - total_paused_time[0])
                # Estimate remaining time
                if value > 0:
                    avg_time_per_percent = elapsed / value
                    remaining = avg_time_per_percent * (100 - value)
                else:
                    remaining = -1
                # Estimate processed count
                processed_count = int((value / 100) * total_files)
                processed[0] = processed_count
                root.after(
                    0,
                    update_progress,
                    value,
                    elapsed,
                    remaining,
                    processed_count,
                    total_files,
                )

            # Loop for pause support
            image_files.sort(key=get_image_timestamp)
            used = set()
            pairs = []
            for i, path1 in enumerate(image_files):
                if path1 in used:
                    continue
                time1 = get_image_timestamp(path1)
                for j in range(i + 1, len(image_files)):
                    path2 = image_files[j]
                    if path2 in used:
                        continue
                    time2 = get_image_timestamp(path2)
                    if (
                        time2
                        and abs((time2 - time1).total_seconds()) <= TIME_DIFF_THRESHOLD
                    ):
                        if is_similar_image(path1, path2):
                            pairs.append((path1, path2))
                            used.add(path1)
                            used.add(path2)
                            break
                # Pause support: wait if paused
                while not pause_event.is_set():
                    time.sleep(0.1)
                if progress_callback:
                    progress_callback(min(100, int((i / len(image_files)) * 100)))

            # move files to local 'pairs' or 'singles' folders in each folder
            for pair in pairs:
                for file in pair:
                    subdir = os.path.dirname(file)
                    dest_dir = os.path.join(subdir, "_pairs")
                    os.makedirs(dest_dir, exist_ok=True)
                    # shutil.move(file, os.path.join(dest_dir, os.path.basename(file)))
                    src = file
                    dst = os.path.join(dest_dir, os.path.basename(file))
                    if os.path.exists(src):
                        try:
                            shutil.move(src, dst)
                        except FileNotFoundError:
                            pass

            for file in image_files:
                if file not in used:
                    subdir = os.path.dirname(file)
                    if os.path.basename(subdir) == "_singles":
                        continue  # Already in _singles folder, do not move
                    dest_dir = os.path.join(subdir, "_singles")
                    os.makedirs(dest_dir, exist_ok=True)
                    shutil.move(file, os.path.join(dest_dir, os.path.basename(file)))

            num_pairs = len(pairs)
            num_singles = len(image_files) - len(used)
            elapsed = time.time() - start_time
            root.after(0, update_progress, 100, elapsed, 0, total_files, total_files)
            root.after(
                0,
                lambda: [
                    listbox_results.insert(END, f"Pairs moved: {num_pairs}"),
                    listbox_results.insert(END, f"Singles moved: {num_singles}"),
                    messagebox.showinfo(
                        "Done", f"Sorted {num_pairs} pairs and {num_singles} singles."
                    ),
                ],
            )

            # Start the sorting in a background thread

        threading.Thread(target=task, daemon=True).start()

    # --- Button row: Start | Pause | Close ---
    frame_buttons = ttk.Frame(root)
    frame_buttons.pack(fill="x", pady=10)
    frame_buttons.configure(style="Buttons.TFrame")
    style.configure("Buttons.TFrame", background="lightcoral")

    # Configure columns: spacers expand, buttons fixed
    frame_buttons.columnconfigure(0, weight=1)  # left spacer
    frame_buttons.columnconfigure(1, weight=0)  # left button
    frame_buttons.columnconfigure(2, weight=1)  # center-left spacer
    frame_buttons.columnconfigure(3, weight=0)  # center button
    frame_buttons.columnconfigure(4, weight=1)  # center-right spacer
    frame_buttons.columnconfigure(5, weight=0)  # right button
    frame_buttons.columnconfigure(6, weight=1)  # right spacer

    # Start sorting button (left, green)
    button_start = Button(
        frame_buttons,
        text="Start",
        command=start_sorting,
        width=7,
        bg="limegreen",
        activebackground="green2",
        font=("Arial", 12, "bold")
    )
    button_start.grid(row=0, column=1, padx=10)

    # Pause/Continue button (center, yellow)
    pause_event = threading.Event()
    pause_event.set()  # Start unpaused
    pause_continue_label = StringVar(value="Pause")
    pause_start_time = [None]  # Use list for mutability in closures
    total_paused_time = [0]

    def pause_or_continue():
        if pause_event.is_set():
            # Pausing: record when pause starts
            pause_event.clear()
            pause_continue_label.set("Continue")
            pause_start_time[0] = time.time()
        else:
            # Resuming: add to total paused time
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
        activebackground="yellow",
        font=("Arial", 12, "bold"),
    )
    button_pause.grid(row=0, column=3, padx=10)

    # Close window button (right, red)
    button_close = Button(
        frame_buttons,
        text="EXIT",
        command=lambda: confirm_close(root, progress),
        width=7,
        bg="red",
        activebackground="darkred",
        font=("Arial", 12, "bold"),
    )
    button_close.grid(row=0, column=5, padx=10)

    root.mainloop()


if __name__ == "__main__":
    main()

# This code is designed to be run as a standalone script.