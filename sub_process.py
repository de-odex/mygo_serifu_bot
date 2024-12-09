import subprocess

def extract_frame(video_file, frame_number, output_image):
    # 计算时间戳
    timestamp = frame_number / 23.98
    print(f"Extracting frame at {timestamp} seconds (frame number {frame_number})")

    # 使用 FFmpeg 提取特定帧
    ffmpeg_command = [
        "ffmpeg", 
        "-i", video_file,  # 输入视频文件
        "-ss", str(timestamp),  # 跳转到指定的时间戳
        "-vframes", "1",  # 提取一帧
        output_image  # 输出的图像文件
    ]
    
    try:
        # 调用 FFmpeg 命令
        subprocess.run(ffmpeg_command, check=True)
        print(f"Frame extracted and saved as {output_image}")
    except subprocess.CalledProcessError as e:
        print(f"Error extracting frame: {e}")

# 示例
video_file = "input_video.mp4"  # 视频文件路径
frame_number = 1512  # 需要提取的帧号
output_image = "output_frame.png"  # 输出图像文件

extract_frame(video_file, frame_number, output_image)
