import os
import subprocess
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, ttk, messagebox

VIDEO_EXTENSIONS = (".mp4", ".mov", ".mkv", ".avi", ".webm")

encoder_tests = {
    "Intel QSV": ["h264_qsv", "hevc_qsv"],
    "NVIDIA NVENC": ["h264_nvenc", "hevc_nvenc", "av1_nvenc"],
    "AMD AMF": ["h264_amf", "hevc_amf"],
    "VAAPI": ["h264_vaapi", "hevc_vaapi"],
    "VideoToolbox": ["h264_videotoolbox", "hevc_videotoolbox"]
}

def get_ffmpeg_path():
    return os.path.join(os.path.dirname(__file__), "extra", "bin", "ffmpeg.exe")

def test_encoder(encoder):
    try:
        ffmpeg_path = get_ffmpeg_path()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            tmp_path = tmp.name
        cmd = [
            ffmpeg_path, "-y",
            "-f", "lavfi", "-i", "color=black:s=128x128:d=1",
            "-c:v", encoder,
            tmp_path
        ]
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        result = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo)
        os.remove(tmp_path)
        return "Error" not in result.stderr and result.returncode == 0
    except:
        return False

def detect_working_encoders():
    available = {}
    for vendor, encoders in encoder_tests.items():
        working = []
        for enc in encoders:
            if test_encoder(enc):
                working.append(enc)
        if working:
            available[vendor] = working
    return available

def convert_video(input_path, output_path, encoder):
    ffmpeg_path = get_ffmpeg_path()
    cmd = [
        ffmpeg_path, "-y",
        "-i", input_path,
        "-c:v", encoder,
        "-c:a", "aac", "-b:a", "320k",
        "-map", "0:v:0", "-map", "0:a?",
        output_path
    ]
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, startupinfo=startupinfo)

class VideoConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("GPU Video Converter")
        self.folder = ""
        self.encoder = ""
        self.output_format = ".mp4"
        self.files = []
        self.vendor_encoder_map = detect_working_encoders()

        if not self.vendor_encoder_map:
            messagebox.showerror("Error", "No usable GPU encoders detected.")
            self.root.destroy()
            return

        self.create_widgets()

    def create_widgets(self):
        tk.Label(self.root, text="1. Select Folder:").pack()
        self.select_btn = tk.Button(self.root, text="Select Folder", command=self.select_folder)
        self.select_btn.pack()

        tk.Label(self.root, text="2. Choose GPU Encoder:").pack()
        self.encoder_var = tk.StringVar()
        self.encoder_menu = ttk.Combobox(self.root, textvariable=self.encoder_var, state="readonly")
        all_encs = [enc for encs in self.vendor_encoder_map.values() for enc in encs]
        self.encoder_menu['values'] = all_encs
        self.encoder_menu.current(0)
        self.encoder_menu.pack()

        tk.Label(self.root, text="3. Output Format:").pack()
        self.format_var = tk.StringVar(value=".mp4")
        self.format_menu = ttk.Combobox(self.root, textvariable=self.format_var, state="readonly")
        self.format_menu['values'] = [".mp4", ".mkv", ".webm"]
        self.format_menu.pack()

        self.progress_bar = ttk.Progressbar(self.root, length=400, mode='determinate')
        self.progress_bar.pack(pady=10)

        self.progress_label = tk.Label(self.root, text="Converted: 0 | Pending: 0 | 0%")
        self.progress_label.pack()

        self.convert_btn = tk.Button(self.root, text="Start Conversion", command=self.start_conversion)
        self.convert_btn.pack(pady=10)

    def select_folder(self):
        self.folder = filedialog.askdirectory()
        if self.folder:
            self.files = [
                f for f in os.listdir(self.folder)
                if f.lower().endswith(VIDEO_EXTENSIONS)
            ]
            messagebox.showinfo("Found Files", f"{len(self.files)} video files found.")

    def start_conversion(self):
        if not self.folder or not self.files:
            messagebox.showwarning("No Folder", "Please select a folder with video files.")
            return

        self.encoder = self.encoder_var.get()
        self.output_format = self.format_var.get()
        output_dir = os.path.join(self.folder, "converted")
        os.makedirs(output_dir, exist_ok=True)

        self.progress_bar["maximum"] = 100
        self.progress_bar["value"] = 0
        self.convert_btn.config(state=tk.DISABLED)

        threading.Thread(target=self.convert_all, args=(output_dir,)).start()

    def update_progress(self, completed):
        total = len(self.files)
        percent = int((completed / total) * 100)
        pending = total - completed
        self.progress_bar["value"] = percent
        self.progress_label.config(text=f"Converted: {completed} / {total} | Pending: {pending} | {percent}%")
        self.root.update_idletasks()

    def convert_all(self, output_dir):
        completed = 0
        for filename in self.files:
            input_path = os.path.join(self.folder, filename)
            base_name, _ = os.path.splitext(filename)
            output_path = os.path.join(output_dir, base_name + "_" + self.encoder + self.output_format)
            convert_video(input_path, output_path, self.encoder)
            completed += 1
            self.update_progress(completed)

        self.convert_btn.config(state=tk.NORMAL)
        messagebox.showinfo("Done", "Video conversion completed.")

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoConverterApp(root)
    root.mainloop()
