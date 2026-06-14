from pythonosc.dispatcher import Dispatcher
from pythonosc import osc_server
import time
import socket
import pathlib
import os
import random
import threading
import cv2
import numpy as np
import subprocess
from collections import deque
from flask import Flask, render_template, request, redirect, url_for, jsonify
import json
import fcntl


app = Flask(__name__)


def files_loader():
    global dirs, videos, wrong_folders, current_dir
    dirs = sorted([
        name for name in os.listdir(current_dir)
        if os.path.isdir(os.path.join(current_dir, name))
        and name not in wrong_folders
    ])
    print(dirs)

    for dir_name in dirs:
        full_path = os.path.join(current_dir, dir_name)
        videos[dir_name] = os.listdir(full_path)


def filter_handler(address, *args):
    global local_config, to_category, status, to_sync
    if args[0] == 1:
        print("going synchronous")
        time.sleep(random.randint(0, local_config["delta_sync_mode"]))
        to_sync = True
        status = "synchronous"
        to_category = args[1]
    else:
        print("leaving synchronous")
        status = "random"
        to_sync = False
    

def osc_receiver():
    server = osc_server.ThreadingOSCUDPServer(
        (ip, port), dispatcher)
    print("Serving on {}".format(server.server_address))
    server.serve_forever()
    

def random_video():
    global local_config, last_category, repeat_count, to_category, status
    if(last_category is not None and repeat_count >= local_config["max_repeat"]):
        available_categories = [c for c in dirs if c != last_category]
    else:
        available_categories = dirs
    
    # Build matching weights
    weights_map = {
        "assis": local_config["param1"],
        "dos": local_config["param2"],
        "face": local_config["param3"],
        "marche": local_config["param4"],
        "profil": local_config["param5"],
        "visage": local_config["param6"],
        "yeux": local_config["param7"]
    }

    available_weights = [
        weights_map[c]
        for c in available_categories
    ]
    
    category = random.choices(available_categories, weights=available_weights, k=1)[0]
    
    if category == last_category:
        repeat_count += 1
    else:
        last_category = category
        repeat_count = 1

    print(
        f"Category: {category} "
        f"(repeat {repeat_count}/{local_config['max_repeat']})"
    )
    
    available_videos = []
    for i in range(len(videos[category])):
        if videos[category][i] not in old_videos:
            available_videos.append(videos[category][i])
            
    if len(available_videos) == 0:
        video = random.choice(videos[category])
    else:
        video = random.choice(available_videos)
    
    old_videos.append(video)
    if len(old_videos) >= local_config["video_buffer"]:
        old_videos.pop(0)
    return os.path.join(current_dir, category, video)


def preload(path):
    global BUFFER_SIZE, buffer, cap
    cap = cv2.VideoCapture(path)
    ret = True
    print(f"Loading video: {path}")
    for _ in range(BUFFER_SIZE):
        ret, frame = cap.read()
        if not ret:
            break
        buffer.append(frame)
    print(f"Video {path}, fully loaded\n")
    return buffer


def video_decoder():
    global local_config, running, buffer, cap, status, to_sync, to_category, old_getmtime, sync_video
    if os.path.getmtime(CONFIG_FILE) != old_getmtime:
        old_getmtime = os.path.getmtime(CONFIG_FILE)
        cfg = load_config()
        local_config = cfg

    while running:
        if len(buffer) >= buffer.maxlen:
            time.sleep(0.001)
            continue

        # refill ONE frame
        ret, new_frame = cap.read()
        if ret:
            buffer.append(new_frame)
        else:
            print("changing video")
            if status == "synchronous":
                good_videos = videos[to_category].copy()
                good_videos.remove(sync_video)
                sync_video = random.choice(good_videos)
                path = os.path.join(current_dir, to_category, sync_video)
            else:
                path = random_video()
            cap.release()
            cap = cv2.VideoCapture(path)
            new_video = True
            ret, new_frame = cap.read()
            buffer.append(new_frame)

        if status == "synchronous" and to_sync:
            to_sync = False
            print("to category: " + to_category)
            sync_video = random.choice(videos[to_category])
            print(sync_video)
            cap.release()
            cap = cv2.VideoCapture(os.path.join(current_dir, to_category, sync_video))
            new_video = True
            ret, new_frame = cap.read()
            buffer.append(new_frame)


def video_handler():
    global local_config, running, buffer, cap, status, to_sync, to_category, old_getmtime, FBIO_WAITFORVSYNC
    new_video = True
    start_time = time.perf_counter()
    frame_index = 0
    fb_fd = os.open("/dev/fb0", os.O_RDWR)
    fb_map = np.memmap("/dev/fb0", dtype='uint8',mode='r+', shape=(1080,1920,3))

    while running:
        if len(buffer) == 0:
            time.sleep(0.01)
            continue
        
        if new_video:
            start_time = time.perf_counter()
            frame_index = 0
            new_video = False

        target = start_time + frame_index / FPS
        
        frame = buffer.popleft()
        fcntl.ioctl(fb_fd, FBIO_WAITFORVSYNC)
        fb_map[:] = frame

        while True:
            remaining = target - time.perf_counter()
            if remaining <= 0:
                break
            time.sleep(min(remaining, 0.001))

        frame_index += 1


# Load config
def load_config():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump(default_config, f, indent=4)

    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


# Save config
def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)


@app.route("/")
def index():
    selected_folder = request.args.get(
        "folder",
        dirs[0]
    )

    if selected_folder not in dirs:
        selected_folder = dirs[0]

    folder_path = os.path.join(
        BASE_UPLOAD_FOLDER,
        selected_folder
    )

    if os.path.exists(folder_path):
        files = sorted(os.listdir(folder_path))
    else:
        files = []

    return render_template(
        "index.html",
        folders=dirs,
        selected_folder=selected_folder,
        files=files,
        config=local_config
    )


@app.route("/identify", methods=["POST"])
def flash_screen():
    global current_dir, buffer
    print("FLASHING SCREEN...")
    white = cv2.imread(os.path.join(current_dir, "white.png"))
    buffer.append(white)
    print("Done flashing")
    return redirect(url_for("index"))


@app.route("/upload", methods=["POST"])
def upload_video():
    if "video" not in request.files:
        return "No file uploaded", 400

    file = request.files["video"]
    selected_folder = request.form.get("folder")

    # Security check
    if selected_folder not in dirs:
        return "Invalid folder", 400

    if file.filename != "":
        upload_path = os.path.join(BASE_UPLOAD_FOLDER, selected_folder)
        filepath = os.path.join(upload_path, file.filename)
        file.save(filepath)
        
    files_loader()
    return redirect(url_for("index"))


@app.route("/delete_file", methods=["POST"])
def delete_file():

    folder = request.form.get("folder")
    filename = request.form.get("filename")

    # Security checks
    if folder not in dirs:
        return "Invalid folder", 400

    filepath = os.path.join(BASE_UPLOAD_FOLDER, folder, filename)

    # Prevent weird path traversal attacks
    filepath = os.path.abspath(filepath)
    allowed_path = os.path.abspath(
        os.path.join(BASE_UPLOAD_FOLDER, folder)
    )

    if not filepath.startswith(allowed_path):
        return "Invalid path", 400

    if os.path.exists(filepath):
        os.remove(filepath)

    files_loader()
    return redirect(url_for("index"))


@app.route("/save_config", methods=["POST"])
def save_parameters():
    global local_config
    new_config = {
        "param1": int(request.form["param1"]),
        "param2": int(request.form["param2"]),
        "param3": int(request.form["param3"]),
        "param4": int(request.form["param4"]),
        "param5": int(request.form["param5"]),
        "param6": int(request.form["param6"]),
        "param7": int(request.form["param7"]),
        "max_repeat": int(request.form["max_repeat"]),
        "video_buffer": int(request.form["video_buffer"]),
        "delta_sync_mode": int(request.form["delta_sync_mode"])
    }

    save_config(new_config)
    local_config = load_config()

    return redirect(url_for("index"))


dirs = []
videos = {}
old_videos = []
wrong_folders = [".idea", ".venv", "templates", "uploads"]
current_dir = os.path.join(pathlib.Path(__file__).parent.resolve(), 'uploads')

BASE_UPLOAD_FOLDER = current_dir
CONFIG_FILE = os.path.join(pathlib.Path(__file__).parent.resolve(), 'config.json')

os.makedirs(BASE_UPLOAD_FOLDER, exist_ok=True)

default_config = {
    "param1": 10,
    "param2": 10,
    "param3": 10,
    "param4": 10,
    "param5": 10,
    "param6": 10,
    "param7": 40,
    "max_repeat": 3,
    "video_buffer": 10,
    "delta_sync_mode": 10
}

local_config = load_config()
last_category = None
repeat_count = 0
FBIO_WAITFORVSYNC = 1074021920

# Python variables linked to config
config = load_config()

dispatcher = Dispatcher()
dispatcher.map("/synchronous", filter_handler)

ip = "0.0.0.0"
print(ip)
port = 9000

start_time = 0
FPS = 25
BUFFER_SECONDS = 4
BUFFER_SIZE = FPS * BUFFER_SECONDS

os.environ["vblank_mode"] = "1"

buffer = deque(maxlen=100)
cap = cv2.VideoCapture()

to_category = None
status = "random"
to_sync = False

print("loading files: ")
files_loader()
print("Loading videos:\n")
media = random_video()
video1 = preload(media)
running = False
old_getmtime = 1000

print("All videos loaded.")

time.sleep(10)


if __name__ == "__main__":
    os.system('sudo sh -c "TERM=linux setterm -foreground black -clear all > /dev/tty0"')
    os.system('sudo sh -c "TERM=linux setterm -cursor off > /dev/tty0"')
    # subprocess.Popen(["unclutter", "-idle", "0.01", "-root"])
    running = True
    decoder_thread = threading.Thread(target=video_decoder, daemon=False)
    decoder_thread.start()
    video_thread = threading.Thread(target=video_handler, daemon=False)
    video_thread.start()
    osc_thread = threading.Thread(target=osc_receiver, daemon=False)
    osc_thread.start()
    app.run(host="0.0.0.0", port=8000, debug=False)
