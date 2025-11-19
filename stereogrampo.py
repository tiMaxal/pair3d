# stereogram_maker.py
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
stereogram_maker

A utility for creating stereograms from stereo image pairs.
Supports red+cyan anaglyph, side-by-side, and left-right-left formats.
Handles images in a single folder, subfolders, or separate L/R folders.
Optionally outputs MPO files and allows deletion of originals with confirmation.
Images are aligned to ensure horizontal matching.
Output is placed in a duplicated source tree '_3d_[source]' with format-specific subfolders.
Logs processing details to a file in the app directory and a summary in the source folder.
"""

import sys
import os
import shutil
import threading
import time
import logging
from tkinter import filedialog, messagebox, Tk, Label, Button, Listbox, END, StringVar
from tkinter import ttk
from datetime import datetime
from PIL import Image
import cv2
import numpy as np
import imagehash
import piexif
from io import BytesIO

# Constants
TIME_DIFF_THRESHOLD = 2  # Seconds for timestamp-based pairing
HASH_DIFF_THRESHOLD = 10  # Perceptual hash difference threshold

# Get the application directory
def get_app_dir():
    """Return the application directory for settings and logs."""
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        if os.access(exe_dir, os.W_OK):
            return exe_dir
    script_dir = os.path.dirname(__file__)
    if os.access(script_dir, os.W_OK):
        return script_dir
    config_dir = os.path.expanduser("~/.config/stereogram_maker")
    os.makedirs(config_dir, exist_ok=True)
    return config_dir

# Setup logging
LOG_FILE = os.path.join(get_app_dir(), "stereogram_maker.log")
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
SETTINGS_FILE = os.path.join(get_app_dir(), "settings.txt")

# Load the last used folder path
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
        except Exception as e:
            logging.error(f"Failed to load last folder: {e}")
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
    except Exception as e:
        logging.error(f"Failed to save last folder: {e}")

def get_image_files(directory, recursive=False):
    """
    Retrieve image files from the directory, skipping '_3d_' folders.
    Args:
        directory (str): Path to the directory.
        recursive (bool): Whether to include subdirectories.
    Returns:
        list: List of image file paths (.jpg, .jpeg, .png).
    """
    image_files = []
    skip_folders = ["_3d_anaglyph", "_3d_sbs", "_3d_lrl"]
    if recursive:
        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if not d.startswith("_3d_")]
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
    Retrieve image files grouped by folder, skipping '_3d_' folders.
    Args:
        directory (str): Root directory.
        recursive (bool): Whether to include subfolders.
    Returns:
        dict: Mapping from folder path to list of image file paths.
    """
    folders = {}
    skip_folders = ["_3d_anaglyph", "_3d_sbs", "_3d_lrl"]
    if recursive:
        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if not d.startswith("_3d_")]
            image_files = [
                os.path.join(root, f)
                for f in files
                if f.lower().endswith((".jpg", ".jpeg", ".png"))
            ]
            if image_files:
                folders[root] = image_files
    else:
        image_files = get_image_files(directory, recursive=False)
        if image_files:
            folders[directory] = image_files
    return folders

def get_image_timestamp(path):
    """
    Get the modification timestamp of an image file.
    Args:
        path (str): Path to the image file.
    Returns:
        datetime or None: Modification time, or None if unavailable.
    """
    try:
        return datetime.fromtimestamp(os.path.getmtime(path))
    except Exception as e:
        logging.error(f"Failed to get timestamp for {path}: {e}")
        return None

def is_similar_image(file1, file2):
    """
    Determine if two images are perceptually similar using phash.
    Args:
        file1 (str): Path to the first image.
        file2 (str): Path to the second image.
    Returns:
        bool: True if images are similar within the hash threshold.
    """
    try:
        with Image.open(file1) as img1, Image.open(file2) as img2:
            hash1 = imagehash.phash(img1)
            hash2 = imagehash.phash(img2)
        logging.info(f"Hash difference for {file1} and {file2}: {abs(hash1 - hash2)}")
        return abs(hash1 - hash2) < HASH_DIFF_THRESHOLD
    except Exception as e:
        logging.error(f"Failed to compare images {file1} and {file2}: {e}")
        return False

def align_images(left_path, right_path):
    """
    Align two images by detecting rotation needed to make them horizontally level.
    Args:
        left_path (str): Path to the left image.
        right_path (str): Path to the right image.
    Returns:
        tuple: Aligned (left_image, right_image) as PIL Images, or None if alignment fails.
    """
    try:
        left_img = cv2.imread(left_path, cv2.IMREAD_GRAYSCALE)
        right_img = cv2.imread(right_path, cv2.IMREAD_GRAYSCALE)
        if left_img is None or right_img is None:
            logging.error(f"Failed to load images for alignment: {left_path}, {right_path}")
            return None

        orb = cv2.ORB_create()
        keypoints1, descriptors1 = orb.detectAndCompute(left_img, None)
        keypoints2, descriptors2 = orb.detectAndCompute(right_img, None)

        """
        Bedsides the dependencies, you need to ensure the following are installed:
        - opencv-python
        - Pillow
        - imagehash
        - piexif
        - numpy
        If you do not have them installed, you can install them with:
        ```bash
        pip install opencv-python Pillow imagehash piexif numpy
        ```
        """

        if descriptors1 is None or descriptors2 is None:
            logging.error(f"No descriptors found for {left_path} or {right_path}")
            return None

        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(descriptors1, descriptors2)
        matches = sorted(matches, key=lambda x: x.distance)

        if len(matches) < 10:
            logging.warning(f"Too few matches ({len(matches)}) for {left_path} and {right_path}")
            return None

        points1 = np.float32([keypoints1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
        points2 = np.float32([keypoints2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)

        H, _ = cv2.findHomography(points2, points1, cv2.RANSAC, 5.0)
        if H is None:
            logging.error(f"Homography estimation failed for {left_path} and {right_path}")
            return None

        left_pil = Image.open(left_path).convert('RGB')
        right_pil = Image.open(right_path).convert('RGB')
        right_np = np.array(right_pil)

        h, w = left_img.shape
        aligned_right_np = cv2.warpPerspective(right_np, H, (w, h))

        aligned_right = Image.fromarray(aligned_right_np)
        return left_pil, aligned_right
    except Exception as e:
        logging.error(f"Alignment failed for {left_path} and {right_path}: {e}")
        return None

def create_anaglyph(left_img, right_img):
    """
    Create a red+cyan anaglyph stereogram from two images.
    Args:
        left_img (PIL.Image): Left image.
        right_img (PIL.Image): Right image.
    Returns:
        PIL.Image: Anaglyph image.
    """
    try:
        left_np = np.array(left_img)
        right_np = np.array(right_img)
        anaglyph = np.zeros_like(left_np)
        anaglyph[:, :, 0] = left_np[:, :, 0]  # Red channel from left
        anaglyph[:, :, 1] = right_np[:, :, 1]  # Green channel from right
        anaglyph[:, :, 2] = right_np[:, :, 2]  # Blue channel from right
        return Image.fromarray(anaglyph)
    except Exception as e:
        logging.error(f"Failed to create anaglyph: {e}")
        return None

def create_side_by_side(left_img, right_img):
    """
    Create a side-by-side stereogram.
    Args:
        left_img (PIL.Image): Left image.
        right_img (PIL.Image): Right image.
    Returns:
        PIL.Image: Side-by-side image.
    """
    try:
        w, h = left_img.size
        sbs = Image.new('RGB', (w * 2, h))
        sbs.paste(left_img, (0, 0))
        sbs.paste(right_img, (w, 0))
        return sbs
    except Exception as e:
        logging.error(f"Failed to create side-by-side: {e}")
        return None

def create_left_right_left(left_img, right_img):
    """
    Create a left-right-left stereogram.
    Args:
        left_img (PIL.Image): Left image.
        right_img (PIL.Image): Right image.
    Returns:
        PIL.Image: Left-right-left image.
    """
    try:
        w, h = left_img.size
        lrl = Image.new('RGB', (w * 3, h))
        lrl.paste(left_img, (0, 0))
        lrl.paste(right_img, (w, 0))
        lrl.paste(left_img, (w * 2, 0))
        return lrl
    except Exception as e:
        logging.error(f"Failed to create left-right-left: {e}")
        return None

def create_mpo(left_img, right_img, output_path):
    """
    Create an MPO file from two images.
    Args:
        left_img (PIL.Image): Left image.
        right_img (PIL.Image): Right image.
        output_path (str): Path to save the MPO file.
    """
    try:
        # Save left image with MPF tags
        left_buffer = BytesIO()
        left_img.save(left_buffer, format='JPEG', quality=95)
        left_data = left_buffer.getvalue()

        # Save right image
        right_buffer = BytesIO()
        right_img.save(right_buffer, format='JPEG', quality=95)
        right_data = right_buffer.getvalue()

        # Create MPF EXIF data
        mpf_ifd = {
            piexif.ExifIFD.MakerNote: (
                b'MPF\0'  # MPFVersion
                b'\x00\x00\x00\x02'  # NumberOfImages
                b'\xb0\x01\x00\x00'  # MPEntry 1: Attribute (stereo)
                b'\x00\x00\x00\x00'  # Size
                b'\x00\x00\x00\x00'  # Offset
                b'\x00\x00\x00\x00'  # Data
                b'\xb0\x01\x00\x00'  # MPEntry 2: Attribute
                b'\x00\x00\x00\x00'  # Size
                b'\x00\x00\x00\x00'  # Offset
                b'\x00\x00\x00\x00'  # Data
            )
        }

        exif_dict = {'Exif': mpf_ifd}
        exif_bytes = piexif.dump(exif_dict)

        # Write MPO file
        with open(output_path, 'wb') as f:
            f.write(left_data)
            f.write(right_data)

        # Insert EXIF data
        piexif.insert(exif_bytes, output_path)

        logging.info(f"Created MPO file: {output_path}")
    except Exception as e:
        logging.error(f"Failed to create MPO file {output_path}: {e}")

def confirm_close(root, progress):
    """
    Confirm closing the application if processing is in progress.
    Args:
        root (Tk): The Tkinter root window.
        progress (ttk.Progressbar): The progress bar widget.
    """
    if 0 < progress["value"] < 100:
        if not messagebox.askyesno(
            "Work in progress",
            "Processing is ongoing. Are you sure you want to close?"
        ):
            return
    root.destroy()

def main():
    """
    Launch the Tkinter GUI for creating stereograms from stereo image pairs.
    Features:
    - Folder selection with persistence via settings file.
    - Options for anaglyph, side-by-side, or left-right-left output.
    - Checkbox for MPO output.
    - Checkbox for processing subfolders.
    - Checkbox for deleting original files with confirmation.
    - Radio buttons to specify folder structure (single folder, subfolders, L/R folders).
    - Displays folder contents in a Listbox.
    - Start, Pause, and Exit buttons with progress bar and time estimates.
    - Outputs to a duplicated source tree '_3d_[source]' with format-specific subfolders.
    - Logs processing details to a file in the app directory and source folder.
    """
    root = Tk()
    root.title("Stereogram Maker")
    root.configure(bg="lightcoral")
    root.tk_setPalette(background="lightcoral", foreground="blue")
    default_font = ("Arial", 12, "bold")
    root.option_add("*Font", default_font)
    root.geometry("600x800")

    # Center window
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - 800) // 4
    y = (screen_height - 600) // 4
    root.geometry(f"+{x}+{y}")

    # Set icon if available
    icon_path = os.path.join(os.path.dirname(__file__), "imgs/stereogram_maker.ico")
    if os.path.exists(icon_path):
        root.iconbitmap(icon_path)

    # Store selected folder
    selected_folder = {"path": load_last_folder()}

    # Prompt text
    label = Label(
        root,
        text="Select folder[s] containing stereo image pairs:",
        bg="lightcoral",
        fg="blue",
        font=("Arial", 14, "bold")
    )
    label.pack(pady=10)

    # Frame for folder label and browse button
    frame_folder = ttk.Frame(root)
    frame_folder.pack(fill="x", padx=10)
    label_selected_folder = Label(
        frame_folder,
        text=selected_folder["path"] if selected_folder["path"] else "No folder selected",
        fg="black" if selected_folder["path"] else "gray",
        bg="lightcoral"
    )
    label_selected_folder.pack(side="left", fill="x", expand=True)

    def browse_folder():
        """Handle folder selection and update UI."""
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
            update_folder_contents_listbox()

    button_browse = Button(
        frame_folder, text="Browse", command=browse_folder, bg="lightblue"
    )
    button_browse.pack(side="right", padx=5, pady=5)

    # Folder options
    frame_folder_options = ttk.Frame(root)
    frame_folder_options.pack(pady=5, fill="x")
    style = ttk.Style()
    style.configure("TCheckbutton", background="lightcoral", foreground="blue")
    style.configure("TFrame", background="lightcoral")
    frame_folder_options.configure(style="FolderOptions.TFrame")
    style.configure("FolderOptions.TFrame", background="lightcoral")

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

    delete_originals_var = StringVar(value="0")
    check_delete_originals = ttk.Checkbutton(
        frame_folder_options,
        text="Delete originals (with confirmation)",
        variable=delete_originals_var,
        onvalue="1",
        offvalue="0"
    )
    check_delete_originals.grid(row=0, column=3, padx=10, pady=2)

    # Output format selection
    frame_output_format = ttk.Frame(root)
    frame_output_format.pack(pady=5, fill="x")
    frame_output_format.configure(style="OutputFormat.TFrame")
    style.configure("OutputFormat.TFrame", background="lightcoral")
    style.configure("TRadiobutton", background="lightcoral", foreground="blue")

    output_format_var = StringVar(value="anaglyph")
    Label(frame_output_format, text="Output Format:", bg="lightcoral", fg="blue").pack(anchor="w", padx=10)
    ttk.Radiobutton(
        frame_output_format,
        text="Red+Cyan Anaglyph",
        value="anaglyph",
        variable=output_format_var
    ).pack(anchor="w", padx=20)
    ttk.Radiobutton(
        frame_output_format,
        text="Side-by-Side",
        value="sbs",
        variable=output_format_var
    ).pack(anchor="w", padx=20)
    ttk.Radiobutton(
        frame_output_format,
        text="Left-Right-Left",
        value="lrl",
        variable=output_format_var
    ).pack(anchor="w", padx=20)

    # MPO output option
    mpo_output_var = StringVar(value="0")
    check_mpo = ttk.Checkbutton(
        frame_output_format,
        text="Also output MPO files",
        variable=mpo_output_var,
        onvalue="1",
        offvalue="0"
    )
    check_mpo.pack(anchor="w", padx=20, pady=5)

    # Folder structure selection
    frame_folder_structure = ttk.Frame(root)
    frame_folder_structure.pack(pady=5, fill="x")
    frame_folder_structure.configure(style="FolderStructure.TFrame")
    style.configure("FolderStructure.TFrame", background="lightcoral")

    folder_structure_var = StringVar(value="single")
    Label(frame_folder_structure, text="Folder Structure:", bg="lightcoral", fg="blue").pack(anchor="w", padx=10)
    ttk.Radiobutton(
        frame_folder_structure,
        text="Single folder (L/R pairs)",
        value="single",
        variable=folder_structure_var,
        command=lambda: update_folder_contents_listbox()
    ).pack(anchor="w", padx=20)
    ttk.Radiobutton(
        frame_folder_structure,
        text="Subfolders (L/R pairs)",
        value="subfolders",
        variable=folder_structure_var,
        command=lambda: update_folder_contents_listbox()
    ).pack(anchor="w", padx=20)
    ttk.Radiobutton(
        frame_folder_structure,
        text="Separate L/R folders",
        value="lr_folders",
        variable=folder_structure_var,
        command=lambda: update_folder_contents_listbox()
    ).pack(anchor="w", padx=20)

    # Threshold controls
    frame_thresholds = ttk.Frame(root)
    frame_thresholds.pack(pady=5, fill="x")
    frame_thresholds.configure(style="Thresholds.TFrame")
    style.configure("Thresholds.TFrame", background="lightcoral")

    frame_thresholds.columnconfigure(0, weight=1)
    frame_thresholds.columnconfigure(1, weight=0)
    frame_thresholds.columnconfigure(2, weight=0)
    frame_thresholds.columnconfigure(3, weight=1)
    frame_thresholds.columnconfigure(4, weight=0)
    frame_thresholds.columnconfigure(5, weight=0)
    frame_thresholds.columnconfigure(6, weight=1)

    Label(frame_thresholds, text="Time diff (s):", font=("Arial", 12, "bold")).grid(
        row=0, column=1, padx=(0, 2), pady=2, sticky="e"
    )
    time_diff_var = StringVar(value=str(TIME_DIFF_THRESHOLD))
    entry_time_diff = ttk.Entry(frame_thresholds, textvariable=time_diff_var, width=5)
    entry_time_diff.grid(row=0, column=2, padx=(0, 10), pady=2, sticky="w")
    entry_time_diff.configure(background="lightblue", foreground="blue")

    Label(frame_thresholds, text="Hash diff:", font=("Arial", 12, "bold")).grid(
        row=0, column=4, padx=(0, 2), pady=2, sticky="e"
    )
    hash_diff_var = StringVar(value=str(HASH_DIFF_THRESHOLD))
    entry_hash_diff = ttk.Entry(frame_thresholds, textvariable=hash_diff_var, width=5)
    entry_hash_diff.grid(row=0, column=5, padx=(0, 0), pady=2, sticky="w")
    entry_hash_diff.configure(background="lightblue", foreground="blue")

    def update_thresholds():
        """Update global threshold variables."""
        global TIME_DIFF_THRESHOLD, HASH_DIFF_THRESHOLD
        try:
            TIME_DIFF_THRESHOLD = max(0.01, float(time_diff_var.get()))
        except Exception as e:
            logging.warning(f"Invalid time diff input: {e}")
        try:
            HASH_DIFF_THRESHOLD = max(1, int(hash_diff_var.get()))
        except Exception as e:
            logging.warning(f"Invalid hash diff input: {e}")
        logging.info(f"Thresholds updated: Time={TIME_DIFF_THRESHOLD}, Hash={HASH_DIFF_THRESHOLD}")

    entry_time_diff.bind("<FocusOut>", lambda e: update_thresholds())
    entry_time_diff.bind("<Return>", lambda e: update_thresholds())
    entry_hash_diff.bind("<FocusOut>", lambda e: update_thresholds())
    entry_hash_diff.bind("<Return>", lambda e: update_thresholds())

    # Listbox for folder contents
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

    # Results listbox
    listbox_results = Listbox(root, width=30, height=3, bg="lightblue", fg="blue")
    listbox_results.pack(pady=10)

    # Label to show total image count
    label_image_count = Label(root, text="No folder selected")
    label_image_count.pack()

    def update_folder_contents_listbox():
        """Update Listbox with folder contents based on folder structure."""
        listbox_folder_contents.delete(0, END)
        folder = selected_folder["path"]
        if not folder:
            return
        try:
            structure = folder_structure_var.get()
            if structure == "lr_folders":
                folders_dict = {}
                left_folder = os.path.join(folder, "Left")
                right_folder = os.path.join(folder, "Right")
                if os.path.isdir(left_folder) and os.path.isdir(right_folder):
                    left_files = get_image_files(left_folder, recursive=False)
                    right_files = get_image_files(right_folder, recursive=False)
                    folders_dict[left_folder] = left_files
                    folders_dict[right_folder] = right_files
            else:
                folders_dict = get_image_files_by_folder(
                    folder, recursive=(structure == "subfolders")
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
            logging.error(f"Error updating folder contents: {e}")

    # Progress bar and info
    frame_progress = ttk.Frame(root)
    frame_progress.pack(pady=5, fill="x")
    frame_progress.configure(style="Progress.TFrame")
    style.configure("Progress.TFrame", background="lightcoral")

    frame_labels = ttk.Frame(frame_progress)
    frame_labels.pack(fill="x")
    frame_labels.configure(style="Labels.TFrame")
    style.configure("Labels.TFrame", background="lightcoral")

    frame_left = ttk.Frame(frame_labels)
    frame_left.pack(side="left", anchor="w")
    frame_right = ttk.Frame(frame_labels)
    frame_right.pack(side="right", anchor="e")

    label_elapsed = Label(frame_left, text="Elapsed: 0s", bg="lightcoral", fg="blue")
    label_elapsed.pack(anchor="w")
    label_remaining = Label(frame_left, text="Estimated remaining: --", bg="lightcoral", fg="blue")
    label_remaining.pack(anchor="w")
    label_processed = Label(frame_right, text="Processed: 0", bg="lightcoral", fg="blue")
    label_processed.pack(anchor="e")
    label_total = Label(frame_right, text="Total: --", bg="lightcoral", fg="blue")
    label_total.pack(anchor="e")

    progress = ttk.Progressbar(frame_progress, orient="horizontal", length=300, mode="determinate")
    progress.pack(fill="x", pady=5, padx=5, expand=True)

    def update_progress(value, elapsed=None, remaining=None, processed=None, total=None):
        """Update progress bar and info labels."""
        progress["value"] = value
        if elapsed is not None:
            label_elapsed.config(text=f"Elapsed: {int(elapsed)}s")
        if remaining is not None:
            label_remaining.config(text=f"Estimated remaining: {int(remaining)}s" if remaining >= 0 else "Estimated remaining: --")
        if processed is not None:
            label_processed.config(text=f"Processed: {processed}")
        if total is not None:
            label_total.config(text=f"Total: {total}")
        root.update_idletasks()

    def start_processing():
        """Process stereo pairs and create stereograms in a duplicated source tree."""
        folder = selected_folder["path"]
        if not folder:
            messagebox.showerror("No folder selected", "Please select a folder before starting.")
            return

        update_thresholds()
        progress["value"] = 0
        label_elapsed.config(text="Elapsed: 0s")
        label_remaining.config(text="Estimated remaining: --")
        label_processed.config(text="Processed: 0")
        label_total.config(text="Total: --")
        listbox_results.delete(0, END)

        def task():
            start_time = time.time()
            structure = folder_structure_var.get()
            output_format = output_format_var.get()
            mpo_output = mpo_output_var.get() == "1"
            delete_originals = delete_originals_var.get() == "1"
            source_base = os.path.basename(folder)
            output_root = os.path.join(os.path.dirname(folder), f"_3d_{source_base}")
            log_file = os.path.join(folder, f"stereogram_maker_{output_format}_log.txt")
            processed_files = []
            deleted_files = []

            # Get pairs
            if structure == "lr_folders":
                left_folder = os.path.join(folder, "Left")
                right_folder = os.path.join(folder, "Right")
                if not (os.path.isdir(left_folder) and os.path.isdir(right_folder)):
                    root.after(0, lambda: messagebox.showerror("Error", "Left or Right folder missing."))
                    return
                left_files = get_image_files(left_folder, recursive=False)
                right_files = get_image_files(right_folder, recursive=False)
                left_files.sort()
                right_files.sort()
                pairs = [(left_files[i], right_files[i]) for i in range(min(len(left_files), len(right_files)))]
                total_files = len(pairs)
            else:
                folders_dict = get_image_files_by_folder(folder, recursive=(structure == "subfolders"))
                image_files = [f for files in folders_dict.values() for f in files]
                total_files = len(image_files) if structure == "single" else sum(len(files) // 2 for files in folders_dict.values())
                pairs = []
                if structure == "single":
                    image_files.sort()
                    pairs = [(image_files[i], image_files[i + 1]) for i in range(0, len(image_files) - 1, 2)]
                else:
                    for subfolder, files in folders_dict.items():
                        files.sort(key=get_image_timestamp)
                        used = set()
                        for i, path1 in enumerate(files):
                            if path1 in used:
                                continue
                            time1 = get_image_timestamp(path1)
                            for j in range(i + 1, len(files)):
                                path2 = files[j]
                                if path2 in used:
                                    continue
                                time2 = get_image_timestamp(path2)
                                if time2 and abs((time2 - time1).total_seconds()) <= TIME_DIFF_THRESHOLD:
                                    if is_similar_image(path1, path2):
                                        pairs.append((path1, path2))
                                        used.add(path1)
                                        used.add(path2)
                                        break

            root.after(0, update_progress, 0, 0, None, 0, total_files)

            processed = [0]
            for i, (left_path, right_path) in enumerate(pairs):
                while not pause_event.is_set():
                    time.sleep(0.1)

                # Validate images
                try:
                    with Image.open(left_path) as left_img, Image.open(right_path) as right_img:
                        pass
                except Exception as e:
                    logging.error(f"Invalid image pair {left_path}, {right_path}: {e}")
                    continue

                # Create output directory
                rel_path = os.path.relpath(os.path.dirname(left_path), folder)
                output_dir = os.path.join(output_root, rel_path, f"{output_format}")
                os.makedirs(output_dir, exist_ok=True)
                if mpo_output:
                    mpo_dir = os.path.join(output_root, rel_path, f"mpo")
                    os.makedirs(mpo_dir, exist_ok=True)

                aligned = align_images(left_path, right_path)
                if aligned is None:
                    logging.error(f"Skipping pair {left_path}, {right_path} due to alignment failure")
                    continue
                left_img, right_img = aligned

                output_name = f"stereo_{i:04d}.jpg"
                output_path = os.path.join(output_dir, output_name)
                if output_format == "anaglyph":
                    result = create_anaglyph(left_img, right_img)
                elif output_format == "sbs":
                    result = create_side_by_side(left_img, right_img)
                else:  # lrl
                    result = create_left_right_left(left_img, right_img)

                if result:
                    result.save(output_path, quality=95)
                    processed_files.append(output_path)
                    logging.info(f"Created stereogram: {output_path}")

                if mpo_output:
                    mpo_path = os.path.join(mpo_dir, f"stereo_{i:04d}.mpo")
                    create_mpo(left_img, right_img, mpo_path)
                    if os.path.exists(mpo_path):
                        processed_files.append(mpo_path)

                processed[0] += 1
                elapsed = max(0, time.time() - start_time - total_paused_time[0])
                avg_time_per_file = elapsed / max(1, processed[0])
                remaining = avg_time_per_file * (total_files - processed[0])
                root.after(0, update_progress, (processed[0] / total_files) * 100, elapsed, remaining, processed[0], total_files)

            if delete_originals and processed_files:
                if messagebox.askyesno("Confirm Delete", "Delete original files? This cannot be undone."):
                    for left_path, right_path in pairs:
                        try:
                            if os.path.exists(left_path):
                                os.remove(left_path)
                                deleted_files.append(left_path)
                            if os.path.exists(right_path):
                                os.remove(right_path)
                                deleted_files.append(right_path)
                        except Exception as e:
                            logging.error(f"Failed to delete {left_path} or {right_path}: {e}")

            # Write log file
            try:
                with open(log_file, "w", encoding="utf-8") as f:
                    f.write(f"Stereogram Maker Log - {datetime.now()}\n")
                    f.write(f"Output Format: {output_format}\n")
                    f.write(f"MPO Output: {'Yes' if mpo_output else 'No'}\n")
                    f.write(f"Folder Structure: {structure}\n")
                    f.write(f"Output Root: {output_root}\n")
                    f.write(f"Processed Pairs: {len(pairs)}\n")
                    f.write("Output Files:\n")
                    for file in processed_files:
                        f.write(f"  {file}\n")
                    if deleted_files:
                        f.write("Deleted Originals:\n")
                        for file in deleted_files:
                            f.write(f"  {file}\n")
            except Exception as e:
                logging.error(f"Failed to write log file {log_file}: {e}")

            root.after(0, lambda: [
                listbox_results.insert(END, f"Processed {len(pairs)} pairs"),
                listbox_results.insert(END, f"Output files: {len(processed_files)}"),
                messagebox.showinfo("Done", f"Created {len(processed_files)} stereograms/MPOs.")
            ])

        threading.Thread(target=task, daemon=True).start()

    # Buttons
    frame_buttons = ttk.Frame(root)
    frame_buttons.pack(fill="x", pady=10)
    frame_buttons.configure(style="Buttons.TFrame")
    style.configure("Buttons.TFrame", background="lightcoral")

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
        command=start_processing,
        width=7,
        bg="limegreen",
        activebackground="green2",
        font=("Arial", 12, "bold")
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
        activebackground="yellow",
        font=("Arial", 12, "bold")
    )
    button_pause.grid(row=0, column=3, padx=10)

    button_close = Button(
        frame_buttons,
        text="EXIT",
        command=lambda: confirm_close(root, progress),
        width=7,
        bg="red",
        activebackground="darkred",
        font=("Arial", 12, "bold")
    )
    button_close.grid(row=0, column=5, padx=10)

    root.mainloop()

if __name__ == "__main__":
    try:
        import cv2
        import numpy
        from PIL import Image
        import imagehash
        import piexif
        from io import BytesIO
    except ImportError as e:
        print(f"Error: Missing required module: {e}")
        print("Please install the required modules using:")
        print("pip install opencv-python Pillow imagehash piexif numpy")
        sys.exit(1)
    main()