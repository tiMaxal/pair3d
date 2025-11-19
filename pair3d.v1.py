"""
pair3d.py

A utility for sorting stereo image pairs in a folder.
Pairs are detected based on file modification timestamps and perceptual image similarity.
Pairs are moved into a 'pairs' subfolder, and unpaired images into a 'singles' subfolder.
A simple Tkinter GUI allows users to select a folder and view results.

    =====

original ai prompt [20250624]:

 a way to separate pairs from folders also containing singles .. software that compares for image-similarity and closeness of time-created

"""

import os
import shutil
import threading
import time
from tkinter import filedialog, messagebox, Tk, Label, Button, Listbox, END, StringVar
from tkinter import ttk
from datetime import datetime
from PIL import Image
import imagehash

TIME_DIFF_THRESHOLD = 2
HASH_DIFF_THRESHOLD = 10

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "settings.txt")


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
    skipping any 'pairs' or 'singles' folders.

    Args:
        directory (str): Path to the directory to search.
        recursive (bool): Whether to include image files from subdirectories.

    Returns:
        list: List of image file paths with extensions .jpg, .jpeg, or .png.
    """
    image_files = []
    if recursive:
        for root, dirs, files in os.walk(directory):
            # Skip 'pairs' and 'singles' folders
            dirs[:] = [d for d in dirs if d not in ("pairs", "singles")]
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


def get_image_files_by_folder(directory, recursive=False):
    """
    Retrieve image files grouped by folder. When recursive is True,
    returns a dictionary mapping each folder path to its own list of image files.

    Skips 'pairs' and 'singles' folders.

    Args:
        directory (str): Root directory.
        recursive (bool): Whether to include subfolders.

    Returns:
        dict: Mapping from folder path to list of image file paths.
    """
    folders = {}
    if recursive:
        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if d not in ("pairs", "singles")]
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
    The interface provides:
    - A label to prompt folder selection.
    - A 'Browse' button to choose a directory containing image files.
    - A label to display the selected folder path.
    - A 'Start' button to commence sorting after a folder is selected.
    - A listbox to display the result counts for pairs and singles.
    - A progress bar that updates as image pairs are processed.
    - Elapsed time (left), processed count (right),
        and estimated time remaining (left, below elapsed)
            and total file count (right, below processed) are displayed.
    - A 'Pause' button to suspend processing [does not yet pause 'elapsed']
    - A 'Close' button to exit the app, with alert warning tied to progress bar.
    """
    root = Tk()
    root.title("pair3d - Stereo Image Sorter")

    # Store selected folder path using a mutable object, initialized from settings
    selected_folder = {"path": load_last_folder()}

    # Prompt text
    label = Label(root, text="Select a folder containing images to sort:")
    label.pack(pady=10)

    # Display selected folder (show last folder if available)
    init_folder = selected_folder["path"]
    label_selected_folder = Label(
        root,
        text=init_folder if init_folder else "No folder selected",
        fg="black" if init_folder else "gray",
    )
    label_selected_folder.pack()

    # Checkbox for processing subfolders
    process_subfolders_var = StringVar(value="0")
    check_subfolders = ttk.Checkbutton(
        root,
        text="Process subfolders",
        variable=process_subfolders_var,
        onvalue="1",
        offvalue="0",
    )
    check_subfolders.pack()

    # Display results
    listbox_results = Listbox(root, width=40)
    listbox_results.pack(pady=10)

    # --- Progress bar and info frame ---
    frame_progress = ttk.Frame(root)
    frame_progress.pack(pady=5, fill="x")

    # Elapsed/remaining on left, processed/total on right
    frame_left = ttk.Frame(frame_progress)
    frame_left.pack(side="left", anchor="w")
    frame_right = ttk.Frame(frame_progress)
    frame_right.pack(side="right", anchor="e")

    label_elapsed = Label(frame_left, text="Elapsed: 0s")
    label_elapsed.pack(anchor="w")
    label_remaining = Label(frame_left, text="Estimated remaining: --")
    label_remaining.pack(anchor="w")

    label_processed = Label(frame_right, text="Processed: 0")
    label_processed.pack(anchor="e")
    label_total = Label(frame_right, text="Total: --")
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

    def browse_folder():
        """
        Handle folder selection via file dialog and update the UI.
        Remembers the last used folder across sessions.
        """
        initialdir = selected_folder["path"] if selected_folder["path"] else None
        folder = filedialog.askdirectory(initialdir=initialdir)
        if folder:
            selected_folder["path"] = folder
            save_last_folder(folder)
            label_selected_folder.config(text=folder, fg="black")
            listbox_results.delete(0, END)
            progress["value"] = 0
            label_elapsed.config(text="Elapsed: 0s")
            label_remaining.config(text="Estimated remaining: --")
            label_processed.config(text="Processed: 0")
            label_total.config(text="Total: --")

    def start_sorting():
        """
        Perform image sorting using the selected folder.
        Moves paired and single images into separate subfolders.
        Displays the result in the listbox and alerts completion.
        Also shows elapsed and estimated remaining time, processed count, and total count.
        """
        folder = selected_folder["path"]
        save_last_folder(folder)
        if not folder:
            messagebox.showwarning("No Folder", "Please select a folder first.")
            return

        progress["value"] = 0
        label_elapsed.config(text="Elapsed: 0s")
        label_remaining.config(text="Estimated remaining: --")
        label_processed.config(text="Processed: 0")
        label_total.config(text="Total: --")
        listbox_results.delete(0, END)

        def task():
            start_time = time.time()
            folders_dict = get_image_files_by_folder(
                folder, recursive=(process_subfolders_var.get() == "1")
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
                    dest_dir = os.path.join(subdir, "pairs")
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
                    dest_dir = os.path.join(subdir, "singles")
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

    # left frame select/sort buttons
    frame_left_buttons = ttk.Frame(root)
    frame_left_buttons.pack(side="left", anchor="nw", padx=10, pady=5)

    # Folder selection button
    button_browse = Button(frame_left_buttons, text="Browse", command=browse_folder)
    button_browse.pack(pady=5)

    # Start sorting button
    button_start = Button(frame_left_buttons, text="Start", command=start_sorting)
    button_start.pack(pady=5)

    # right frame pause/close buttons
    frame_right_buttons = ttk.Frame(root)
    frame_right_buttons.pack(side="right", anchor="se", padx=10, pady=5)

    # Pause/Continue button
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
        frame_right_buttons,
        textvariable=pause_continue_label,
        command=pause_or_continue,
    )
    button_pause.pack(pady=5)

    # Close window button
    button_close = Button(
        frame_right_buttons, text="Close", command=lambda: confirm_close(root, progress)
    )
    button_close.pack(pady=5)

    root.mainloop()


if __name__ == "__main__":
    main()
