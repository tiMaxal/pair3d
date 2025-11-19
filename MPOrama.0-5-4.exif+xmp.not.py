import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
from PIL import Image
import numpy as np
import time
import threading
import logging
from datetime import datetime
import sys
import json
from exiftool import ExifToolHelper
import exiftool

class MPOramaApp:
    """A GUI application for converting .mpo stereo image files into various stereogram formats.

    The application allows users to select an input folder containing .mpo files, choose an output
    folder (defaulting to '_x2' in the input directory), and select stereogram formats (anaglyph,
    crossview, parallel, left-right-left, left, right) via checkboxes. It supports processing
    subdirectories with options to save outputs in a root folder or respective subdirectories.
    Outputs can be organized into format-specific folders, with an option to keep original filenames
    without format prefixes/suffixes. Users can choose to retain Exif, IPTC, and XMP metadata from
    input files. Settings are saved to a JSON file. The GUI includes a progress bar, file count,
    time tracking, pause/resume functionality, and logging.
    """

    def __init__(self, root):
        """Initialize the MPOrama application with GUI elements and state variables.

        Args:
            root (tk.Tk): The Tkinter root window.
        """
        self.root = root
        self.root.title("MPOrama - Stereogram Converter")
        self.root.geometry("600x800")
        self.root.configure(bg="lightcoral")
        self.root.tk_setPalette(background="lightcoral", foreground="blue")
        default_font = ("Arial", 12)
        self.root.option_add("*Font", default_font)

        # Center the window
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width - 600) // 4
        y = (screen_height - 800) // 4
        self.root.geometry(f"+{x}+{y}")

        # Initialize logging
        self._setup_logging()

        # Variables
        self.input_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.include_subdirs = tk.BooleanVar()
        self.save_in_root = tk.BooleanVar(value=True)
        self.separate_formats = tk.BooleanVar()
        self.no_filename_change = tk.BooleanVar()
        self.formats = {
            "anaglyph": tk.BooleanVar(),
            "crossview": tk.BooleanVar(),
            "parallel": tk.BooleanVar(),
            "lrl": tk.BooleanVar(),
            "left": tk.BooleanVar(),
            "right": tk.BooleanVar()
        }
        self.metadata = {
            "exif": tk.BooleanVar(value=True),  # Default checked
            "iptc": tk.BooleanVar(),
            "xmp": tk.BooleanVar(value=True)    # Default checked
        }
        self.pause_event = threading.Event()
        self.pause_event.set()
        self.total_paused_time = [0]
        self.pause_start_time = [None]
        self.exiftool = None

        # Load saved settings
        self.settings_file = os.path.join(os.path.dirname(__file__) if not getattr(sys, "frozen", False) else os.path.dirname(sys.executable), "mporama_settings.json")
        self.load_settings()

        # Bind settings update on variable changes
        self.input_dir.trace_add("write", self.save_settings)
        self.output_dir.trace_add("write", self.save_settings)
        self.include_subdirs.trace_add("write", self.save_settings)
        self.save_in_root.trace_add("write", self.save_settings)
        self.separate_formats.trace_add("write", self.save_settings)
        self.no_filename_change.trace_add("write", self.save_settings)
        for var in self.formats.values():
            var.trace_add("write", self.save_settings)
        for var in self.metadata.values():
            var.trace_add("write", self.save_settings)

        # GUI Elements
        # Input Directory
        tk.Label(root, text="Select folder containing .mpo files:", bg="lightcoral", fg="blue", font=("Arial", 14, "bold")).pack(pady=10)
        frame_folder = ttk.Frame(root)
        frame_folder.pack(fill="x", padx=10)
        self.input_entry = tk.Entry(frame_folder, textvariable=self.input_dir, bg="lightblue", highlightbackground="lightblue", highlightcolor="lightblue", highlightthickness=1)
        self.input_entry.pack(side="left", fill="x", expand=True)
        tk.Button(frame_folder, text="Browse", command=self.browse_input, bg="lightblue").pack(side="right", padx=5, pady=5)

        # Output Directory
        tk.Label(root, text="Select output folder:", bg="lightcoral", fg="blue", font=("Arial", 14, "bold")).pack(pady=10)
        frame_output = ttk.Frame(root)
        frame_output.pack(fill="x", padx=10)
        self.output_entry = tk.Entry(frame_output, textvariable=self.output_dir, bg="lightblue", highlightbackground="lightblue", highlightcolor="lightblue", highlightthickness=1)
        self.output_entry.pack(side="left", fill="x", expand=True)
        tk.Button(frame_output, text="Browse", command=self.browse_output, bg="lightblue").pack(side="right", padx=5, pady=5)

        # File Count Display
        self.label_file_count = tk.Label(root, text="Total .mpo files: 0", bg="lightcoral", fg="blue", font=("Arial", 12, "bold"))
        self.label_file_count.pack(pady=5)

        # Include Subdirectories and Save Options
        frame_options = ttk.Frame(root)
        frame_options.pack(pady=5, fill="x")
        style = ttk.Style()
        style.configure("Options.TFrame", background="lightcoral")
        style.configure("Custom.TRadiobutton", background="lightcoral", foreground="blue")
        frame_options.configure(style="Options.TFrame")
        tk.Checkbutton(frame_options, text="Include Subdirectories", variable=self.include_subdirs, command=self.toggle_subdir_options, bg="lightcoral", fg="blue").pack(anchor="w", padx=10)
        
        self.subdir_frame = ttk.Frame(frame_options)
        self.subdir_frame.pack(anchor="w")
        self.radio_root = ttk.Radiobutton(self.subdir_frame, text="Save in Root Output Folder", variable=self.save_in_root, value=True, style="Custom.TRadiobutton", state="disabled")
        self.radio_root.pack(anchor="w", padx=20)
        self.radio_subdirs = ttk.Radiobutton(self.subdir_frame, text="Save in Respective Subdirectories", variable=self.save_in_root, value=False, style="Custom.TRadiobutton", state="disabled")
        self.radio_subdirs.pack(anchor="w", padx=20)
        
        frame_format_options = ttk.Frame(frame_options)
        frame_format_options.pack(anchor="w", padx=10)
        frame_format_options.configure(style="Options.TFrame")
        tk.Checkbutton(frame_format_options, text="Separate to Format Folders", variable=self.separate_formats, bg="lightcoral", fg="blue").pack(side="left")
        tk.Checkbutton(frame_format_options, text="No Filename Change", variable=self.no_filename_change, bg="lightcoral", fg="blue").pack(side="left", padx=10)

        # Format Selection
        tk.Label(root, text="Select Output Formats:", bg="lightcoral", fg="blue", font=("Arial", 14, "bold")).pack(pady=10)
        format_frame = ttk.Frame(root)
        format_frame.pack()
        format_frame.configure(style="Options.TFrame")
        tk.Checkbutton(format_frame, text="Anaglyph (rc_)", variable=self.formats["anaglyph"], bg="lightcoral", fg="blue").grid(row=0, column=0, padx=5, pady=2)
        tk.Checkbutton(format_frame, text="Left-Right-Left (lrl_)", variable=self.formats["lrl"], bg="lightcoral", fg="blue").grid(row=0, column=1, padx=5, pady=2)
        tk.Checkbutton(format_frame, text="Parallel (ii_)", variable=self.formats["parallel"], bg="lightcoral", fg="blue").grid(row=1, column=0, padx=5, pady=2)
        tk.Checkbutton(format_frame, text="Crossview (xi_)", variable=self.formats["crossview"], bg="lightcoral", fg="blue").grid(row=1, column=1, padx=5, pady=2)
        tk.Checkbutton(format_frame, text="Left (_l)", variable=self.formats["left"], bg="lightcoral", fg="blue").grid(row=2, column=0, padx=5, pady=2)
        tk.Checkbutton(format_frame, text="Right (_r)", variable=self.formats["right"], bg="lightcoral", fg="blue").grid(row=2, column=1, padx=5, pady=2)

        # Metadata Retention Options
        tk.Label(root, text="Retain Metadata if Present:", bg="lightcoral", fg="blue", font=("Arial", 14, "bold")).pack(pady=10)
        metadata_frame = ttk.Frame(root)
        metadata_frame.pack()
        metadata_frame.configure(style="Options.TFrame")
        tk.Checkbutton(metadata_frame, text="Exif", variable=self.metadata["exif"], bg="lightcoral", fg="blue").grid(row=0, column=0, padx=5, pady=2)
        tk.Checkbutton(metadata_frame, text="IPTC", variable=self.metadata["iptc"], bg="lightcoral", fg="blue").grid(row=0, column=1, padx=5, pady=2)
        tk.Checkbutton(metadata_frame, text="XMP", variable=self.metadata["xmp"], bg="lightcoral", fg="blue").grid(row=0, column=2, padx=5, pady=2)
        tk.Button(metadata_frame, text="All", command=self.select_all_metadata, bg="lightblue", width=5).grid(row=1, column=1, padx=5, pady=2)
        tk.Button(metadata_frame, text="None", command=self.select_none_metadata, bg="lightblue", width=5).grid(row=1, column=2, padx=5, pady=2)

        # Progress and Info
        frame_progress = ttk.Frame(root)
        frame_progress.pack(pady=5, fill="x")
        frame_progress.configure(style="Progress.TFrame")
        style.configure("Progress.TFrame", background="lightcoral")
        frame_labels = ttk.Frame(frame_progress)
        frame_labels.pack(fill="x")
        frame_labels.configure(style="Labels.TFrame")
        style.configure("Labels.TFrame", background="lightcoral", foreground="blue")
        frame_left = ttk.Frame(frame_labels)
        frame_left.pack(side="left", anchor="w")
        frame_left.configure(style="Labels.TFrame")
        frame_right = ttk.Frame(frame_labels)
        frame_right.pack(side="right", anchor="e")
        frame_right.configure(style="Labels.TFrame")

        self.label_elapsed = tk.Label(frame_left, text="Elapsed: 0s", bg="lightcoral", fg="blue", font=("Arial", 12, "bold"))
        self.label_elapsed.pack(anchor="w")
        self.label_remaining = tk.Label(frame_left, text="Estimated remaining: --", bg="lightcoral", fg="blue", font=("Arial", 12, "bold"))
        self.label_remaining.pack(anchor="w")
        self.label_processed = tk.Label(frame_right, text="Processed: 0", bg="lightcoral", fg="blue", font=("Arial", 12, "bold"))
        self.label_processed.pack(anchor="e")
        self.label_total = tk.Label(frame_right, text="Total: --", bg="lightcoral", fg="blue", font=("Arial", 12, "bold"))
        self.label_total.pack(anchor="e")

        self.progress = ttk.Progressbar(frame_progress, orient="horizontal", length=300, mode="determinate")
        self.progress.pack(fill="x", pady=5, padx=5, expand=True)

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

        self.start_button = tk.Button(frame_buttons, text="Start", command=self.start_processing, width=7, bg="limegreen", activebackground="green2", font=("Arial", 12, "bold"))
        self.start_button.grid(row=0, column=1, padx=10)
        self.pause_label = tk.StringVar(value="Pause")
        self.pause_button = tk.Button(frame_buttons, textvariable=self.pause_label, command=self.pause_or_continue, width=10, bg="gold", activebackground="yellow", font=("Arial", 12, "bold"))
        self.pause_button.grid(row=0, column=3, padx=10)
        tk.Button(frame_buttons, text="Exit", command=self.confirm_close, width=7, bg="red", activebackground="darkred", font=("Arial", 12, "bold")).grid(row=0, column=4, padx=10)

    def _setup_logging(self):
        """Configure logging to a file in the application directory."""
        log_dir = os.path.dirname(__file__) if not getattr(sys, "frozen", False) else os.path.dirname(sys.executable)
        log_file = os.path.join(log_dir, "mporama.log")
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s"
        )
        logging.info("MPOrama application started")

    def load_settings(self):
        """Load user settings from a JSON file if it exists."""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, "r") as f:
                    settings = json.load(f)
                self.input_dir.set(settings.get("input_dir", ""))
                self.output_dir.set(settings.get("output_dir", ""))
                self.include_subdirs.set(settings.get("include_subdirs", False))
                self.save_in_root.set(settings.get("save_in_root", True))
                self.separate_formats.set(settings.get("separate_formats", False))
                self.no_filename_change.set(settings.get("no_filename_change", False))
                for fmt, value in settings.get("formats", {}).items():
                    if fmt in self.formats:
                        self.formats[fmt].set(value)
                for mtd, value in settings.get("metadata", {}).items():
                    if mtd in self.metadata:
                        self.metadata[mtd].set(value)
                logging.info("Settings loaded from mporama_settings.json")
        except Exception as e:
            logging.error(f"Error loading settings: {e}")

    def save_settings(self, *args):
        """Save user settings to a JSON file."""
        try:
            settings = {
                "input_dir": self.input_dir.get(),
                "output_dir": self.output_dir.get(),
                "include_subdirs": self.include_subdirs.get(),
                "save_in_root": self.save_in_root.get(),
                "separate_formats": self.separate_formats.get(),
                "no_filename_change": self.no_filename_change.get(),
                "formats": {fmt: var.get() for fmt, var in self.formats.items()},
                "metadata": {mtd: var.get() for mtd, var in self.metadata.items()}
            }
            with open(self.settings_file, "w") as f:
                json.dump(settings, f, indent=4)
            logging.info("Settings saved to mporama_settings.json")
        except Exception as e:
            logging.error(f"Error saving settings: {e}")

    def select_all_metadata(self):
        """Select all metadata retention options."""
        for var in self.metadata.values():
            var.set(True)
        logging.info("All metadata options selected")

    def select_none_metadata(self):
        """Deselect all metadata retention options."""
        for var in self.metadata.values():
            var.set(False)
        logging.info("All metadata options deselected")

    def browse_input(self):
        """Open a folder selection dialog for the input directory and update file count."""
        folder = filedialog.askdirectory()
        if folder:
            self.input_dir.set(folder)
            default_output = os.path.join(folder, "_x2")
            self.output_dir.set(default_output)
            self.progress["value"] = 0
            self.label_elapsed.config(text="Elapsed: 0s")
            self.label_remaining.config(text="Estimated remaining: --")
            self.label_processed.config(text="Processed: 0")
            self.label_total.config(text="Total: --")
            self.update_file_count()
            logging.info(f"Input directory selected: {folder}")

    def browse_output(self):
        """Open a folder selection dialog for the output directory."""
        folder = filedialog.askdirectory()
        if folder:
            self.output_dir.set(folder)
            logging.info(f"Output directory selected: {folder}")

    def toggle_subdir_options(self):
        """Enable or disable subdirectory radio buttons and update file count."""
        if self.include_subdirs.get():
            self.radio_root.config(state="normal")
            self.radio_subdirs.config(state="normal")
        else:
            self.radio_root.config(state="disabled")
            self.radio_subdirs.config(state="disabled")
        self.update_file_count()
        logging.info(f"Include subdirectories toggled: {self.include_subdirs.get()}")

    def update_file_count(self):
        """Update the displayed count of .mpo files in the input directory."""
        input_dir = self.input_dir.get()
        if not input_dir:
            self.label_file_count.config(text="Total .mpo files: 0")
            return
        try:
            mpo_files = []
            if self.include_subdirs.get():
                for root, _, files in os.walk(input_dir):
                    mpo_files.extend(os.path.join(root, f) for f in files if f.lower().endswith(".mpo"))
            else:
                mpo_files = [os.path.join(input_dir, f) for f in os.listdir(input_dir) if f.lower().endswith(".mpo")]
            self.label_file_count.config(text=f"Total .mpo files: {len(mpo_files)}")
            logging.info(f"Updated file count: {len(mpo_files)} .mpo files")
        except Exception as e:
            self.label_file_count.config(text="Total .mpo files: Error")
            logging.error(f"Error updating file count: {e}")

    def confirm_close(self):
        """Confirm closing the application if processing is in progress."""
        if 0 < self.progress["value"] < 100:
            if not messagebox.askyesno("Work in progress:", "Are you sure you want to close?"):
                return
        if self.exiftool:
            self.exiftool.close()
        self.save_settings()
        logging.info("Application closed")
        self.root.destroy()

    def pause_or_continue(self):
        """Toggle between pausing and resuming the processing task."""
        if self.pause_event.is_set():
            self.pause_event.clear()
            self.pause_label.set("Continue")
            self.pause_start_time[0] = time.time()
            self.start_button.config(state="disabled")
            logging.info("Processing paused")
        else:
            self.pause_event.set()
            self.pause_label.set("Pause")
            if self.pause_start_time[0] is not None:
                self.total_paused_time[0] += time.time() - self.pause_start_time[0]
                self.pause_start_time[0] = None
            self.start_button.config(state="normal")
            logging.info("Processing resumed")

    def update_progress(self, value, elapsed=None, remaining=None, processed=None, total=None):
        """Update the progress bar and status labels.

        Args:
            value (float): Progress percentage (0-100).
            elapsed (float, optional): Elapsed time in seconds.
            remaining (float, optional): Estimated remaining time in seconds.
            processed (int, optional): Number of files processed.
            total (int, optional): Total number of files to process.
        """
        self.progress["value"] = value
        if elapsed is not None:
            self.label_elapsed.config(text=f"Elapsed: {int(elapsed)}s")
        if remaining is not None:
            self.label_remaining.config(text=f"Estimated remaining: {int(remaining)}s" if remaining >= 0 else "Estimated remaining: --")
        if processed is not None:
            self.label_processed.config(text=f"Processed: {processed}")
        if total is not None:
            self.label_total.config(text=f"Total: {total}")
        self.root.update_idletasks()

    def create_anaglyph(self, left_img, right_img):
        """Create an anaglyph image from left and right stereo images.

        Args:
            left_img (PIL.Image): Left stereo image.
            right_img (PIL.Image): Right stereo image.

        Returns:
            PIL.Image: Anaglyph image combining red from left and green/blue from right.
        """
        left_array = np.array(left_img.convert("RGB"))
        right_array = np.array(right_img.convert("RGB"))
        anaglyph = np.zeros_like(left_array)
        anaglyph[:,:,0] = left_array[:,:,0]
        anaglyph[:,:,1] = right_array[:,:,1]
        anaglyph[:,:,2] = right_array[:,:,2]
        return Image.fromarray(anaglyph)

    def create_crossview(self, left_img, right_img):
        """Create a crossview stereogram (right image on left, left image on right).

        Args:
            left_img (PIL.Image): Left stereo image.
            right_img (PIL.Image): Right stereo image.

        Returns:
            PIL.Image: Crossview stereogram image.
        """
        width, height = left_img.size
        crossview = Image.new("RGB", (width * 2, height))
        crossview.paste(right_img, (0, 0))
        crossview.paste(left_img, (width, 0))
        return crossview

    def create_parallel(self, left_img, right_img):
        """Create a parallel view stereogram (left image on left, right image on right).

        Args:
            left_img (PIL.Image): Left stereo image.
            right_img (PIL.Image): Right stereo image.

        Returns:
            PIL.Image: Parallel view stereogram image.
        """
        width, height = left_img.size
        parallel = Image.new("RGB", (width * 2, height))
        parallel.paste(left_img, (0, 0))
        parallel.paste(right_img, (width, 0))
        return parallel

    def create_lrl(self, left_img, right_img):
        """Create a left-right-left stereogram.

        Args:
            left_img (PIL.Image): Left stereo image.
            right_img (PIL.Image): Right stereo image.

        Returns:
            PIL.Image: Left-right-left stereogram image.
        """
        width, height = left_img.size
        lrl = Image.new("RGB", (width * 3, height))
        lrl.paste(left_img, (0, 0))
        lrl.paste(right_img, (width, 0))
        lrl.paste(left_img, (width * 2, 0))
        return lrl

    def get_metadata(self, mpo_path):
        """Extract selected metadata from an .mpo file using ExifTool.

        Args:
            mpo_path (str): Path to the .mpo file.

        Returns:
            dict: Dictionary containing selected metadata (Exif, IPTC, XMP).
        """
        metadata = {}
        try:
            with ExifToolHelper() as et:
                all_metadata = et.get_metadata(mpo_path)[0]
                if self.metadata["exif"].get():
                    exif_data = {k: v for k, v in all_metadata.items() if k.startswith("EXIF:")}
                    if exif_data:
                        metadata["exif"] = exif_data
                if self.metadata["iptc"].get():
                    iptc_data = {k: v for k, v in all_metadata.items() if k.startswith("IPTC:")}
                    if iptc_data:
                        metadata["iptc"] = iptc_data
                    else:
                        logging.info(f"No IPTC data found in {mpo_path}")
                if self.metadata["xmp"].get():
                    xmp_data = {k: v for k, v in all_metadata.items() if k.startswith("XMP:")}
                    if xmp_data:
                        metadata["xmp"] = xmp_data
                    else:
                        logging.info(f"No XMP data found in {mpo_path}")
        except Exception as e:
            logging.error(f"Error extracting metadata from {mpo_path}: {e}")
        return metadata

    def save_image_with_metadata(self, output_img, output_path, metadata):
        """Save an image with selected metadata using ExifTool.

        Args:
            output_img (PIL.Image): Image to save.
            output_path (str): Path to save the image.
            metadata (dict): Dictionary containing metadata to retain (Exif, IPTC, XMP).
        """
        try:
            # Save image without metadata first
            output_img.save(output_path, quality=95)
            # Apply metadata using ExifTool
            params = []
            if "exif" in metadata:
                params.extend([f"-EXIF:{k}={v}" for k, v in metadata["exif"].items()])
            if "iptc" in metadata:
                params.extend([f"-IPTC:{k}={v}" for k, v in metadata["iptc"].items()])
            if "xmp" in metadata:
                params.extend([f"-XMP:{k}={v}" for k, v in metadata["xmp"].items()])
            if params:
                with ExifToolHelper() as et:
                    et.set_tags([output_path], params, params_mode="append")
            logging.info(f"Saved image with metadata at {output_path}: {list(metadata.keys())}")
        except Exception as e:
            logging.error(f"Error saving metadata for {output_path}: {e}")
            # Ensure image is saved even if metadata fails
            output_img.save(output_path, quality=95)

    def process_mpo(self, mpo_path, output_dir, processed, total_files, start_time):
        """Process an .mpo file to generate selected stereogram formats.

        Args:
            mpo_path (str): Path to the .mpo file.
            output_dir (str): Output directory for saving generated images.
            processed (list): List containing a single integer tracking processed files.
            total_files (int): Total number of files to process.
            start_time (float): Start time of processing for progress tracking.
        """
        try:
            with Image.open(mpo_path) as img:
                img.seek(0)
                left_img = img.copy()
                metadata = self.get_metadata(mpo_path) if any(self.metadata[m].get() for m in self.metadata) else {}
                img.seek(1)
                right_img = img.copy()

            filename = os.path.splitext(os.path.basename(mpo_path))[0]
            format_dirs = {
                "anaglyph": "rc",
                "crossview": "xi",
                "parallel": "ii",
                "lrl": "lrl",
                "left": "l",
                "right": "r"
            }
            format_prefixes = {
                "anaglyph": "rc_",
                "crossview": "xi_",
                "parallel": "ii_",
                "lrl": "lrl_",
                "left": "_l",
                "right": "_r"
            }

            # Create only the necessary format folders
            if self.separate_formats.get():
                for fmt, var in self.formats.items():
                    if var.get():
                        os.makedirs(os.path.join(output_dir, format_dirs[fmt]), exist_ok=True)
            else:
                os.makedirs(output_dir, exist_ok=True)

            # Generate selected formats
            for fmt, var in self.formats.items():
                if not var.get():
                    continue
                # Determine filename based on no_filename_change option
                if self.separate_formats.get() and self.no_filename_change.get():
                    output_filename = f"{filename}.jpg"
                else:
                    output_filename = f"{format_prefixes[fmt]}{filename}.jpg" if fmt in ["anaglyph", "crossview", "parallel", "lrl"] else f"{filename}{format_prefixes[fmt]}.jpg"
                output_path = os.path.join(output_dir, output_filename)
                if self.separate_formats.get():
                    output_path = os.path.join(output_dir, format_dirs[fmt], output_filename)
                
                logging.info(f"Generating {fmt} for {mpo_path} at {output_path}")
                if fmt == "anaglyph":
                    output_img = self.create_anaglyph(left_img, right_img)
                elif fmt == "crossview":
                    output_img = self.create_crossview(left_img, right_img)
                elif fmt == "parallel":
                    output_img = self.create_parallel(left_img, right_img)
                elif fmt == "lrl":
                    output_img = self.create_lrl(left_img, right_img)
                elif fmt == "left":
                    output_img = left_img
                elif fmt == "right":
                    output_img = right_img
                else:
                    continue

                self.save_image_with_metadata(output_img, output_path, metadata)
                processed[0] += 1
                value = min(100, (processed[0] / total_files) * 100)
                now = time.time()
                elapsed = max(0, now - start_time - self.total_paused_time[0])
                remaining = (elapsed / value * 100) - elapsed if value > 0 else -1
                self.root.after(0, self.update_progress, value, elapsed, remaining, processed[0], total_files)

            logging.info(f"Processed {mpo_path} (Progress: {processed[0]}/{total_files})")

        except Exception as e:
            logging.error(f"Error processing {mpo_path}: {e}")

    def start_processing(self):
        """Start processing .mpo files in a background thread."""
        input_dir = self.input_dir.get()
        output_dir = self.output_dir.get()
        if not input_dir or not output_dir:
            messagebox.showerror("Error", "Please select input and output directories.")
            logging.error("Processing aborted: Missing input or output directory")
            return
        if not any(f.get() for f in self.formats.values()):
            messagebox.showerror("Error", "Please select at least one output format.")
            logging.error("Processing aborted: No output formats selected")
            return

        # Initialize ExifTool
        try:
            self.exiftool = ExifToolHelper()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to initialize ExifTool: {e}. Ensure ExifTool is installed and in PATH.")
            logging.error(f"ExifTool initialization failed: {e}")
            return

        metadata_settings = [m for m, v in self.metadata.items() if v.get()]
        logging.info(f"Starting processing with metadata retention: {metadata_settings}")

        def task():
            self.start_button.config(state="disabled")
            start_time = time.time()
            processed = [0]
            mpo_files = []
            if self.include_subdirs.get():
                for root, _, files in os.walk(input_dir):
                    mpo_files.extend(os.path.join(root, f) for f in files if f.lower().endswith(".mpo"))
            else:
                mpo_files = [os.path.join(input_dir, f) for f in os.listdir(input_dir) if f.lower().endswith(".mpo")]
            
            num_formats = sum(1 for var in self.formats.values() if var.get())
            total_files = len(mpo_files) * num_formats if num_formats > 0 else 0
            self.root.after(0, self.update_progress, 0, 0, None, 0, total_files)
            logging.info(f"Starting processing of {len(mpo_files)} .mpo files with {num_formats} formats (Total: {total_files} outputs)")

            for mpo_file in mpo_files:
                while not self.pause_event.is_set():
                    time.sleep(0.1)
                if self.include_subdirs.get() and not self.save_in_root.get():
                    rel_path = os.path.relpath(os.path.dirname(mpo_file), input_dir)
                    target_dir = os.path.join(output_dir, rel_path) if rel_path != "." else output_dir
                else:
                    target_dir = output_dir
                self.process_mpo(mpo_file, target_dir, processed, total_files, start_time)

            self.exiftool.close()
            elapsed = time.time() - start_time - self.total_paused_time[0]
            self.root.after(0, self.update_progress, 100, elapsed, 0, processed[0], total_files)
            self.root.after(0, lambda: messagebox.showinfo("Success", "Processing completed!"))
            self.root.after(0, lambda: self.start_button.config(state="normal"))
            logging.info(f"Processing completed: {processed[0]} files processed in {int(elapsed)}s")

        threading.Thread(target=task, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = MPOramaApp(root)
    root.mainloop()