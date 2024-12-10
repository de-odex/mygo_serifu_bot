import subprocess

def extract_frame(episode, frame_number, back_seconds):
    # 计算时间戳
    episode = 'src/' + str(episode) + '.mp4'
    back_frames = round(back_seconds * 23.98)
    frame_number = frame_number + back_frames + 15
    timestamp = frame_number / 23.98  # 时间戳（秒）
    # 使用 FFmpeg 提取特定帧
    output_image = 'output/' + str(frame_number) + '.png'
    ffmpeg_command = [
        "ffmpeg", 
        "-ss", f"{timestamp:.6f}", 
        "-i", episode,  # 输入视频文件
        "-frames:v", "1",
        "-q:v", "2",                 # 高质量截图
        '-loglevel', 'error',
        output_image  # 输出的图像文件
    ]

        # 调用 FFmpeg 命令
    subprocess.run(ffmpeg_command, check=True)
    return output_image







if __name__ == "__main__":
    # 示例
    episode = "1-3"  # 视频文件路径
    frame_number = 1512  # 需要提取的帧号


    extract_frame(episode, frame_number)
