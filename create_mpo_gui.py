import os
import exiftool
import tkinter as tk
from tkinter import filedialog, messagebox
from uuid import uuid4
import logging
import glob
from datetime import datetime
import shutil
import subprocess

# Set up logging (file and console)
log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mpo_creation.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()  # Console output
    ]
)
logger = logging.getLogger(__name__)

class MPOCreatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MPO Creator for StereoPhoto Maker")
        self.root.geometry("600x400")

        # Variables for file paths
        self.left_image = tk.StringVar()
        self.right_image = tk.StringVar()
        self.input_folder = tk.StringVar()
        self.output_folder = tk.StringVar()

        # GUI elements
        tk.Label(root, text="MPO Creator", font=("Arial", 14)).pack(pady=10)

        tk.Label(root, text="Left Image:").pack()
        tk.Entry(root, textvariable=self.left_image, width=50).pack()
        tk.Button(root, text="Browse", command=self.browse_left).pack()

        tk.Label(root, text="Right Image:").pack()
        tk.Entry(root, textvariable=self.right_image, width=50).pack()
        tk.Button(root, text="Browse", command=self.browse_right).pack()

        tk.Label(root, text="Input Folder (for multiple pairs):").pack()
        tk.Entry(root, textvariable=self.input_folder, width=50).pack()
        tk.Button(root, text="Browse", command=self.browse_input_folder).pack()

        tk.Label(root, text="Output Folder:").pack()
        tk.Entry(root, textvariable=self.output_folder, width=50).pack()
        tk.Button(root, text="Browse", command=self.browse_output_folder).pack()

        tk.Button(root, text="Start", command=self.start_processing, bg="green", fg="white").pack(pady=10)
        tk.Button(root, text="Exit", command=self.exit_app, bg="red", fg="white").pack(pady=5)

    def browse_left(self):
        file = filedialog.askopenfilename(filetypes=[("JPEG files", "*.jpg")])
        if file:
            self.left_image.set(file)
            logger.info(f"Selected left image: {file}")

    def browse_right(self):
        file = filedialog.askopenfilename(filetypes=[("JPEG files", "*.jpg")])
        if file:
            self.right_image.set(file)
            logger.info(f"Selected right image: {file}")

    def browse_input_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.input_folder.set(folder)
            logger.info(f"Selected input folder: {folder}")

    def browse_output_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_folder.set(folder)
            logger.info(f"Selected output folder: {folder}")

    def create_mpo(self, left_image_path, right_image_path, output_mpo_path):
        temp_left = None
        temp_right = None
        temp_mpo = None
        try:
            # Normalize paths
            left_image_path = os.path.normpath(left_image_path)
            right_image_path = os.path.normpath(right_image_path)
            output_mpo_path = os.path.normpath(output_mpo_path)

            # Verify input files exist
            if not (os.path.exists(left_image_path) and os.path.exists(right_image_path)):
                raise FileNotFoundError(f"Input image(s) not found: {left_image_path}, {right_image_path}")

            # Ensure output directory exists and is writable
            output_dir = os.path.dirname(output_mpo_path)
            os.makedirs(output_dir, exist_ok=True)
            if not os.access(output_dir, os.W_OK):
                raise PermissionError(f"No write permission for output directory: {output_dir}")
            logger.info(f"Ensured output directory exists and is writable: {output_dir}")

            # Get sizes of input images
            left_size = os.path.getsize(left_image_path)
            right_size = os.path.getsize(right_image_path)
            logger.info(f"Image sizes - Left: {left_size} bytes, Right: {right_size} bytes")

            # Create temporary copies of input files to avoid modifying originals
            temp_left = os.path.join(output_dir, f"temp_left_{uuid4().hex}.jpg")
            temp_right = os.path.join(output_dir, f"temp_right_{uuid4().hex}.jpg")
            shutil.copy2(left_image_path, temp_left)
            shutil.copy2(right_image_path, temp_right)
            logger.info(f"Created temporary copies: {temp_left}, {temp_right}")

            # Prepare MPF tags for SPM compatibility
            mpf_tags = {
                'MPF:MPFVersion': '0100',
                'MPF:NumberOfImages': 2,
                'MPF:MPEntry': (
                    # First image (left): Attribute (0x00000000 = primary), size, offset
                    b'\x00\x00\x00\x00' +
                    left_size.to_bytes(4, byteorder='big') +
                    b'\x00\x00\x00\x00' +  # Offset for first image (0)
                    b'\x00\x00\x00\x00' +  # Dependency (none)
                    # Second image (right): Attribute (0x00020000 = stereo right), size, offset
                    b'\x00\x02\x00\x00' +
                    right_size.to_bytes(4, byteorder='big') +
                    left_size.to_bytes(4, byteorder='big') +  # Offset for second image
                    b'\x00\x00\x00\x00'   # Dependency (none)
                ),
                'MPF:MPType': 'Baseline Stereo Image',
                'EXIF:YCbCrPositioning': 'Co-Sited'  # Match FUJIFILM sample
            }

            # Create temporary concatenated file
            temp_mpo = os.path.join(output_dir, f"temp_{uuid4().hex}.mpo")
            with open(temp_mpo, 'wb') as mpo_file:
                with open(temp_left, 'rb') as left_file:
                    mpo_file.write(left_file.read())
                with open(temp_right, 'rb') as right_file:
                    mpo_file.write(right_file.read())
            logger.info(f"Created temporary MPO file: {temp_mpo}")

            # Use ExifTool to set MPF tags and create final MPO
            with exiftool.ExifToolHelper() as et:
                # Set consistent timestamps and YCbCrPositioning on temporary files
                timestamp = datetime.now().strftime("%Y:%m:%d %H:%M:%S")
                et.set_tags(
                    [temp_left, temp_right],
                    {
                        'EXIF:DateTime': timestamp,
                        'EXIF:DateTimeOriginal': timestamp,
                        'EXIF:DateTimeDigitized': timestamp,
                        'EXIF:YCbCrPositioning': 'Co-Sited'
                    },
                    params=["-overwrite_original"]
                )
                logger.info(f"Set consistent timestamps and YCbCrPositioning for {temp_left} and {temp_right}")

                # Create MPO with MPF tags using subprocess for detailed error capture
                cmd = [
                    "exiftool",
                    f"-MPF:MPFVersion={mpf_tags['MPF:MPFVersion']}",
                    f"-MPF:NumberOfImages={mpf_tags['MPF:NumberOfImages']}",
                    f"-MPF:MPEntry={mpf_tags['MPF:MPEntry'].hex()}",
                    f"-MPF:MPType={mpf_tags['MPF:MPType']}",
                    f"-EXIF:YCbCrPositioning={mpf_tags['EXIF:YCbCrPositioning']}",
                    f"-o",
                    output_mpo_path,
                    temp_mpo
                ]
                logger.info(f"Executing exiftool command: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.error(f"ExifTool execution failed: {result.stderr}")
                    raise Exception(f"ExifTool failed: {result.stderr}")

            # Verify MPO file exists
            if not os.path.exists(output_mpo_path):
                raise FileNotFoundError(f"MPO file was not created at {output_mpo_path}")

            # Log MPF tags for debugging
            with exiftool.ExifToolHelper() as et:
                tags = et.get_tags(output_mpo_path, ['MPF:All', 'EXIF:YCbCrPositioning'])
                logger.info(f"MPO file tags: {tags}")

            logger.info(f"Successfully created MPO file: {output_mpo_path}")
            messagebox.showinfo("Success", f"Created MPO file: {output_mpo_path}")
        except Exception as e:
            logger.error(f"Error creating MPO file {output_mpo_path}: {str(e)}")
            messagebox.showerror("Error", f"Failed to create MPO file: {str(e)}")
        finally:
            for temp_file in [temp_left, temp_right, temp_mpo]:
                if temp_file and os.path.exists(temp_file):
                    os.remove(temp_file)
                    logger.info(f"Cleaned up temporary file: {temp_file}")

    def find_image_pairs(self, folder):
        """Find pairs of images based on EXIF DateTimeDigitized (1–4 seconds, no intervening timestamps)."""
        pairs = []
        files = glob.glob(os.path.join(folder, "*.jpg"))
        files.sort()  # Sort by name
        logger.info(f"Found {len(files)} files in folder: {folder}")
        for f in files:
            logger.info(f"File: {f}")

        # Extract EXIF timestamps
        file_info = []
        with exiftool.ExifToolHelper() as et:
            for file in files:
                try:
                    tags = et.get_tags(file, ['EXIF:DateTimeDigitized', 'EXIF:DateTimeOriginal'])
                    timestamp_str = tags[0].get('EXIF:DateTimeDigitized') or tags[0].get('EXIF:DateTimeOriginal')
                    if timestamp_str:
                        try:
                            timestamp = datetime.strptime(timestamp_str, "%Y:%m:%d %H:%M:%S")
                            file_info.append((file, timestamp))
                            logger.info(f"EXIF timestamp for {file}: {timestamp_str}")
                        except ValueError:
                            logger.warning(f"Invalid EXIF timestamp format in {file}: {timestamp_str}")
                    else:
                        logger.warning(f"No DateTimeDigitized or DateTimeOriginal in {file}")
                except Exception as e:
                    logger.warning(f"Failed to read EXIF for {file}: {str(e)}")

        # Pair files by EXIF timestamp proximity (1–4 seconds, no intervening timestamps)
        file_info.sort(key=lambda x: x[1])  # Sort by timestamp
        i = 0
        while i < len(file_info) - 1:
            file1, ts1 = file_info[i]
            file2, ts2 = file_info[i + 1]
            time_diff = (ts2 - ts1).total_seconds()
            # Check if time difference is 1–4 seconds
            if 1 <= time_diff <= 4:
                # Ensure no other file's timestamp falls between ts1 and ts2
                valid_pair = True
                for _, other_ts in file_info:
                    if other_ts != ts1 and other_ts != ts2 and ts1 < other_ts < ts2:
                        valid_pair = False
                        logger.warning(f"Skipped pairing {file1} and {file2} (intervening timestamp: {other_ts})")
                        break
                if valid_pair:
                    pairs.append((file1, file2))
                    logger.info(f"Paired: {file1} and {file2} (EXIF diff: {time_diff}s)")
                    i += 2
                else:
                    i += 1
            else:
                logger.warning(f"Skipped pairing {file1} and {file2} (EXIF diff: {time_diff}s)")
                i += 1

        logger.info(f"Found {len(pairs)} image pairs in folder: {folder}")
        return pairs

    def start_processing(self):
        if not self.output_folder.get():
            messagebox.showerror("Error", "Please select an output folder")
            logger.error("No output folder selected")
            return

        # Process single image pair if selected
        if self.left_image.get() and self.right_image.get():
            output_mpo = os.path.join(
                self.output_folder.get(),
                f"{os.path.splitext(os.path.basename(self.left_image.get()))[0]}.mpo"
            )
            self.create_mpo(self.left_image.get(), self.right_image.get(), output_mpo)

        # Process multiple pairs if folder is selected
        if self.input_folder.get():
            pairs = self.find_image_pairs(self.input_folder.get())
            if not pairs:
                messagebox.showerror("Error", "No valid image pairs found in the input folder")
                logger.error("No valid image pairs found in the input folder")
                return

            for left, right in pairs:
                output_mpo = os.path.join(
                    self.output_folder.get(),
                    f"{os.path.splitext(os.path.basename(left))[0]}.mpo"
                )
                self.create_mpo(left, right, output_mpo)

    def exit_app(self):
        logger.info("Application exited")
        self.root.quit()

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = MPOCreatorApp(root)
        root.mainloop()
    except Exception as e:
        logger.error(f"Application failed to start: {e}")
        raise