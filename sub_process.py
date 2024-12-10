import subprocess

def extract_frame(episode, frame_number, back_seconds):
    episode = 'src/' + str(episode) + '.mp4'
    back_frames = round(back_seconds * 23.98)
    frame_number = frame_number + back_frames + 15
    timestamp = frame_number / 23.98
    output_image = 'output/' + str(frame_number) + '.png'
    ffmpeg_command = [
        "ffmpeg", 
        "-ss", f"{timestamp:.6f}", 
        "-i", episode, 
        "-frames:v", "1",
        "-q:v", "2",               
        '-loglevel', 'error',
        output_image  
    ]


    subprocess.run(ffmpeg_command, check=True)
    return output_image







if __name__ == "__main__":
    episode = "1-3" 
    frame_number = 1512 


    extract_frame(episode, frame_number)
