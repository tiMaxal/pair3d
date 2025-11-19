# pair3d Web - Stereo Image Sorter

**pair3d Web** is a web-based utility for sorting stereo image pairs from uploaded ZIP files containing images. It detects pairs based on file modification timestamps and perceptual image similarity, organizing them into `_pairs` and `_singles` folders. Optionally, it moves `_pairs` to a `_x2_[folder]` structure and `_singles` to their parent directory, renaming the source folder to `[folder]_singles`. The app features a browser-based interface built with Flask, Flask-SocketIO, and HTML/CSS/JavaScript, styled with a red-cyan theme inspired by anaglyph stereo glasses.

## Features

- **Stereo Pair Detection**: Identifies image pairs using timestamp differences (default: 2 seconds) and perceptual hash similarity (default: 10).
- **Folder Organization**: Moves pairs to `_pairs` folders and singles to `_singles` folders within the uploaded structure.
- **Optional Moving**: Moves `_pairs` to a `_x2_[folder]` structure (to root or subdirectories) and `_singles` to their parent, renaming the source folder.
- **Recursive Processing**: Supports processing subfolders with an option to include existing `_singles` folders.
- **Web Interface**:
  - Upload ZIP files containing images.
  - View file lists grouped by subfolder.
  - Configure options (subfolders, singles inclusion, moving, thresholds).
  - Monitor progress with a progress bar, elapsed time, estimated remaining time, and file counts.
  - Real-time log and result updates via WebSocket.
  - Download processed results as a ZIP file.
- **Logging**: Records operations to `pair3d_log.txt` in the application directory and the processed folder structure.
- **Settings Persistence**: Saves the last uploaded folder name in `pair3d_settings.json`.

## Requirements

- Python 3.6 or higher
- Required Python packages:
  - `Flask` (web framework)
  - `Flask-SocketIO` (real-time updates)
  - `Pillow` (image processing)
  - `imagehash` (perceptual hashing)
- A modern web browser (e.g., Chrome, Firefox) for the interface.

## Installation

1. **Clone or Download**:
   Clone the repository or download `pair3d_web.py` and the `templates/index.html` file.

   ```bash
   git clone <repository-url>
   cd pair3d
   ```

2. **Install Dependencies**:
   Install required Python packages using pip:

   ```bash
   pip install flask flask-socketio Pillow imagehash
   ```

3. **Directory Structure**:
   Ensure the following structure:
   ```
   pair3d/
   ├── pair3d_web.py
   ├── templates/
   │   └── index.html
   ```

## Usage

1. **Run the Application**:
   Start the Flask server:

   ```bash
   python pair3d_web.py
   ```

   Access the app at `http://localhost:5000` in your browser.

2. **Web Interface Instructions**:
   - **Upload Folder**: Select a ZIP file containing images (`.jpg`, `.jpeg`, `.png`) using the file input.
   - **Configure Options**:
     - Check "Process subfolders" to include subdirectories in the ZIP.
     - Check "Include '_singles' folders" to reprocess existing `_singles` folders.
     - Check "Move to '_x2_[folder]'" to enable moving pairs to a new structure.
     - If moving and subfolders are enabled, select "To root" or "To subdir's" for pair destination.
     - Adjust "Time diff (s)" and "Hash diff" thresholds as needed.
   - **View Files**: The file list updates to show images grouped by subfolder.
   - **Start Processing**: Click "Start" to begin sorting. Monitor progress via the progress bar, logs, and results.
   - **Download Results**: After processing, a ZIP file (`pair3d_output.zip`) is automatically downloaded, containing `_pairs`, `_singles`, and optionally `_x2_[folder]` structures.

3. **Output**:
   - Paired images are organized into `_pairs` folders and unpaired images into `_singles` folders.
   - If moving is enabled, pairs are moved to `_x2_[folder]` (root or subdirectories), singles to their parent, and the source folder is renamed to `[folder]_singles`.
   - Logs are included in the output ZIP and saved to the application directory.

## Example

1. Upload a ZIP file containing a folder `/photos` with images.
2. After processing:
   - Pairs are in `/photos/_pairs`, singles in `/photos/_singles`.
   - If moving is enabled, pairs are in `/photos_x2` (or subdirectories), singles in `/photos`, and the source is renamed to `/photos_singles`.
3. Download `pair3d_output.zip` to access the organized structure.

## Key Changes from Desktop Version (`pair3d.v3.py`)

The web version (`pair3d_web.py`) adapts the original Tkinter-based desktop app to a browser-based environment. Key changes include:

1. **Interface**:
   - **Desktop**: Tkinter GUI with a red-cyan theme, folder picker, listbox, progress bar, and buttons.
   - **Web**: HTML/CSS/JavaScript interface with similar styling, using a file input for ZIP uploads, a scrollable file list, and WebSocket-driven progress updates.
   - **Impact**: The web interface is accessible without Python installation but requires uploading ZIP files instead of selecting folders directly.

2. **File Handling**:
   - **Desktop**: Uses `os` and `shutil` for direct file system access via Tkinter’s `filedialog.askdirectory`.
   - **Web**: Processes uploaded ZIP files, extracting them server-side to a temporary directory and returning a ZIP of results.
   - **Impact**: ZIP-based workflow is less intuitive than folder selection but necessary due to browser security restrictions.

3. **Real-Time Updates**:
   - **Desktop**: Updates GUI elements (progress bar, listbox) directly via Tkinter’s event loop.
   - **Web**: Uses Flask-SocketIO for real-time progress, log, and result updates to the browser.
   - **Impact**: Achieves similar feedback but requires WebSocket setup, adding complexity.

4. **Settings**:
   - **Desktop**: Saves the last selected folder path in `pair3d_settings.json`.
   - **Web**: Saves the last uploaded ZIP filename, displayed for reference but less actionable in a web context.
   - **Impact**: Settings are less persistent due to the stateless nature of web apps.

5. **Window Icon**:
   - **Desktop**: Sets a custom `pair3d.ico` icon for the Tkinter window (Windows-only).
   - **Web**: No window icon; browser tabs use default favicon (not implemented in this version).
   - **Impact**: Minor loss of branding, as web apps rely on browser or favicon customization.

## Limitations Compared to Desktop Version

1. **Folder Upload**:
   - **Issue**: Browsers restrict direct folder access, requiring users to upload a ZIP file instead of selecting a folder via a native dialog.
   - **Workaround**: Users must manually create a ZIP of their folder, which adds a preparation step not present in the desktop version.
   - **Impact**: Less user-friendly for non-technical users accustomed to folder selection.

2. **Pause/Continue Functionality**:
   - **Issue**: The desktop version’s pause/continue feature (via a button) is not implemented in the web version due to complexity in managing server-side processing states.
   - **Workaround**: Users must wait for processing to complete without interruption.
   - **Impact**: Reduced control during long-running processes, especially for large image sets.

3. **Confirmation Dialogs**:
   - **Issue**: Desktop confirmation dialogs (e.g., for `_singles` folder or overwrite prompts) are not fully implemented in the web version due to WebSocket-based confirmation challenges.
   - **Workaround**: The demo assumes cancellation for such cases; production versions need additional client-server interaction.
   - **Impact**: Potential for unexpected behavior if `_singles` or existing destinations are encountered, requiring manual intervention.

4. **Security and Robustness**:
   - **Issue**: The web version lacks production-ready security features (e.g., file size limits, user authentication, temporary file cleanup).
   - **Workaround**: Use on a trusted server with manual cleanup of temporary files.
   - **Impact**: Not suitable for public deployment without enhancements; desktop version is inherently more secure for local use.

5. **Performance**:
   - **Issue**: Server-side processing of large ZIP files may strain resources, and browser-based file uploads are slower than local file access.
   - **Workaround**: Optimize server resources or limit upload sizes in production.
   - **Impact**: Slower for large datasets compared to desktop’s direct file access.

6. **Platform-Specific Features**:
   - **Issue**: The desktop version’s window icon and native folder picker are not replicable in a browser, and favicon support is not implemented.
   - **Workaround**: Add a favicon for branding in future versions.
   - **Impact**: Minor loss of visual consistency and native OS integration.

## Notes

- **Browser Compatibility**: Tested with modern browsers (Chrome, Firefox). Some features (e.g., file uploads) may vary by browser.
- **Temporary Files**: Processed files are stored in a temporary directory; ensure sufficient disk space and implement cleanup for production use.
- **Scalability**: The demo is single-user; production use requires handling concurrent uploads and sessions.
- **Logging**: Logs are saved in the output ZIP and application directory (`~/.config/pair3d/pair3d_log.txt`).

## License

This software is released under the MIT License. See the header of `pair3d_web.py` for details.

## Acknowledgments

Adapted from the original `pair3d.v3.py` desktop app, inspired by an AI prompt from 2025, with contributions from ChatGPT, Perplexity AI, and Copilot AI.