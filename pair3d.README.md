# pair3d - Stereo Image Sorter

**pair3d** is a Python utility for sorting stereo image pairs in a folder based on file modification timestamps and perceptual image similarity. It organizes paired images into `_pairs` subfolders and unpaired images into `_singles` subfolders. Optionally, it can move paired images to a duplicated directory structure (`_x2_[folder]`) and rename the source folder to `[folder]_singles`. The application features a user-friendly Tkinter GUI with a red-cyan theme inspired by anaglyph stereo glasses.

## Features

- **Stereo Pair Detection**: Identifies image pairs using timestamp differences (default: 2 seconds) and perceptual hash similarity (default: 10).
- **Folder Organization**: Moves pairs to `_pairs` subfolders and singles to `_singles` subfolders within the source directory.
- **Optional Moving**: Moves `_pairs` to a new `_x2_[folder]` structure (to root or subdirectories) and `_singles` to their immediate parent, renaming the source folder.
- **Recursive Processing**: Supports processing of subfolders with an option to include existing `_singles` folders.
- **GUI Interface**:
  - Browse and select folders.
  - View folder contents in a listbox.
  - Adjust time and hash difference thresholds.
  - Monitor progress with a progress bar, elapsed time, estimated remaining time, and file counts.
  - Pause/continue sorting and exit with confirmation during processing.
  - Displays a custom window icon (`pair3d.ico`) on supported platforms.
- **Logging**: Records operations to `pair3d_log.txt` in both the application directory and the source folder.
- **Settings Persistence**: Saves the last used folder in `pair3d_settings.json`.

## Requirements

- Python 3.6 or higher
- Required Python packages:
  - `Pillow` (for image processing)
  - `imagehash` (for perceptual hashing)
- Tkinter (usually included with Python; ensure it's installed)
- A `pair3d.ico` file in the `imgs` subdirectory for the window icon (optional, for Windows)

## Installation

1. **Clone or Download**:
   Clone the repository or download the `pair3d.py` script and the `imgs/pair3d.ico` file (if using the window icon).

   ```bash
   git clone <repository-url>
   cd pair3d
   ```

2. **Install Dependencies**:
   Install the required Python packages using pip:

   ```bash
   pip install Pillow imagehash
   ```

3. **Verify Tkinter**:
   Ensure Tkinter is available by running:

   ```bash
   python -m tkinter
   ```

   If Tkinter is not installed, install it (e.g., on Ubuntu: `sudo apt-get install python3-tk`).

4. **Place Icon File** (optional):
   If using the window icon, place `pair3d.ico` in an `imgs` subdirectory relative to `pair3d.py`.

## Usage

1. **Run the Application**:
   Execute the script to launch the GUI:

   ```bash
   python pair3d.py
   ```

2. **GUI Instructions**:
   - **Select Folder**: Click "Browse" to choose a directory containing images (`.jpg`, `.jpeg`, `.png`).
   - **Configure Options**:
     - Check "Process subfolders" to include subdirectories.
     - Check "Include '_singles' folders" to reprocess existing `_singles` folders.
     - Check "Move to '_x2_[folder]'" to enable moving pairs to a new directory structure.
     - If moving is enabled with subfolders, select "To root" or "To subdir's" for pair destination.
     - Adjust "Time diff (s)" and "Hash diff" thresholds as needed.
   - **View Contents**: The listbox displays images grouped by subfolder.
   - **Start Sorting**: Click "Start" to begin sorting. Monitor progress via the progress bar and labels.
   - **Pause/Continue**: Click "Pause" to pause sorting; click "Continue" to resume.
   - **Exit**: Click "Exit" to close the app, with a confirmation prompt if sorting is in progress.

3. **Output**:
   - Paired images are moved to `_pairs` subfolders.
   - Unpaired images are moved to `_singles` subfolders.
   - If moving is enabled, pairs are moved to `_x2_[folder]`, singles to their parent directory, and the source folder is renamed to `[folder]_singles`.
   - Logs are saved as `pair3d_log.txt` in the application directory and the source folder.

## Example

For a folder `/photos` with images:
- After sorting, pairs are in `/photos/_pairs` and singles in `/photos/_singles`.
- If moving is enabled, pairs are moved to `/photos_x2` (or subdirectories), singles to `/photos`, and `/photos` is renamed to `/photos_singles`.

## Notes

- **Platform Compatibility**: The window icon (`pair3d.ico`) is supported primarily on Windows. On macOS/Linux, it may be ignored.
- **Settings**: The last selected folder is saved in `pair3d_settings.json` in the application directory (e.g., `~/.config/pair3d` or the script directory).
- **Error Handling**: The app handles file access errors and prompts for confirmation when overwriting existing destinations or processing `_singles`-named folders.
- **Performance**: Sorting large folders may take time due to image similarity comparisons. Adjust thresholds to balance accuracy and speed.

## License

This software is released under the MIT License. See the header of `pair3d.py` for details.

## Acknowledgments

Inspired by an AI prompt from 2025, with contributions from ChatGPT, Perplexity AI, and Copilot AI.