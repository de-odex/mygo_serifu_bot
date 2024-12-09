import subprocess

def extract_frame(episode, frame_number):
    # 计算时间戳
    episode = 'src/' + str(episode) + '.mp4'
    timestamp = frame_number / 23.98
    print(f"Extracting frame at {timestamp} seconds (frame number {frame_number})")

    # 使用 FFmpeg 提取特定帧
    output_image = 'output/' + str(frame_number) + '.png'
    ffmpeg_command = [
        "ffmpeg", 
        "-i", episode,  # 输入视频文件
        "-vf", f"select=eq(n\\,{frame_number})",  # 精确选择帧
        "-vsync", "vfr",  # 防止不必要的帧同步
        "-vframes", "1",  # 仅提取一帧
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
