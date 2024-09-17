import os
import json
import subprocess
import requests
import concurrent.futures
import shutil
import zipfile
import fnmatch
from tkinter import Tk, Button, Label, StringVar, filedialog
from tqdm import tqdm

class FFMPEGMergerGUI:
    def __init__(self, master):
        self.master = master
        master.title("FFMPEG 视频音频合并工具")
        
        self.label = Label(master, text="请选择包含视频和音频文件的文件夹:")
        self.label.pack()

        self.folder_path_var = StringVar()
        self.folder_path_label = Label(master, textvariable=self.folder_path_var)
        self.folder_path_label.pack()

        self.select_button = Button(master, text="选择文件夹", command=self.select_folder)
        self.select_button.pack()

        self.merge_button = Button(master, text="开始合并", command=self.start_merge)
        self.merge_button.pack()

        # 新增输出路径标签和按钮
        self.output_path_label = Label(master, text="请选择输出文件夹:")
        self.output_path_label.pack()

        self.output_path_var = StringVar()
        self.output_path_label = Label(master, textvariable=self.output_path_var)
        self.output_path_label.pack()

        self.select_output_button = Button(master, text="选择输出文件夹", command=self.select_output_folder)
        self.select_output_button.pack()

        # 设置默认输出路径
        default_output_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "导出视频")
        if not os.path.exists(default_output_dir):
            os.makedirs(default_output_dir)
        self.output_path_var.set(default_output_dir)

        # 立即检查并下载 FFmpeg，并传递当前脚本所在目录
        current_dir = os.path.dirname(os.path.realpath(__file__))
        self.ensure_ffmpeg_installed(current_dir)

    def select_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.folder_path_var.set(folder_selected)

    def select_output_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.output_path_var.set(folder_selected)

    def start_merge(self):
        base_dir = self.folder_path_var.get()
        output_dir = self.output_path_var.get()
        if base_dir:
            tasks = []
            for root, dirs, files in os.walk(base_dir):
                if 'info.json' in files:
                    with open(os.path.join(root, 'info.json'), 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if 'VideoPath' in data and isinstance(data['VideoPath'], list) and len(data['VideoPath']) >= 2:
                            video_file = os.path.join(root, data['VideoPath'][0])
                            audio_file = os.path.join(root, data['VideoPath'][1])
                            episode_title = data['EpisodeTitle']
                            output_file = os.path.join(output_dir, f"{episode_title}.mp4")

                            # 将处理操作加入到线程池的任务列表中
                            tasks.append((video_file, audio_file, output_file))

            # 使用线程池来并发处理所有任务
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = [executor.submit(self.handle_ffmpeg_operations, *task) for task in tasks]
                concurrent.futures.wait(futures)

            self.label.config(text="合并完成！")
        else:
            self.label.config(text="请先选择文件夹！")

    def handle_ffmpeg_operations(self, video_path, audio_path, output_path):
        # 由于在多线程环境下，可能需要确保 ffmpeg 路径的正确性
        ffmpeg_path = self.find_ffmpeg(os.path.dirname(os.path.realpath(__file__)))
        command = [
            ffmpeg_path, "-i", video_path, "-i", audio_path,
            "-c", "copy", "-map", "0:v:0", "-map", "1:a:0",
            "-y", output_path
        ]
        self.execute_ffmpeg_command(command, output_path)

    def execute_ffmpeg_command(self, command, output_path):
        with open(os.devnull, "w") as f:
            process = subprocess.Popen(command, stdout=f, stderr=f)
        
            # 等待 ffmpeg 进程结束
            process.wait()
        
            if process.returncode == 0:
                print(f"文件 {output_path} 合并成功！")
            else:
                print(f"合并 {output_path} 失败！错误码：{process.returncode}")

    def download_ffmpeg(self, url, destination_folder):
        response = requests.get(url, stream=True)
        response.raise_for_status()

        total_size_in_bytes = int(response.headers.get('content-length', 0))
        block_size = 1024  # 1 Kibibyte
        progress_bar = tqdm(total=total_size_in_bytes, unit='iB', unit_scale=True)

        with open('ffmpeg.zip', 'wb') as file:
            for data in response.iter_content(block_size):
                progress_bar.update(len(data))
                file.write(data)

        progress_bar.close()
        if total_size_in_bytes != 0 and progress_bar.n != total_size_in_bytes:
            raise Exception("错误，下载出现问题")

        # 解压 ffmpeg 到指定文件夹
        with zipfile.ZipFile('ffmpeg.zip', 'r') as zip_ref:with zipfile.ZipFile('ffmpeg.zip', 'r') as zip_ref:
            zip_ref.extractall(destination_folder)

        # 清理临时文件
        os.remove('ffmpeg.zip')

    def find_ffmpeg(self, start_path):
        # 遍历 start_path 及其子目录寻找 ffmpeg.exe
        for dirpath, dirnames, filenames in os.walk(start_path):
            for filename in fnmatch.filter(filenames, 'ffmpeg.exe'):
                return os.path.join(dirpath, filename)
        return None

    def detect_ffmpeg(self):
        current_dir = os.path.dirname(os.path.realpath(__file__))
        ffmpeg_path = self.find_ffmpeg(current_dir)
        try:
            subprocess.run([ffmpeg_path, "-version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def ensure_ffmpeg_installed(self, base_dir):
        if not self.detect_ffmpeg():
            print("未找到 ffmpeg。尝试下载...")
            ffmpeg_folder = os.path.join(base_dir, "ffmpeg")
            if not os.path.exists(ffmpeg_folder):
                os.makedirs(ffmpeg_folder)
            
            # 示例 URL，用于下载 ffmpeg，请根据实际需要调整。
            url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
            self.download_ffmpeg(url, ffmpeg_folder)
            print("ffmpeg 已下载并解压完成。")


if __name__ == "__main__":
    root = Tk()
    gui = FFMPEGMergerGUI(root)
    root.mainloop()
