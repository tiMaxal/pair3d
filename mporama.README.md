# MPOrama - Stereogram Converter

MPOrama is a Python-based GUI application for converting .mpo stereo image files into various stereogram formats, such as anaglyph, crossview, parallel, left-right-left, left, and right images. It provides a user-friendly interface to select input and output directories, choose output formats, and manage subdirectory processing. The application supports organizing outputs into format-specific folders, with options to control filename conventions, and includes progress tracking, pause/resume functionality, and logging.

## Features

- **Input/Output Selection**: Select input folder containing .mpo files and output folder (defaults to `_x2` in the input directory).
- **Stereogram Formats**: Generate anaglyph (`rc`), crossview (`xi`), parallel (`ii`), left-right-left (`lrl`), left (`l`), and right (`r`) images.
- **Subdirectory Support**: Process .mpo files in subdirectories with options to save outputs in the root output folder or respective subdirectories.
- **Format Folder Organization**: Save outputs in format-specific folders (e.g., `_x2/rc/`, `_x2/xi/`), with an option to use original filenames without prefixes/suffixes.
- **Progress Tracking**: Displays a progress bar, elapsed time, estimated time remaining, and processed/total file counts.
- **Pause/Resume**: Pause and resume processing with accurate time tracking.
- **Logging**: Logs key events and errors to `mporama.log` in the application directory.
- **User Interface**: Styled with a lightcoral background, blue text, light-blue input/output fields, and buttons (limegreen Start, gold Pause/Continue, red Exit).

## Requirements

- **Python 3.6+**
- **Pillow**: For image processing (`pip install Pillow`)
- **Tkinter**: Included with standard Python installations for the GUI

## Installation

1. Ensure Python 3.6 or higher is installed on your system.
2. Install the Pillow library:
   ```bash
   pip install Pillow
   ```
3. Download or clone the MPOrama repository to your local machine.
4. Place the `mporama.py` script in your desired directory.

## Usage

1. **Run the Application**:
   ```bash
   python mporama.py
   ```
   This launches the GUI window titled "MPOrama - Stereogram Converter".

2. **Select Input Directory**:
   - Click the "Browse" button next to "Select folder containing .mpo files".
   - Choose a folder containing .mpo files. The total number of .mpo files is displayed below.

3. **Select Output Directory**:
   - Click the "Browse" button next to "Select output folder".
   - Choose an output folder (defaults to `<input_folder>/_x2`).

4. **Configure Options**:
   - **Include Subdirectories**: Check to process .mpo files in subfolders.
   - **Save in Root Output Folder** or **Save in Respective Subdirectories**: Select how outputs are organized when processing subdirectories (enabled only if "Include Subdirectories" is checked).
   - **Separate to Format Folders**: Check to save outputs in format-specific folders (e.g., `_x2/rc/`, `_x2/xi/`).
   - **No Filename Change**: Check to use original filenames (e.g., `image.jpg`) in format folders instead of adding prefixes/suffixes (e.g., `rc_image.jpg`).
   - **Output Formats**: Select desired formats (Anaglyph, Crossview, Parallel, Left-Right-Left, Left, Right).

5. **Start Processing**:
   - Click the "Start" button to begin converting .mpo files.
   - Use the "Pause"/"Continue" button to pause or resume processing.
   - Monitor progress via the progress bar, elapsed time, estimated remaining time, and file counts.

6. **Exit**:
   - Click "Exit" to close the application. If processing is in progress, a confirmation prompt appears.

## Output Structure

- **Without Separate to Format Folders**:
  - Outputs are saved directly in the output directory (e.g., `_x2/rc_image.jpg`, `_x2/image_l.jpg`).
- **With Separate to Format Folders**:
  - Outputs are saved in format-specific subfolders (e.g., `_x2/rc/image.jpg`, `_x2/xi/image.jpg` if "No Filename Change" is checked, or `_x2/rc/rc_image.jpg`, `_x2/xi/xi_image.jpg` otherwise).
- **With Subdirectories**:
  - If "Save in Respective Subdirectories" is selected, outputs mirror the input folder structure within the output directory.

## Logging

- A log file (`mporama.log`) is created in the same directory as the script or executable.
- It records events such as directory selections, processing steps, and errors with timestamps.

## Notes

- **MPO Files**: The application assumes .mpo files contain two images (left and right views), standard for MPO stereo images.
- **Performance**: Processing time depends on the number and size of .mpo files and selected formats.
- **Error Handling**: Errors during processing are logged and do not interrupt the application; check `mporama.log` for details.

## License

This project is licensed under the MIT License. See the license header in `mporama.py` for details.

## Contributing

Contributions are welcome! Please submit issues or pull requests via the repository hosting this project.

## Contact

For questions or support, please open an issue on the repository or contact the developer.

---
*Generated on August 08, 2025*