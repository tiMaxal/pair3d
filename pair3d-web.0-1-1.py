# pair3d_web.py
# Copyright (c) 2025 tiMaxal
#
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT

"""
pair3d Web App

A web-based utility for sorting stereo image pairs from uploaded folders or ZIP files.
Pairs are detected based on timestamps and perceptual similarity, organized into '_pairs' and '_singles' folders,
and optionally moved to a '_x2_[folder]' structure. Built with Flask and Flask-SocketIO.
"""

import os
import shutil
import zipfile
import threading
import time
from datetime import datetime
from flask import Flask, render_template, request, send_file
from flask_socketio import SocketIO, emit
from PIL import Image
import imagehash
import json
import tempfile
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()
socketio = SocketIO(app)

TIME_DIFF_THRESHOLD = 2
HASH_DIFF_THRESHOLD = 10
processing = False

def get_app_dir():
    """Get directory for logs and settings."""
    config_dir = os.path.expanduser("~/.config/pair3d")
    os.makedirs(config_dir, exist_ok=True)
    return config_dir

SETTINGS_FILE = os.path.join(get_app_dir(), "pair3d_settings.json")

def load_last_folder():
    """Load last used folder from settings."""
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            settings = json.load(f)
            return settings.get("last_folder", "")
    except (FileNotFoundError, json.JSONDecodeError):
        return ""

def save_last_folder(folder):
    """Save last used folder to settings."""
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump({"last_folder": folder}, f)
    except Exception as e:
        print(f"Failed to save settings: {e}")

def get_image_files(directory, recursive=False, include_singles=False):
    """Retrieve image file paths from directory."""
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
    """Retrieve image files grouped by folder."""
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
    """Get modification timestamp of an image."""
    try:
        return datetime.fromtimestamp(os.path.getmtime(path))
    except Exception:
        return None

def is_similar_image(file1, file2):
    """Check if two images are perceptually similar."""
    try:
        with Image.open(file1) as img1, Image.open(file2) as img2:
            hash1 = imagehash.phash(img1)
            hash2 = imagehash.phash(img2)
        return abs(hash1 - hash2) < HASH_DIFF_THRESHOLD
    except Exception:
        return False

def delete_if_empty(path):
    """Delete folder if empty or contains only .picasa.ini."""
    if os.path.isdir(path):
        contents = os.listdir(path)
        if not contents:
            os.rmdir(path)
        elif contents == ['.picasa.ini']:
            os.remove(os.path.join(path, '.picasa.ini'))
            os.rmdir(path)

def move_contents(src_dir, dst_dir):
    """Move files from src_dir to dst_dir and delete src_dir if empty."""
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

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html', last_folder=load_last_folder())

@app.route('/upload', methods=['POST'])
def upload_folder():
    """Handle folder or ZIP upload."""
    global processing
    if processing:
        return {"error": "Processing already in progress"}, 400

    process_subfolders = request.form.get('process_subfolders', '0') == '1'
    include_singles = request.form.get('include_singles', '0') == '1'
    move_to_x2 = request.form.get('move_to_x2', '0') == '1'
    move_destination = request.form.get('move_destination', 'root')
    try:
        global TIME_DIFF_THRESHOLD, HASH_DIFF_THRESHOLD
        TIME_DIFF_THRESHOLD = max(0.01, float(request.form.get('time_diff', '2')))
        HASH_DIFF_THRESHOLD = max(1, int(request.form.get('hash_diff', '10')))
    except Exception as e:
        return {"error": f"Invalid thresholds: {e}"}, 400

    if 'folder' not in request.files:
        return {"error": "No folder uploaded"}, 400

    file = request.files['folder']
    if not file.filename:
        return {"error": "No file selected"}, 400

    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, secure_filename(file.filename))
    file.save(zip_path)

    src_root = os.path.join(temp_dir, "extracted")
    os.makedirs(src_root, exist_ok=True)

    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(src_root)
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return {"error": f"Failed to extract ZIP: {e}"}, 400

    save_last_folder(file.filename)
    processing = True
    threading.Thread(
        target=process_images,
        args=(src_root, temp_dir, process_subfolders, include_singles, move_to_x2, move_destination),
        daemon=True
    ).start()
    return {"status": "Processing started", "temp_dir": temp_dir}

def process_images(src_root, temp_dir, process_subfolders, include_singles, move_to_x2, move_destination):
    """Process images and emit progress updates."""
    app_log_file = os.path.join(get_app_dir(), "pair3d_log.txt")
    src_log_file = os.path.join(src_root, "pair3d_log.txt")

    def log(msg):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {msg}\n"
        socketio.emit('log', log_message)
        try:
            with open(app_log_file, "a", encoding="utf-8") as f:
                f.write(log_message)
            with open(src_log_file, "a", encoding="utf-8") as f:
                f.write(log_message)
        except Exception as e:
            socketio.emit('log', f"Failed to write log: {e}")

    start_time = time.time()
    folders_dict = get_image_files_by_folder(src_root, recursive=process_subfolders, include_singles=include_singles)
    image_files = [f for files in folders_dict.values() for f in files]
    total_files = len(image_files)
    socketio.emit('progress', {'value': 0, 'processed': 0, 'total': total_files})

    processed = [0]
    def progress_callback(value):
        elapsed = time.time() - start_time
        processed_count = int((value / 100) * total_files)
        processed[0] = processed_count
        remaining = ((elapsed / value) * (100 - value)) if value > 0 else -1
        socketio.emit('progress', {
            'value': value,
            'elapsed': int(elapsed),
            'remaining': int(remaining) if remaining >= 0 else '--',
            'processed': processed_count,
            'total': total_files
        })

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
        progress_callback(min(100, int((i / len(image_files)) * 100)))

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
    socketio.emit('results', {'pairs': num_pairs, 'singles': num_singles})

    # Moving Phase
    if move_to_x2:
        base_name = os.path.basename(src_root)
        if base_name.endswith("_singles"):
            socketio.emit('confirm', {
                'message': f"Source folder '{src_root}' ends with '_singles'. Continue?",
                'action': 'continue_processing'
            })
            return  # Simplified: Assume user cancels for now

        parent_dir = os.path.dirname(src_root)
        dst_root = os.path.join(parent_dir, f"_x2_{base_name}")
        singles_root = os.path.join(parent_dir, f"{base_name}_singles")

        if os.path.exists(dst_root):
            socketio.emit('confirm', {
                'message': f"Destination '{dst_root}' exists. Overwrite?",
                'action': 'overwrite_destination'
            })
            return  # Simplified: Assume user cancels for now

        os.makedirs(dst_root)
        log(f"Processing from: {src_root}")
        log(f"Duplicated tree at: {dst_root}")

        for dirpath, _, _ in os.walk(src_root, topdown=False):
            file_count = len(get_image_files(dirpath, include_singles=True))
            rel_path = os.path.relpath(dirpath, src_root)
            parent_path = os.path.dirname(dirpath)
            parent_rel = os.path.relpath(parent_path, src_root)
            if os.path.basename(dirpath) == '_pairs':
                pair_dest = os.path.join(dst_root, f"{base_name}_pairs") if move_destination == 'root' else \
                            os.path.join(dst_root, parent_rel, f"{os.path.basename(parent_path)}_pairs") if parent_rel != '.' else \
                            os.path.join(dst_root, f"{base_name}_pairs")
                log(f"Moving from _pairs: {dirpath} → {pair_dest}")
                move_contents(dirpath, pair_dest)
                processed[0] += file_count
            elif os.path.basename(dirpath) == '_singles':
                single_dest = src_root if parent_rel == '.' else parent_path
                log(f"Moving from _singles: {dirpath} → {single_dest}")
                move_contents(dirpath, single_dest)
                processed[0] += file_count
            delete_if_empty(dirpath)
            progress_callback(min(100, int((processed[0] / total_files) * 100) if total_files else 100))

        try:
            if os.path.exists(singles_root):
                log(f"Warning: '{singles_root}' exists, merging contents")
                move_contents(src_root, singles_root)
                shutil.rmtree(src_root)
            else:
                os.rename(src_root, singles_root)
            log(f"Renamed source root: {src_root} → {singles_root}")
        except Exception as e:
            log(f"Failed to rename source root: {e}")
            socketio.emit('error', f"Failed to rename source root: {e}")
            return

        log(f"Done. Primary log: {app_log_file}, Source log: {singles_root}/pair3d_log.txt")
        socketio.emit('results', {'moved_to': dst_root, 'renamed_to': singles_root})

    # Create output ZIP
    output_zip = os.path.join(temp_dir, "output.zip")
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, temp_dir)
                zipf.write(file_path, arcname)

    elapsed = time.time() - start_time
    socketio.emit('progress', {
        'value': 100,
        'elapsed': int(elapsed),
        'remaining': 0,
        'processed': total_files,
        'total': total_files
    })
    socketio.emit('download', {'url': f'/download/{os.path.basename(temp_dir)}'})
    global processing
    processing = False

@app.route('/download/<temp_dir>')
def download(temp_dir):
    """Serve the processed output ZIP."""
    zip_path = os.path.join(app.config['UPLOAD_FOLDER'], temp_dir, "output.zip")
    return send_file(zip_path, as_attachment=True, download_name="pair3d_output.zip")

@socketio.on('list_files')
def list_files(data):
    """List files in uploaded folder."""
    temp_dir = data.get('temp_dir', '')
    if not temp_dir or not os.path.exists(temp_dir):
        emit('file_list', {'files': [], 'error': 'No folder uploaded'})
        return
    recursive = data.get('process_subfolders', False)
    include_singles = data.get('include_singles', False)
    folders_dict = get_image_files_by_folder(temp_dir, recursive=recursive, include_singles=include_singles)
    file_list = []
    for subfolder, files in sorted(folders_dict.items()):
        rel_subfolder = os.path.relpath(subfolder, temp_dir)
        file_list.append(f"[{rel_subfolder}]")
        for f in sorted(files):
            file_list.append(f"    {os.path.basename(f)}")
    emit('file_list', {'files': file_list, 'total': sum(len(files) for files in folders_dict.values())})

if __name__ == '__main__':
    socketio.run(app, host='localhost', port=5050, debug=True)